import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __name__ = "users"
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True) # Optional for simple demo mode
    is_active = Column(Boolean, default=True)
    is_demo_user = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    flashcard_decks = relationship("FlashcardDeck", back_populates="user", cascade="all, delete-orphan")
    mind_maps = relationship("MindMap", back_populates="user", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    learning_events = relationship("LearningEvent", back_populates="user", cascade="all, delete-orphan")
    topic_memory_states = relationship("TopicMemoryState", back_populates="user", cascade="all, delete-orphan")
    study_tasks = relationship("StudyTask", back_populates="user", cascade="all, delete-orphan")
    captures = relationship("CaptureItem", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("AgentConversation", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(100), nullable=True)

    user = relationship("User", back_populates="sessions")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_roles = Column(JSON, default=list) # Multi-select: e.g. ["school_student", "competitive_aspirant", "other"]
    learning_goals = Column(String(500), default="Master core academic topics and prepare for exams")
    learning_goals_list = Column(JSON, default=list) # Multi-select: e.g. ["jee_prep", "cbse_prep", "other"]
    target_exam = Column(String(100), default="") # e.g. "JEE Advanced", "CBSE 12th Board", "NEET"
    curriculum = Column(String(100), default="") # e.g. "CBSE", "ICSE", "State Board"
    learning_context = Column(JSON, default=dict) # conditional details: class_grade, target_year, stage, profession
    subjects_of_interest = Column(JSON, default=list) # e.g. ["Physics", "Chemistry", "Mathematics", "Biology"]
    explanation_depth = Column(String(50), default="balanced") # simple, balanced, detailed, academic
    teaching_styles = Column(JSON, default=list) # Multi-select: ["examples_first", "step_by_step", "visual", "analogies", "exam_focused"]
    preferred_formats = Column(JSON, default=list) # ["summaries", "quizzes", "flashcards", "mind_maps"]
    graph_detail_level = Column(String(20), default="semi-detailed") # brief, semi-detailed, detailed
    mindmap_detail_level = Column(String(20), default="semi-detailed") # brief, semi-detailed, detailed
    custom_other_responses = Column(JSON, default=dict) # key-value for "other" text inputs: {"role_other": "...", "goal_other": "...", etc.}
    language = Column(String(20), default="en")
    daily_study_time_minutes = Column(Integer, default=45)
    notifications_enabled = Column(Boolean, default=True)
    quiet_hours_start = Column(String(5), default="22:00")
    quiet_hours_end = Column(String(5), default="08:00")
    quiz_difficulty = Column(String(20), default="adaptive") # easy, medium, hard, adaptive
    preferred_study_hours = Column(String(50), default="evening") # morning, afternoon, evening, night
    notification_categories = Column(JSON, default=list) # ["review_due", "weak_recall", "upcoming_exams", "unlearned_topics", "study_materials"]
    auto_review_reminders = Column(Boolean, default=True)
    auto_quiz_prep = Column(Boolean, default=True)
    auto_exam_revision = Column(Boolean, default=True)
    custom_subjects = Column(JSON, default=list)
    custom_instructions = Column(Text, default="")
    onboarding_completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), default="")
    color = Column(String(20), default="#4f46e5")
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="categories")
    documents = relationship("Document", back_populates="category")
    notes = relationship("Note", back_populates="category")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # pdf, docx, txt, md, manual
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, default=0)
    processing_status = Column(String(50), default="pending") # pending, processing, completed, failed
    resource_prep_status = Column(String(50), default="pending") # pending, processing, completed, failed
    coverage_summary = Column(Text, default="{}")
    error_message = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    category = relationship("Category", back_populates="documents")
    chunks = relationship("SourceChunk", back_populates="document", cascade="all, delete-orphan")
    topics = relationship("DocumentTopic", back_populates="document", cascade="all, delete-orphan")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    char_count = Column(Integer, default=0)
    section_heading = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    chunk_id = Column(String(36), ForeignKey("source_chunks.id", ondelete="CASCADE"), nullable=False, unique=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_json = Column(Text, nullable=False)
    dimension = Column(Integer, nullable=False)
    model_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunk = relationship("SourceChunk", back_populates="embedding")
    document = relationship("Document")
    user = relationship("User")



class Topic(Base):
    __tablename__ = "topics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    canonical_name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    aliases = Column(JSON, default=list) # synonyms, alternative spellings
    topic_type = Column(String(50), default="concept") # concept, principle, algorithm, theory, fact
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Document associations
    document_associations = relationship("DocumentTopic", back_populates="topic", cascade="all, delete-orphan")
    memory_state = relationship("TopicMemoryState", back_populates="topic", uselist=False, cascade="all, delete-orphan")


class DocumentTopic(Base):
    __tablename__ = "document_topics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Float, default=1.0)
    evidence_snippet = Column(Text, default="")

    document = relationship("Document", back_populates="topics")
    topic = relationship("Topic", back_populates="document_associations")


class TopicRelationship(Base):
    __tablename__ = "topic_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    target_topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(100), default="relates_to") # prerequisite_of, builds_on, contrast_with, part_of, relates_to
    confidence = Column(Float, default=0.8)
    evidence_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class TopicMemoryState(Base):
    __tablename__ = "topic_memory_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(50), default="unlearned") # unlearned, learned, review_due, overdue, relearning, muted
    stability = Column(Float, default=1.0) # in days
    difficulty = Column(Float, default=0.3) # 0.0 (easy) to 1.0 (hard)
    recall_accuracy = Column(Float, default=0.0) # 0.0 to 1.0
    total_reviews = Column(Integer, default=0)
    successful_reviews = Column(Integer, default=0)
    last_learned_at = Column(DateTime, nullable=True)
    last_recalled_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    estimated_retention = Column(Float, default=1.0) # estimated % retention today
    is_muted = Column(Boolean, default=False)
    no_need_suppressed = Column(Boolean, default=False) # Permanent suppression via 'No Need'
    suppressed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    user = relationship("User", back_populates="topic_memory_states")
    topic = relationship("Topic", back_populates="memory_state")


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False) # study_session, ai_tutor, quiz_attempt, flashcard_review
    duration_seconds = Column(Integer, default=0)
    score = Column(Float, nullable=True) # 0.0 to 1.0 if quiz or flashcard rating
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="learning_events")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500), default="")
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    difficulty = Column(String(50), default="medium")
    questions = Column(JSON, default=list) 
    # questions schema: [{ id, question, type: 'mcq'|'tf'|'short', options: [], correct_answer, explanation, source_chunk_id }]
    created_at = Column(DateTime, default=datetime.utcnow)

    topic = relationship("Topic")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quiz_id = Column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score_percentage = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    user_answers = Column(JSON, default=dict) # { question_id: { answer, is_correct, feedback } }
    weak_topics_identified = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    quiz = relationship("Quiz", back_populates="attempts")


class DocumentConceptInventory(Base):
    __tablename__ = "document_concept_inventories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    outline_json = Column(JSON, default=list) # [{ section_index, heading, page_number, chunk_ids }]
    concepts_json = Column(JSON, default=list) # [{ concept_id, name, type, definition, section_heading, chunk_id }]
    sections_count = Column(Integer, default=0)
    concepts_count = Column(Integer, default=0)
    status = Column(String(50), default="verified") # verified, partial, unreadable
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document")
    user = relationship("User")


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(500), default="")
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    detail_level = Column(String(50), default="semi-detailed") # brief, semi-detailed, detailed
    version = Column(Integer, default=1)
    section_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="flashcard_decks")
    cards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    deck_id = Column(String(36), ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    hint = Column(String(255), default="")
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    detail_level = Column(String(50), default="semi-detailed") # brief, semi-detailed, detailed
    concept_id = Column(String(100), nullable=True)
    section_name = Column(String(255), nullable=True)
    source_citation = Column(String(255), nullable=True)
    stability = Column(Float, default=1.0)
    difficulty = Column(Float, default=0.3)
    reps = Column(Integer, default=0)
    lapses = Column(Integer, default=0)
    next_review_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    deck = relationship("FlashcardDeck", back_populates="cards")


class MindMap(Base):
    __tablename__ = "mind_maps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    central_topic = Column(String(200), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    structure_json = Column(JSON, default=dict) # Nodes and edges formatted for React Flow
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="mind_maps")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(String(50), default="user") # user, ai_tutor, summary
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")
    category = relationship("Category", back_populates="notes")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(200), nullable=False)
    exam_date = Column(DateTime, nullable=False)
    exam_time_str = Column(String(50), default="")
    location = Column(String(200), default="")
    syllabus_summary = Column(Text, default="")
    total_preparation_days = Column(Integer, default=7)
    confidence_level = Column(String(50), default="moderate") # low, moderate, high
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="exams")
    study_tasks = relationship("StudyTask", back_populates="exam", cascade="all, delete-orphan")


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id = Column(String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500), default="")
    scheduled_for = Column(DateTime, nullable=False)
    allocated_minutes = Column(Integer, default=30)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    priority = Column(String(20), default="medium") # high, medium, low
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="study_tasks")
    exam = relationship("Exam", back_populates="study_tasks")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="review_due") 
    # document_processed, document_failed, quiz_completed, weak_topics_identified,
    # exam_alert, exam_tomorrow, review_due, high_forgetting_risk, weak_recall,
    # mindmap_ready, mindmap_failed, task_deadline, system_notice
    action_url = Column(String(255), default="/learn")
    entity_type = Column(String(50), nullable=True) # document, quiz, exam, topic, mind_map, study_task, system
    entity_id = Column(String(36), nullable=True)
    priority = Column(String(20), default="normal") # low, normal, high, urgent
    is_read = Column(Boolean, default=False)
    is_snoozed = Column(Boolean, default=False)
    snooze_until = Column(DateTime, nullable=True)
    is_dismissed = Column(Boolean, default=False)
    action_state = Column(String(50), default="active") # active, started, dismissed, snoozed, no_need
    last_action_at = Column(DateTime, nullable=True)
    dedup_key = Column(String(255), nullable=True, index=True)
    scheduled_for = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")



class CaptureItem(Base):
    __tablename__ = "capture_inbox"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False) # 'web_url', 'selection', 'extension', 'share_target', 'file', 'image'
    source_url = Column(String(1000), nullable=True)
    title = Column(String(255), nullable=False)
    content_text = Column(Text, nullable=False)
    cleaned_html = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True) # If file or image was temporarily stored
    file_type = Column(String(50), nullable=True) # pdf, docx, txt, md, image, etc.
    file_size_bytes = Column(Integer, default=0)
    recommended_category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    recommended_category_name = Column(String(100), nullable=True)
    recommendation_confidence = Column(Float, default=0.0) # 0.0 to 1.0 heuristic
    recommendation_reason = Column(String(255), nullable=True)
    alternative_categories = Column(JSON, default=list) # List of alternative category dicts
    status = Column(String(50), default="pending_review") # pending_review, confirmed, discarded, failed
    error_message = Column(Text, nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True) # When confirmed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="captures")
    recommended_category = relationship("Category")
    document = relationship("Document")


class WebPushSubscription(Base):
    __tablename__ = "web_push_subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class AgentConversation(Base):
    """
    Persistent conversational study session for the AI Learning Agent.
    """
    __tablename__ = "agent_conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Study Session")
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    topic = relationship("Topic")
    messages = relationship("AgentMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AgentMessage.created_at.asc()")


class AgentMessage(Base):
    """
    Individual turn within an agent conversation.
    Tracks role, structured tool calls, citations, and execution metadata.
    """
    __tablename__ = "agent_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False) # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, default=list) # [{ id, name, args }]
    tool_call_id = Column(String(100), nullable=True) # for role='tool'
    citations = Column(JSON, default=list) # [{ source_type, title, locator, url, snippet }]
    meta = Column(JSON, default=dict) # token usage, latency, model used, language
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("AgentConversation", back_populates="messages")



