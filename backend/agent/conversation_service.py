"""
Conversation Service for Human Cache Agent.
Handles persistent conversation threads, multi-turn message storage,
bounded context assembly, and model response generation.
"""

import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from backend.models import AgentConversation, AgentMessage, User, Topic
from backend.agent.context import LearnerContextAssembler
from backend.ai.generation import RAGIntelligenceEngine

logger = logging.getLogger("human_cache.agent.conversation")


class AgentConversationService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        topic_id: Optional[str] = None
    ) -> AgentConversation:
        """Creates a new persistent conversation thread scoped to the user."""
        # Optional validation of topic_id if passed
        if topic_id:
            topic = self.db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
            if not topic:
                topic_id = None

        thread_title = title.strip() if title and title.strip() else "New Study Session"
        conv = AgentConversation(
            user_id=user_id,
            title=thread_title,
            topic_id=topic_id,
            is_archived=False
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def list_conversations(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        include_archived: bool = False
    ) -> List[AgentConversation]:
        """Lists conversations for user ordered by most recently active."""
        query = self.db.query(AgentConversation).filter(AgentConversation.user_id == user_id)
        if not include_archived:
            query = query.filter(AgentConversation.is_archived == False)

        return query.order_by(AgentConversation.updated_at.desc()).offset(skip).limit(limit).all()

    def get_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message_limit: int = 50
    ) -> AgentConversation:
        """Retrieves conversation ensuring user authorization."""
        conv = self.db.query(AgentConversation).filter(
            AgentConversation.id == conversation_id,
            AgentConversation.user_id == user_id
        ).first()

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

        return conv

    def update_conversation(
        self,
        user_id: str,
        conversation_id: str,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None
    ) -> AgentConversation:
        """Updates title or archive status of conversation."""
        conv = self.get_conversation(user_id, conversation_id)
        if title is not None and title.strip():
            conv.title = title.strip()
        if is_archived is not None:
            conv.is_archived = is_archived

        conv.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Deletes conversation and cascades messages."""
        conv = self.get_conversation(user_id, conversation_id)
        self.db.delete(conv)
        self.db.commit()
        return True

    def post_user_message_and_respond(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        language: Optional[str] = "auto",
        document_ids: Optional[List[str]] = None
    ) -> AgentMessage:
        """
        Appends user message, builds grounded context with earlier turns,
        invokes the tutor intelligence model, and persists both turns.
        """
        conv = self.get_conversation(user_id, conversation_id)
        user = self.db.query(User).filter(User.id == user_id).first()
        user_name = user.name if user else "Learner"

        clean_content = content.strip()
        if not clean_content:
            raise HTTPException(status_code=400, detail="Message content cannot be empty.")

        # 1. Fetch prior messages for history BEFORE appending current turn
        prior_messages = self.db.query(AgentMessage).filter(
            AgentMessage.conversation_id == conversation_id
        ).order_by(AgentMessage.created_at.asc()).all()

        history_payload = [{"role": m.role, "content": m.content} for m in prior_messages]

        # 2. Persist the user message turn
        user_msg = AgentMessage(
            conversation_id=conversation_id,
            role="user",
            content=clean_content,
            meta={"language": language}
        )
        self.db.add(user_msg)
        self.db.commit()

        # Update thread title if first turn
        if conv.title == "New Study Session" and len(prior_messages) == 0:
            snippet = clean_content[:35].replace("\n", " ").strip()
            conv.title = snippet + ("..." if len(clean_content) > 35 else "")

        # 3. Assemble structured context
        assembler = LearnerContextAssembler(self.db, max_history_turns=10, max_chunks=4)
        prompt, citations, ctx_meta = assembler.assemble(
            user_id=user_id,
            user_name=user_name,
            current_query=clean_content,
            conversation_history=history_payload,
            document_ids=document_ids
        )

        # 4. Generate AI response
        t_start = time.perf_counter()
        rag_engine = RAGIntelligenceEngine(self.db)
        provider = rag_engine.provider

        reply_text = ""
        model_name = "mock-tutor"

        if provider.is_available():
            try:
                reply_text = provider.generate_text(prompt, temperature=0.3)
                model_name = getattr(provider, "model_name", "gemini-3.8-flash")
            except Exception as e:
                logger.warning(f"Live Gemini generation failed: {e}. Using intelligent fallback.")
                reply_text = self._build_deterministic_fallback(clean_content, citations, user_name)
        else:
            reply_text = self._build_deterministic_fallback(clean_content, citations, user_name)

        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        # 5. Persist assistant response turn
        assistant_msg = AgentMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=reply_text,
            citations=citations,
            meta={
                "model": model_name,
                "latency_ms": latency_ms,
                "language": language,
                "context_meta": ctx_meta
            }
        )
        self.db.add(assistant_msg)
        conv.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(assistant_msg)

        return assistant_msg

    def _build_deterministic_fallback(
        self,
        query: str,
        citations: List[Dict[str, Any]],
        user_name: str
    ) -> str:
        """
        Deterministic, grounded academic response used when API keys are unconfigured or offline.
        Strictly distinguishes uploaded source provenance from general knowledge.
        """
        uploaded_citations = [c for c in citations if c.get("source_type") == "uploaded_document"]

        if uploaded_citations:
            top = uploaded_citations[0]
            return (
                f"Hello {user_name}! Based on your uploaded study notes in **{top['title']}** "
                f"({top.get('locator', 'Page 1')}):\n\n"
                f"> \"{top.get('snippet', '')}\"\n\n"
                f"This foundational concept is directly indexed in your knowledge vault. "
                f"To lock this in before your upcoming reviews, would you like to attempt a quick 3-question active recall drill?"
            )
        else:
            return (
                f"Hello {user_name}! Regarding your question on **'{query}'**:\n\n"
                f"*Note: This concept is not in your currently indexed upload files; "
                f"the following explanation is drawn from foundational general curriculum knowledge.*\n\n"
                f"In general principles, {query} relates to core axioms and systematic applications. "
                f"When you upload relevant course slides, syllabus PDFs, or textbook chapters, I will automatically cross-reference "
                f"its exact formulas and definitions directly into your personal knowledge graph!"
            )
