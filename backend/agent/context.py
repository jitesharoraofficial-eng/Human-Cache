"""
Learner Context Foundation & Assembler for Human Cache Agent.
Constructs bounded, grounded prompt contexts tailored to the learner's onboarding profile,
target exam, retention states, recent conversation history, and indexed knowledge.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
from sqlalchemy.orm import Session
import logging

from backend.models import (
    User, UserPreference, Exam, TopicMemoryState, Topic, SourceChunk, Document
)
from backend.ai.retrieval import RetrievalService
from backend.memory_engine import calculate_current_retention

logger = logging.getLogger("human_cache.agent.context")

# Core system instructions for Human Cache Agentic AI
AGENT_SYSTEM_PROMPT = """You are the Human Cache AI Learning Agent — a personalized, autonomous, and compassionate cognitive mentor.
You assist learners across high school, competitive exams (JEE, NEET, UPSC), university engineering, medical, and professional upskilling tracks.

### 1. Multi-Lingual Understanding (English, Hindi & Hinglish)
- You naturally understand queries in English, Hindi (Devanagari), and conversational Hinglish (e.g., "Mujhe Carnot cycle ka concept samjhao", "Formula derivation clear nahi ho raha", "Exam me kaunse high-yield topics aayenge?").
- Match the learner's conversational language. If the user asks in Hinglish, reply in clear, supportive Hinglish with technical terms in English. If in English, reply in crisp educational English.

### 2. Strict Grounding & Provenance Attribution
- Differentiate between:
  a) **User Uploaded Documents**: Explicitly cited with [Document: <filename>, Page: <page>].
  b) **AI General Knowledge**: When explaining broader concepts or outside syllabus topics, clearly label explanations as based on foundational AI knowledge.
- NEVER fabricate uploaded documents, nonexistent chapters, fake quiz scores, or unindexed study materials.
- If information is not in their uploaded notes, explicitly state so, then provide the standard foundational explanation.

### 3. Persona & Pedagogical Adaptation
- Tailor explanations to the learner's active target exam and educational role:
  * For JEE / NEET: Emphasize core mathematical derivations, problem-solving intuition, and high-yield pitfalls.
  * For College / University: Focus on analytical rigor, system architectures, and practical applications.
  * For General / School: Use clean analogies, stepped breakdowns, and intuitive visual examples.
- Adjust explanation depth according to their preference (concise, semi-detailed, or comprehensive).
- Ask clarification questions only when essential to disambiguate the request.
"""


class LearnerContextAssembler:
    """
    Gathers and synthesizes contextual signals for the current turn:
    - User preferences and learning goals
    - Active exam deadlines
    - Recent retention states on relevant topics
    - Relevant indexed document chunks
    - Bounded conversation history
    """

    def __init__(self, db: Session, max_history_turns: int = 10, max_chunks: int = 4):
        self.db = db
        self.max_history_turns = max_history_turns
        self.max_chunks = max_chunks

    def assemble(
        self,
        user_id: str,
        user_name: str,
        current_query: str,
        conversation_history: List[Dict[str, Any]],
        document_ids: Optional[List[str]] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Builds the unified prompt context.
        Returns:
            (formatted_prompt, retrieved_citations, context_metadata)
        """
        # 1. Fetch user onboarding profile and preferences
        prefs = self.db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        target_exam = prefs.target_exam if prefs and prefs.target_exam else "General Learning"
        curriculum = prefs.curriculum if prefs and prefs.curriculum else "Standard Curriculum"
        roles = prefs.user_roles if prefs and prefs.user_roles else ["Learner"]
        goals = prefs.learning_goals_list if prefs and prefs.learning_goals_list else ["Concept Mastery"]
        depth = prefs.explanation_depth if prefs and prefs.explanation_depth else "semi-detailed"
        teaching_styles = prefs.teaching_styles if prefs and prefs.teaching_styles else ["balanced"]

        context_dict = prefs.learning_context if prefs and isinstance(prefs.learning_context, dict) else {}
        college_degree = (context_dict.get("college_degree") or "").strip()
        college_field = (context_dict.get("college_field") or "").strip()
        class_grade = (context_dict.get("class_grade") or "").strip()
        academic_year = (context_dict.get("academic_year") or "").strip()
        prof_role = (context_dict.get("profession_role") or "").strip()
        prof_industry = (context_dict.get("profession_industry") or "").strip()

        subjects_of_interest = (prefs.subjects_of_interest or []) if prefs else []
        custom_subjects = (prefs.custom_subjects or []) if prefs else []
        all_subjects = list(dict.fromkeys(subjects_of_interest + custom_subjects))
        custom_instructions = (prefs.custom_instructions or "").strip() if prefs else ""

        # 2. Check active upcoming exams
        now = datetime.utcnow()
        upcoming_exams = self.db.query(Exam).filter(
            Exam.user_id == user_id,
            Exam.exam_date >= now
        ).order_by(Exam.exam_date.asc()).limit(2).all()

        exam_context_lines = []
        for ex in upcoming_exams:
            days_left = max(0, (ex.exam_date - now).days)
            exam_context_lines.append(f"- {ex.subject}: in {days_left} days (Date: {ex.exam_date.strftime('%Y-%m-%d')})")
        exam_str = "\n".join(exam_context_lines) if exam_context_lines else "None scheduled."

        # 3. Retrieve relevant knowledge chunks from user's uploaded materials
        retrieval_svc = RetrievalService(self.db)
        chunks = retrieval_svc.retrieve(
            user_id=user_id,
            query=current_query,
            top_k=self.max_chunks,
            document_ids=document_ids
        )

        formatted_chunks = []
        citations = []
        # Common query stops to ignore for lexical validation
        common_stops = {"what", "when", "where", "which", "with", "from", "that", "this", "your", "have", "more", "about", "explain", "describe", "tell", "notes", "material", "show"}
        query_terms = {w for w in re.findall(r'\b[a-zA-Z]{3,}\b', current_query.lower()) if w not in common_stops}

        for c in chunks:
            sim = c.get("score") if c.get("score") is not None else c.get("similarity_score", 0.0)
            if sim < 0.35:
                continue

            doc_title = c.get("document_title") or c.get("filename") or "Uploaded Material"
            chunk_content = c.get("content", "")
            chunk_search_text = f"{chunk_content} {doc_title}".lower()

            # Hybrid check: If query has content words and similarity is below high confidence threshold (0.65),
            # ensure at least one content term appears in the chunk text or document title
            if query_terms and sim < 0.65:
                if not any(term in chunk_search_text for term in query_terms):
                    continue

            page_info = f" (Page {c.get('page_number')})" if c.get("page_number") else ""
            heading = f" [{c.get('section_heading')}]" if c.get("section_heading") else ""
            
            formatted_chunks.append(
                f"### Excerpt from '{doc_title}'{page_info}{heading}:\n{chunk_content}"
            )
            citations.append({
                "source_type": "uploaded_document",
                "title": doc_title,
                "locator": f"Page {c.get('page_number')}" if c.get("page_number") else c.get("section_heading") or "General Excerpt",
                "snippet": chunk_content[:250],
                "document_id": c.get("document_id")
            })

        retrieved_context_str = "\n\n".join(formatted_chunks) if formatted_chunks else "No directly matching excerpts in indexed documents."

        # If no documents matched, note that answer will draw upon foundational AI knowledge
        if not citations:
            citations.append({
                "source_type": "general_knowledge",
                "title": "AI General Knowledge",
                "locator": "Foundational Model Knowledge",
                "snippet": "Synthesized from core educational and foundational concepts."
            })

        # 4. Check memory retention for concepts mentioned in query
        weak_topics = self.db.query(TopicMemoryState, Topic).join(
            Topic, TopicMemoryState.topic_id == Topic.id
        ).filter(
            TopicMemoryState.user_id == user_id,
            TopicMemoryState.status.in_(["unlearned", "review_due"])
        ).limit(4).all()

        weak_topic_names = [t.canonical_name for _, t in weak_topics]
        weak_str = ", ".join(weak_topic_names) if weak_topic_names else "All active concepts up to date."

        # 5. Format conversation history (bounded to last N turns)
        history_lines = []
        bounded_history = conversation_history[-self.max_history_turns:]
        for turn in bounded_history:
            role = "Learner" if turn.get("role") == "user" else "AI Tutor"
            history_lines.append(f"{role}: {turn.get('content', '')}")
        history_str = "\n".join(history_lines) if history_lines else "None (New conversation start)."

        # 6. Synthesize the context
        prompt = f"""{AGENT_SYSTEM_PROMPT}

---
### LEARNER PROFILE & PERSISTED PREFERENCES:
- Learner Name: {user_name}
- Educational Track / Roles: {', '.join(roles)}
- Degree & Branch: {college_degree}{f' ({college_field})' if college_field else ''}{' (Unspecified degree)' if not college_degree and not college_field else ''}
- School / Academic Level: {f'{class_grade} ({academic_year})' if class_grade else 'Not specified'}
- Professional Context: {f'{prof_role} ({prof_industry})' if prof_role else 'Not specified'}
- Target Exam: {target_exam}
- Curriculum: {curriculum}
- Primary Learning Goals: {', '.join(goals)}
- Subjects of Interest / Active Tracks: {', '.join(all_subjects) if all_subjects else 'General Exploration'}
- Explanation Depth Preference: {depth}
- Teaching Style Preferences: {', '.join(teaching_styles)}
- Custom Instructions / Directives: {custom_instructions or 'None'}
- Upcoming Exam Deadlines:
{exam_str}
- Currently Fragile / Review-Due Topics: {weak_str}

---
### RELEVANT INDEXED STUDY MATERIALS (GROUND TRUTH):
{retrieved_context_str}

---
### RECENT CONVERSATION HISTORY (BOUNDED CONTEXT):
{history_str}

---
### CURRENT USER MESSAGE:
Learner: {current_query}

### RESPONSE DIRECTIVES:
1. If the learner asks about their preferences, background, or what you know about them (e.g. "What do you know about my learning preferences?"), directly, accurately, and politely summarize their exact persisted profile attributes above (degree/branch, goals, target exam, active subjects, and preferred explanation style).
2. For academic questions without uploaded sources (e.g., "Explain Newton's third law in simple words"), deliver an intelligent, crystal-clear, pedagogical explanation drawing upon foundational academic knowledge.
3. If the user follows up in Hindi or Hinglish (e.g., "Ab iska rocket wala example samjhao"), respond naturally in conversational code-mixed Hinglish or Hindi while keeping scientific formulas and concepts intact.
4. If relevant source excerpts are present above, cite them with precision. If no source chunks match, clearly provide the conceptual explanation from foundational knowledge.
AI Tutor:"""

        metadata = {
            "target_exam": target_exam,
            "depth": depth,
            "chunks_retrieved": len(chunks),
            "history_turns_included": len(bounded_history),
            "has_uploaded_sources": bool(chunks)
        }

        return prompt, citations, metadata
