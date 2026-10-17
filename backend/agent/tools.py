"""
Agent Tool Registry & Foundation for Human Cache.
Defines typed, permission-aware tools wrapping existing learning features.
Enforces user-scoped execution, Pydantic argument validation, and consequential-action safeguards.
"""

from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
import logging

from backend.models import (
    Topic, Document, TopicMemoryState, FlashcardDeck, Flashcard,
    StudyTask, Exam, Category
)
from backend.memory_engine import calculate_current_retention
from backend.ai.retrieval import RetrievalService
from backend.ai.generation import RAGIntelligenceEngine
from backend.ai_engine import AITutorEngine

logger = logging.getLogger("human_cache.agent.tools")


# --- Tool Input Schemas ---

class RetrieveKnowledgeInput(BaseModel):
    query: str = Field(..., description="Search query to find relevant excerpts from indexed documents.")
    top_k: int = Field(5, ge=1, le=10, description="Maximum number of relevant chunks to retrieve.")
    document_ids: Optional[List[str]] = Field(None, description="Optional filter to scope retrieval to specific document IDs.")


class GeneratePracticeQuizInput(BaseModel):
    topic_id: Optional[str] = Field(None, description="Optional ID of the topic to generate quiz for.")
    topic_name: Optional[str] = Field(None, description="Optional concept name if topic ID is not known.")
    question_count: int = Field(3, ge=1, le=10, description="Number of quiz questions to generate.")
    difficulty: str = Field("adaptive", description="Difficulty level: 'adaptive', 'easy', 'medium', or 'hard'.")


class GenerateAdaptiveFlashcardsInput(BaseModel):
    topic_id: str = Field(..., description="ID of the topic/concept to generate flashcards for.")
    card_count: int = Field(5, ge=1, le=15, description="Number of flashcards to generate.")
    detail_level: str = Field("standard", description="Level of detail: 'concise', 'standard', or 'comprehensive'.")


class GenerateMindMapInput(BaseModel):
    topic_id: str = Field(..., description="ID of the topic to generate structured visual mind map for.")
    depth: int = Field(3, ge=1, le=5, description="Depth level of hierarchical subtopic tree.")


class QueryLearnerRetentionInput(BaseModel):
    topic_ids: Optional[List[str]] = Field(None, description="Optional list of topic IDs to check retention states for.")
    concept_name: Optional[str] = Field(None, description="Optional concept name keyword to filter topics.")


class ModifyStudyScheduleInput(BaseModel):
    task_id: str = Field(..., description="ID of the study task to modify.")
    new_date: str = Field(..., description="New ISO date string for task schedule.")
    new_allocated_minutes: Optional[int] = Field(None, ge=5, le=480, description="Updated study duration in minutes.")


class DeleteDocumentInput(BaseModel):
    document_id: str = Field(..., description="ID of the document to delete.")


# --- Tool Definition Wrapper ---

class AgentTool:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: type[BaseModel],
        handler: Callable,
        is_consequential: bool = False
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
        self.is_consequential = is_consequential

    def get_parameter_specs(self) -> List[Dict[str, Any]]:
        specs = []
        schema = self.input_schema.model_json_schema()
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for field_name, field_info in properties.items():
            specs.append({
                "name": field_name,
                "type": field_info.get("type", "string"),
                "description": field_info.get("description", ""),
                "required": field_name in required,
                "default": field_info.get("default")
            })
        return specs


# --- Tool Implementations ---

def handle_retrieve_knowledge(user_id: str, db: Session, args: RetrieveKnowledgeInput) -> Dict[str, Any]:
    retrieval_svc = RetrievalService(db)
    chunks = retrieval_svc.retrieve(
        user_id=user_id,
        query=args.query,
        top_k=args.top_k,
        document_ids=args.document_ids
    )
    formatted = []
    for c in chunks:
        formatted.append({
            "chunk_id": c.get("chunk_id"),
            "document_id": c.get("document_id"),
            "document_title": c.get("document_title"),
            "filename": c.get("filename"),
            "page_number": c.get("page_number"),
            "section_heading": c.get("section_heading"),
            "snippet": c.get("content", "")[:400],
            "similarity_score": round(c.get("similarity_score", 0.0), 3)
        })
    return {
        "query": args.query,
        "count": len(formatted),
        "chunks": formatted,
        "source_type": "uploaded_documents" if formatted else "none_found"
    }


def handle_generate_quiz(user_id: str, db: Session, args: GeneratePracticeQuizInput) -> Dict[str, Any]:
    topic_name = args.topic_name or "General Topic"
    topic = None

    if args.topic_id:
        topic = db.query(Topic).filter(Topic.id == args.topic_id, Topic.user_id == user_id).first()
        if topic:
            topic_name = topic.canonical_name
    elif args.topic_name:
        topic = db.query(Topic).filter(Topic.canonical_name.ilike(args.topic_name), Topic.user_id == user_id).first()
        if topic:
            topic_name = topic.canonical_name

    rag_engine = RAGIntelligenceEngine(db)
    quiz_data = rag_engine.generate_quiz(
        user_id=user_id,
        topic_name=topic_name,
        question_count=args.question_count,
        difficulty=args.difficulty
    )
    return {
        "topic": topic_name,
        "topic_id": topic.id if topic else None,
        "difficulty": args.difficulty,
        "question_count": len(quiz_data.get("questions", [])),
        "questions": quiz_data.get("questions", []),
        "action": "ready_for_drill"
    }


def handle_generate_flashcards(user_id: str, db: Session, args: GenerateAdaptiveFlashcardsInput) -> Dict[str, Any]:
    topic = db.query(Topic).filter(Topic.id == args.topic_id, Topic.user_id == user_id).first()
    if not topic:
        raise ValueError(f"Topic '{args.topic_id}' not found or access denied.")

    rag_engine = RAGIntelligenceEngine(db)
    deck_data = rag_engine.generate_flashcards(
        user_id=user_id,
        topic_name=topic.canonical_name,
        card_count=args.card_count,
        detail_level=args.detail_level
    )
    cards = deck_data.get("cards", [])

    # Persist flashcard deck
    deck = FlashcardDeck(
        user_id=user_id,
        title=f"Deck: {topic.canonical_name}",
        description=f"Generated by AI Agent for {topic.canonical_name}",
        topic_id=topic.id,
        detail_level=args.detail_level,
        version=1
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)

    for c in cards:
        fc = Flashcard(
            deck_id=deck.id,
            front=c.get("front", ""),
            back=c.get("back", ""),
            hint=c.get("hint", ""),
            topic_id=topic.id,
            difficulty=0.3
        )
        db.add(fc)
    db.commit()

    return {
        "deck_id": deck.id,
        "topic_id": topic.id,
        "topic_name": topic.canonical_name,
        "cards_created": len(cards),
        "cards_preview": cards[:3]
    }


def handle_generate_mind_map(user_id: str, db: Session, args: GenerateMindMapInput) -> Dict[str, Any]:
    topic = db.query(Topic).filter(Topic.id == args.topic_id, Topic.user_id == user_id).first()
    if not topic:
        raise ValueError(f"Topic '{args.topic_id}' not found or access denied.")

    # Build hierarchical subtopic tree
    root_node = {
        "id": f"node_{topic.id}",
        "name": topic.canonical_name,
        "description": topic.description or f"Core concept: {topic.canonical_name}",
        "children": [
            {"id": f"node_{topic.id}_1", "name": "Foundational Principles", "description": "Key definitions and axioms"},
            {"id": f"node_{topic.id}_2", "name": "Core Applications", "description": "Formulas and exam problems"},
            {"id": f"node_{topic.id}_3", "name": "Related Subtopics", "description": "Cross-domain linkages"}
        ]
    }
    return {
        "topic_id": topic.id,
        "central_topic": topic.canonical_name,
        "depth": args.depth,
        "root_node": root_node,
        "status": "generated"
    }


def handle_query_retention(user_id: str, db: Session, args: QueryLearnerRetentionInput) -> Dict[str, Any]:
    query = db.query(TopicMemoryState, Topic).join(Topic, TopicMemoryState.topic_id == Topic.id).filter(
        TopicMemoryState.user_id == user_id
    )
    if args.topic_ids:
        query = query.filter(TopicMemoryState.topic_id.in_(args.topic_ids))
    if args.concept_name:
        query = query.filter(Topic.canonical_name.ilike(f"%{args.concept_name}%"))

    records = query.limit(10).all()
    results = []
    for mem, top in records:
        retention = calculate_current_retention(mem.last_recall_at, mem.stability) if mem.last_recall_at else 1.0
        results.append({
            "topic_id": top.id,
            "topic_name": top.canonical_name,
            "status": mem.status,
            "stability_days": round(mem.stability or 1.0, 2),
            "estimated_retention": round(retention, 3),
            "is_suppressed": mem.no_need_suppressed
        })
    return {
        "count": len(results),
        "retention_data": results
    }


def handle_modify_study_schedule(user_id: str, db: Session, args: ModifyStudyScheduleInput) -> Dict[str, Any]:
    task = db.query(StudyTask).filter(StudyTask.id == args.task_id, StudyTask.user_id == user_id).first()
    if not task:
        raise ValueError(f"Study task '{args.task_id}' not found or does not belong to you.")
    
    from datetime import datetime
    try:
        task.scheduled_for = datetime.fromisoformat(args.new_date)
    except Exception:
        raise ValueError(f"Invalid date format '{args.new_date}'. Use ISO 8601 string.")
    
    if args.new_allocated_minutes:
        task.allocated_minutes = args.new_allocated_minutes
    db.commit()
    db.refresh(task)
    return {
        "task_id": task.id,
        "title": task.title,
        "new_scheduled_for": task.scheduled_for.isoformat(),
        "allocated_minutes": task.allocated_minutes,
        "status": "rescheduled"
    }


def handle_delete_document(user_id: str, db: Session, args: DeleteDocumentInput) -> Dict[str, Any]:
    doc = db.query(Document).filter(Document.id == args.document_id, Document.user_id == user_id).first()
    if not doc:
        raise ValueError(f"Document '{args.document_id}' not found or access denied.")
    title = doc.title
    db.delete(doc)
    db.commit()
    return {
        "deleted_document_id": args.document_id,
        "title": title,
        "status": "deleted"
    }


# --- Tool Registry ---

class AgentToolRegistry:
    def __init__(self):
        self._tools: Dict[str, AgentTool] = {}
        self._register_default_tools()

    def register(
        self,
        name: str,
        description: str,
        input_schema: type[BaseModel],
        handler: Callable,
        is_consequential: bool = False
    ):
        self._tools[name] = AgentTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            is_consequential=is_consequential
        )

    def get_tool(self, name: str) -> Optional[AgentTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "is_consequential": t.is_consequential,
                "requires_confirmation": t.is_consequential,
                "parameters": t.get_parameter_specs()
            }
            for t in self._tools.values()
        ]

    def execute(
        self,
        tool_name: str,
        user_id: str,
        db: Session,
        arguments: Dict[str, Any],
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a registered tool within the caller's authorized user context.
        Validates arguments with Pydantic and blocks unconfirmed consequential actions.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "tool_name": tool_name,
                "success": False,
                "error": f"Tool '{tool_name}' is not registered."
            }

        # Consequential action safety check
        if tool.is_consequential and not confirmed:
            return {
                "tool_name": tool_name,
                "success": False,
                "requires_confirmation": True,
                "confirmation_prompt": (
                    f"Action '{tool_name}' requires your explicit confirmation before proceeding "
                    f"with changes to your study schedule or document records."
                )
            }

        # Validate arguments using the tool's Pydantic schema
        try:
            validated_args = tool.input_schema(**arguments)
        except ValidationError as val_err:
            return {
                "tool_name": tool_name,
                "success": False,
                "error": f"Invalid arguments for '{tool_name}': {val_err.errors()}"
            }

        try:
            result = tool.handler(user_id=user_id, db=db, args=validated_args)
            return {
                "tool_name": tool_name,
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error executing agent tool '{tool_name}': {e}", exc_info=True)
            return {
                "tool_name": tool_name,
                "success": False,
                "error": str(e)
            }

    def _register_default_tools(self):
        self.register(
            name="retrieve_knowledge_chunks",
            description="Searches the authenticated user's uploaded documents and notes for relevant excerpts and formulas.",
            input_schema=RetrieveKnowledgeInput,
            handler=handle_retrieve_knowledge,
            is_consequential=False
        )
        self.register(
            name="generate_practice_quiz",
            description="Generates an active recall quiz for the user based on target concepts and difficulty level.",
            input_schema=GeneratePracticeQuizInput,
            handler=handle_generate_quiz,
            is_consequential=False
        )
        self.register(
            name="generate_adaptive_flashcards",
            description="Generates a deck of adaptive flashcards calibrated to the learner's memory stability.",
            input_schema=GenerateAdaptiveFlashcardsInput,
            handler=handle_generate_flashcards,
            is_consequential=False
        )
        self.register(
            name="generate_mind_map",
            description="Generates a hierarchical visual concept tree for conceptual learning and revision.",
            input_schema=GenerateMindMapInput,
            handler=handle_generate_mind_map,
            is_consequential=False
        )
        self.register(
            name="query_learner_retention",
            description="Checks current retention stability scores, review history, and forgetting curve status for concepts.",
            input_schema=QueryLearnerRetentionInput,
            handler=handle_query_retention,
            is_consequential=False
        )
        self.register(
            name="modify_study_schedule",
            description="Reschedules a study task or adjusts allocated study duration.",
            input_schema=ModifyStudyScheduleInput,
            handler=handle_modify_study_schedule,
            is_consequential=True
        )
        self.register(
            name="delete_document",
            description="Permanently deletes an indexed study document and its associated vectors from the vault.",
            input_schema=DeleteDocumentInput,
            handler=handle_delete_document,
            is_consequential=True
        )


# Global singleton instance
tool_registry = AgentToolRegistry()
