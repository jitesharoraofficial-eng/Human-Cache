from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- User & Auth Schemas ---
class UserBase(BaseModel):
    email: str
    name: str

class UserCreate(UserBase):
    password: Optional[str] = None

class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=4, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)

class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

class AuthResponse(BaseModel):
    message: str
    user: Dict[str, Any]
    session_token: Optional[str] = None

class UserPreferencesUpdate(BaseModel):
    user_roles: Optional[List[str]] = None
    learning_goals: Optional[str] = None
    learning_goals_list: Optional[List[str]] = None
    target_exam: Optional[str] = None
    curriculum: Optional[str] = None
    learning_context: Optional[Dict[str, Any]] = None
    subjects_of_interest: Optional[List[str]] = None
    explanation_depth: Optional[str] = "balanced"
    teaching_styles: Optional[List[str]] = None
    preferred_formats: Optional[List[str]] = None
    graph_detail_level: Optional[str] = "semi-detailed"
    mindmap_detail_level: Optional[str] = "semi-detailed"
    custom_other_responses: Optional[Dict[str, Any]] = None
    language: Optional[str] = "en"
    daily_study_time_minutes: Optional[int] = 45
    notifications_enabled: Optional[bool] = True
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    quiz_difficulty: Optional[str] = "adaptive"
    preferred_study_hours: Optional[str] = "evening"
    notification_categories: Optional[List[str]] = None
    auto_review_reminders: Optional[bool] = True
    auto_quiz_prep: Optional[bool] = True
    auto_exam_revision: Optional[bool] = True
    custom_subjects: Optional[List[str]] = None
    custom_instructions: Optional[str] = ""
    onboarding_completed: Optional[bool] = True

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    preferences: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# --- Category Schemas ---
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    color: Optional[str] = "#4f46e5"

class CategoryResponse(CategoryCreate):
    id: str
    user_id: str
    is_archived: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Document Schemas ---
class DocumentCreateManual(BaseModel):
    title: str
    category_id: Optional[str] = None
    content: str

class DocumentResponse(BaseModel):
    id: str
    user_id: str
    category_id: Optional[str] = None
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    processing_status: str
    error_message: Optional[str] = None
    version: int
    is_demo: bool
    created_at: datetime
    extracted_topics_count: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Topic & Graph Schemas ---
class TopicResponse(BaseModel):
    id: str
    name: str
    canonical_name: str
    description: str
    aliases: List[str] = []
    topic_type: str
    is_demo: bool
    memory_status: Optional[str] = "unlearned"
    estimated_retention: Optional[float] = 1.0
    stability_days: Optional[float] = 1.0
    next_review_at: Optional[datetime] = None
    is_muted: Optional[bool] = False

    class Config:
        from_attributes = True

class TopicRelationshipResponse(BaseModel):
    id: str
    source_topic_id: str
    target_topic_id: str
    relationship_type: str
    confidence: float
    evidence_text: str

    class Config:
        from_attributes = True

class KnowledgeGraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    stats: Dict[str, Any]

# --- Learn & AI Tutoring Schemas ---
class LearnRequest(BaseModel):
    topic_ids: Optional[List[str]] = []
    document_ids: Optional[List[str]] = []
    query: Optional[str] = None
    depth: Optional[str] = "balanced" # simple, balanced, detailed, academic
    mode: Optional[str] = "explain" # explain, analogy, step_by_step, examples, qa
    persona_override: Optional[str] = None # e.g. "jee_aspirant", "cbse_student", "beginner", "professional"

class LearnResponse(BaseModel):
    topic_name: str
    explanation: str
    prerequisites: List[str] = []
    analogies: List[str] = []
    key_takeaways: List[str] = []
    follow_up_questions: List[str] = []
    grounded_sources: List[Dict[str, Any]] = []
    persona_mode_indicator: Optional[str] = "Personalized"
    exam_traps: Optional[List[str]] = []
    coverage_status: Optional[str] = "verified"
    covered_concepts: Optional[List[str]] = []
    missing_concepts: Optional[List[str]] = []
    detail_level: Optional[str] = "semi-detailed"

class SaveLearnAsNoteRequest(BaseModel):
    topic_id: Optional[str] = None
    document_id: Optional[str] = None
    category_id: Optional[str] = None
    title: str
    content: str

class TutorChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = []
    document_ids: Optional[List[str]] = []

class TutorChatResponse(BaseModel):
    reply: str
    citations: List[str] = []
    is_grounded: bool = False


# --- Recall & Quiz Schemas ---
class QuizGenerateRequest(BaseModel):
    topic_ids: Optional[List[str]] = []
    document_ids: Optional[List[str]] = []
    category_id: Optional[str] = None
    question_count: int = 4
    difficulty: str = "medium"

class QuizQuestion(BaseModel):
    id: str
    question: str
    type: str # mcq, tf, short
    options: Optional[List[str]] = []
    correct_answer: str
    explanation: str
    topic_id: Optional[str] = None
    source_chunk_snippet: Optional[str] = None

class QuizResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    topic_id: Optional[str] = None
    questions: List[Dict[str, Any]]
    created_at: datetime

class QuizSubmitRequest(BaseModel):
    quiz_id: str
    user_answers: Dict[str, str] # { question_id: selected_or_typed_answer }

class QuizSubmitResponse(BaseModel):
    attempt_id: str
    quiz_id: str
    score_percentage: float
    total_questions: int
    correct_count: int
    results: Dict[str, Any]
    weak_topics: List[str] = []
    next_review_suggestion: str

# --- Flashcard Schemas ---
class FlashcardCreate(BaseModel):
    deck_id: str
    front: str
    back: str
    hint: Optional[str] = ""
    topic_id: Optional[str] = None
    detail_level: Optional[str] = "semi-detailed"
    concept_id: Optional[str] = None
    section_name: Optional[str] = None
    source_citation: Optional[str] = None

class FlashcardDeckCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    topic_id: Optional[str] = None
    document_id: Optional[str] = None
    detail_level: Optional[str] = "semi-detailed"
    version: Optional[int] = 1

class FlashcardGenerateRequest(BaseModel):
    topic_id: str
    detail_level: Optional[str] = "semi-detailed"
    card_count: Optional[int] = None

class FlashcardReviewRequest(BaseModel):
    rating: int # 1 = Again (failed), 2 = Hard, 3 = Good, 4 = Easy

# --- Mind Map Schemas ---
class MindMapGenerateRequest(BaseModel):
    central_topic: str
    topic_id: Optional[str] = None
    document_id: Optional[str] = None
    detail_level: Optional[str] = "semi-detailed" # brief, semi-detailed, detailed

class MindMapResponse(BaseModel):
    id: str
    title: str
    central_topic: str
    structure_json: Dict[str, Any]
    created_at: datetime

# --- Exam Schemas ---
class ExamCreate(BaseModel):
    subject: str
    exam_date: datetime
    exam_time_str: Optional[str] = ""
    location: Optional[str] = ""
    syllabus_summary: Optional[str] = ""
    total_preparation_days: Optional[int] = 7

class DateSheetExtractResponse(BaseModel):
    extracted_exams: List[Dict[str, Any]]
    confidence: str
    raw_snippet: str

class GenerateStudyPlanRequest(BaseModel):
    exam_id: str
    daily_available_minutes: Optional[int] = 60

# --- Note Schemas ---
class NoteCreate(BaseModel):
    title: str
    content: str
    category_id: Optional[str] = None
    topic_id: Optional[str] = None
    document_id: Optional[str] = None
    tags: Optional[List[str]] = []

class NoteResponse(NoteCreate):
    id: str
    user_id: str
    source_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Notification Schemas ---
class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    action_url: str
    is_read: bool
    is_snoozed: bool
    snooze_until: Optional[datetime] = None
    action_state: Optional[str] = "active"
    last_action_at: Optional[datetime] = None
    created_at: datetime
    topic_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    priority: Optional[str] = "normal"
    scheduled_for: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class SnoozeNotificationRequest(BaseModel):
    snooze_minutes: int = 60

class WebPushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: Optional[str] = ""

class WebPushSubscriptionResponse(BaseModel):
    id: str
    endpoint: str
    created_at: datetime

class SuppressedTopicResponse(BaseModel):
    topic_id: str
    canonical_name: str
    suppressed_at: Optional[datetime] = None
    category_name: Optional[str] = None
    stability_days: float = 1.0


# --- Dashboard & Analytics Schemas ---
class DashboardOverviewResponse(BaseModel):
    welcome_name: str
    daily_study_focus: str
    cognitive_focus_prompt: Optional[str] = None
    cognitive_focus_message: Optional[str] = None
    total_documents: int
    total_categories: int
    topics_discovered: int
    topics_learned: int
    topics_left_to_learn: int
    review_due_count: int
    overdue_count: int
    retention_average: float
    learning_streak_days: int
    flashcard_count: Optional[int] = 0
    mind_map_count: Optional[int] = 0
    note_count: Optional[int] = 0
    today_tasks: List[Dict[str, Any]]
    upcoming_exams: List[Dict[str, Any]]
    review_due_topics: List[Dict[str, Any]]
    learn_again_topics: List[Dict[str, Any]]
    left_to_learn_topics: Optional[List[Dict[str, Any]]] = []
    recent_activity: List[Dict[str, Any]]


# --- Capture & Ingestion Schemas ---
class CaptureTextRequest(BaseModel):
    title: Optional[str] = None
    content_text: str
    source_type: str = "selection" # selection, extension, share_target, paste
    source_url: Optional[str] = None

class CaptureUrlRequest(BaseModel):
    url: str
    source_type: str = "web_url" # web_url, extension, share_target
    title: Optional[str] = None
    page_content: Optional[str] = None

class CaptureResponse(BaseModel):
    id: str
    user_id: str
    source_type: str
    source_url: Optional[str] = None
    title: str
    content_preview: str
    file_type: Optional[str] = None
    file_size_bytes: int = 0
    recommended_category_id: Optional[str] = None
    recommended_category_name: Optional[str] = None
    recommendation_confidence: float = 0.0
    recommendation_reason: Optional[str] = None
    alternative_categories: Optional[List[Dict[str, Any]]] = []
    status: str
    error_message: Optional[str] = None
    document_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CaptureConfirmRequest(BaseModel):
    category_id: Optional[str] = None # Selected existing category ID
    new_category_name: Optional[str] = None # If creating new category
    custom_title: Optional[str] = None # User edited title if desired


# --- Agent & Persistent Conversations Schemas ---
class AgentCitation(BaseModel):
    source_type: str # "uploaded_document" | "general_knowledge" | "learner_history"
    title: str
    locator: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None

class AgentMessageCreate(BaseModel):
    content: str
    language: Optional[str] = "auto"
    document_ids: Optional[List[str]] = None

class AgentMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = []
    tool_call_id: Optional[str] = None
    citations: Optional[List[AgentCitation]] = []
    meta: Optional[Dict[str, Any]] = {}
    created_at: datetime

    class Config:
        from_attributes = True

class AgentConversationCreate(BaseModel):
    title: Optional[str] = None
    topic_id: Optional[str] = None

class AgentConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None

class AgentConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    topic_id: Optional[str] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    messages: Optional[List[AgentMessageResponse]] = None

    class Config:
        from_attributes = True

class AgentToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None

class AgentToolInfo(BaseModel):
    name: str
    description: str
    is_consequential: bool = False
    requires_confirmation: bool = False
    parameters: List[AgentToolParameter] = []

class AgentToolExecuteRequest(BaseModel):
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = {}
    confirmed: bool = False

class AgentToolExecuteResponse(BaseModel):
    tool_name: str
    success: bool
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

