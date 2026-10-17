import os
import shutil
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import engine, Base, get_db
from backend.models import (
    User, UserSession, UserPreference, Category, Document, SourceChunk,
    Topic, DocumentTopic, TopicRelationship, TopicMemoryState, LearningEvent,
    Quiz, QuizAttempt, FlashcardDeck, Flashcard, MindMap, Note,
    Exam, StudyTask, Notification, CaptureItem, WebPushSubscription,
    AgentConversation, AgentMessage
)
from backend.schemas import (
    UserRegisterRequest, UserLoginRequest, AuthResponse,
    UserCreate, UserResponse, UserPreferencesUpdate,
    CategoryCreate, CategoryResponse, DocumentCreateManual, DocumentResponse,
    TopicResponse, KnowledgeGraphResponse,
    LearnRequest, LearnResponse, SaveLearnAsNoteRequest,
    TutorChatRequest, TutorChatResponse,
    QuizGenerateRequest, QuizResponse, QuizSubmitRequest, QuizSubmitResponse,
    FlashcardCreate, FlashcardDeckCreate, FlashcardReviewRequest,
    MindMapGenerateRequest, MindMapResponse,
    ExamCreate, DateSheetExtractResponse, GenerateStudyPlanRequest,
    NoteCreate, NoteResponse, NotificationResponse, SnoozeNotificationRequest,
    DashboardOverviewResponse,
    CaptureTextRequest, CaptureUrlRequest, CaptureResponse, CaptureConfirmRequest,
    WebPushSubscriptionCreate, WebPushSubscriptionResponse, SuppressedTopicResponse,
    AgentConversationCreate, AgentConversationUpdate, AgentConversationResponse,
    AgentMessageCreate, AgentMessageResponse, AgentToolInfo,
    AgentToolExecuteRequest, AgentToolExecuteResponse
)
from backend.agent.conversation_service import AgentConversationService
from backend.agent.tools import tool_registry
from backend.url_capture_service import fetch_url_content_ssrf_safe, validate_target_url
from backend.category_recommender import recommend_category_for_content

from backend.extractor import (
    extract_text_from_file, extract_topics_and_concepts,
    extract_raw_pages_and_text, chunk_pages_and_text,
    compute_page_coverage
)
from backend.file_security import stream_save_and_validate, sanitize_filename
import time
import json
import logging
from backend.logging_config import setup_secure_logging

setup_secure_logging()
logger = logging.getLogger("human_cache")
from backend.graph_engine import build_user_knowledge_graph, connect_new_topics_heuristic, get_concept_details_payload
from backend.memory_engine import (
    update_memory_on_learning, update_memory_on_recall,
    refresh_user_memory_states, calculate_current_retention
)
from backend.ai_engine import AITutorEngine
from backend.exam_planner import parse_date_sheet_text, generate_exam_revision_plan
from backend.notification_engine import (
    run_proactive_notification_cycle, handle_start_notification,
    handle_dismiss_notification, handle_snooze_notification,
    handle_no_need_notification, handle_unmute_concept, handle_mute_topic,
    dispatch_notification, handle_mark_read_notification, handle_mark_all_read
)
from backend.scheduler import memory_coach_scheduler
from backend.seed_data import seed_demo_data, DEMO_USER_ID, DEMO_USER_EMAIL
from backend.personalization_focus import generate_dashboard_focus
from backend.ai.generation import RAGIntelligenceEngine
from backend.ai.retrieval import RetrievalService
from backend.auth import (
    hash_password, verify_password, create_session,
    invalidate_session, get_session_token_from_request, get_current_user
)
from backend.resource_prep_service import auto_prepare_document_learning_suite


def run_background_resource_prep(user_id: str, document_id: str):
    """
    Background worker task to idempotently assemble quizzes, flashcards,
    mind maps, and summary notes for newly ingested documents.
    """
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        auto_prepare_document_learning_suite(db, user_id, document_id)
    except Exception as e:
        logger.warning(f"Background learning suite preparation failed for doc {document_id}: {e}")
    finally:
        db.close()


# Initialize tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Enable CORS for frontend with credentials and explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^(chrome-extension|moz-extension|edge-extension)://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Simple in-memory rate limiting for sensitive auth endpoints (login, register)
AUTH_RATE_LIMIT_STORE: Dict[str, List[datetime]] = {}

def check_auth_rate_limit(client_ip: str, max_requests: int = 10, window_seconds: int = 60):
    now = datetime.utcnow()
    timestamps = AUTH_RATE_LIMIT_STORE.get(client_ip, [])
    # Filter out requests outside the window
    timestamps = [t for t in timestamps if (now - t).total_seconds() < window_seconds]
    if len(timestamps) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please try again in a few moments."
        )
    timestamps.append(now)
    AUTH_RATE_LIMIT_STORE[client_ip] = timestamps

@app.on_event("startup")
def on_startup():
    try:
        db = next(get_db())
        try:
            seed_demo_data(db)
            refresh_user_memory_states(db, DEMO_USER_ID)
            run_proactive_notification_cycle(db, DEMO_USER_ID)
        finally:
            db.close()
    except Exception as e:
        print(f"Startup demo data check: {e}")

    # Launch proactive background scheduler
    try:
        memory_coach_scheduler.start()
    except Exception as e:
        print(f"Scheduler startup skipped: {e}")

@app.on_event("shutdown")
def on_shutdown():
    try:
        memory_coach_scheduler.stop()
    except Exception as e:
        print(f"Scheduler shutdown error: {e}")

# Helper dependency to resolve user_id safely from authenticated user
def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    return current_user.id

# --- 1. HEALTH CHECKS & SYSTEM ---
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Human Cache API",
        "llm_provider": "gemini" if settings.GEMINI_API_KEY else "local-deterministic-academic",
        "storage": "local-disk",
        "timestamp": datetime.utcnow().isoformat()
    }

# --- 2. AUTHENTICATION ENDPOINTS ---
@app.post(f"{settings.API_V1_STR}/auth/register", response_model=AuthResponse)
def register_user(
    payload: UserRegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(client_ip, max_requests=10, window_seconds=60)

    clean_email = payload.email.strip().lower()
    clean_name = payload.name.strip()

    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address format.")
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    # Check email uniqueness
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    hashed_pw = hash_password(payload.password)
    new_user = User(
        email=clean_email,
        name=clean_name,
        hashed_password=hashed_pw,
        is_active=True,
        is_demo_user=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initialize empty preferences for the new user
    pref = UserPreference(
        user_id=new_user.id,
        onboarding_completed=False
    )
    db.add(pref)
    db.commit()

    # Create session
    raw_token, _ = create_session(
        db,
        user_id=new_user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip
    )

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    return AuthResponse(
        message="Registration successful.",
        user={
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "onboarding_completed": False
        },
        session_token=raw_token
    )

@app.post(f"{settings.API_V1_STR}/auth/login", response_model=AuthResponse)
def login_user(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(client_ip, max_requests=10, window_seconds=60)

    clean_email = payload.email.strip().lower()

    # Generic error message to prevent account enumeration
    invalid_credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password."
    )

    user = db.query(User).filter(User.email == clean_email).first()
    if not user and clean_email == "demo@humancache.ai":
        user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()

    if not user or not user.is_active:
        raise invalid_credentials_exc

    if not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials_exc

    user.last_login_at = datetime.utcnow()
    db.commit()

    # Create session
    raw_token, _ = create_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip
    )

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    prefs = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()

    return AuthResponse(
        message="Login successful.",
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "onboarding_completed": prefs.onboarding_completed if prefs else False
        },
        session_token=raw_token
    )

@app.get(f"{settings.API_V1_STR}/auth/me")
def get_auth_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
        "is_demo_user": current_user.is_demo_user,
        "onboarding_completed": prefs.onboarding_completed if prefs else False,
        "role": (prefs.user_roles[0].replace("_", " ").title() if prefs and prefs.user_roles else "Learner"),
        "target_exam": prefs.target_exam if prefs else ""
    }

@app.post(f"{settings.API_V1_STR}/auth/logout")
def logout_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    raw_token = get_session_token_from_request(request)
    if raw_token:
        invalidate_session(db, raw_token)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/"
    )
    return {"message": "Successfully logged out."}

@app.post(f"{settings.API_V1_STR}/demo/reset")
def reset_demo_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes and re-seeds the pristine demo workspace for the demo user only."""
    if not current_user.is_demo_user and current_user.id != DEMO_USER_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset is restricted to demo accounts."
        )
    # Remove existing demo data
    db.query(Notification).filter(Notification.user_id == DEMO_USER_ID).delete()
    db.query(StudyTask).filter(StudyTask.user_id == DEMO_USER_ID).delete()
    db.query(Exam).filter(Exam.user_id == DEMO_USER_ID).delete()
    db.query(Note).filter(Note.user_id == DEMO_USER_ID).delete()
    db.query(MindMap).filter(MindMap.user_id == DEMO_USER_ID).delete()
    db.query(Flashcard).join(FlashcardDeck).filter(FlashcardDeck.user_id == DEMO_USER_ID).delete()
    db.query(FlashcardDeck).filter(FlashcardDeck.user_id == DEMO_USER_ID).delete()
    db.query(QuizAttempt).filter(QuizAttempt.user_id == DEMO_USER_ID).delete()
    db.query(Quiz).filter(Quiz.user_id == DEMO_USER_ID).delete()
    db.query(TopicMemoryState).filter(TopicMemoryState.user_id == DEMO_USER_ID).delete()
    db.query(TopicRelationship).filter(TopicRelationship.user_id == DEMO_USER_ID).delete()
    db.query(DocumentTopic).delete()
    db.query(Topic).filter(Topic.user_id == DEMO_USER_ID).delete()
    db.query(SourceChunk).delete()
    db.query(Document).filter(Document.user_id == DEMO_USER_ID).delete()
    db.query(Category).filter(Category.user_id == DEMO_USER_ID).delete()
    db.commit()

    seed_demo_data(db)
    refresh_user_memory_states(db, DEMO_USER_ID)
    run_proactive_notification_cycle(db, DEMO_USER_ID)
    return {"message": "Demo workspace successfully reset to initial pristine state."}

# --- 2. AUTH & USER PROFILE ---
@app.get(f"{settings.API_V1_STR}/users/me")
def get_user_profile(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_active": user.is_active,
        "preferences": {
            "user_roles": prefs.user_roles if prefs else [],
            "learning_goals": prefs.learning_goals if prefs else "",
            "learning_goals_list": prefs.learning_goals_list if prefs else [],
            "target_exam": prefs.target_exam if prefs else "",
            "curriculum": prefs.curriculum if prefs else "",
            "learning_context": prefs.learning_context if prefs else {},
            "subjects_of_interest": prefs.subjects_of_interest if prefs else [],
            "explanation_depth": prefs.explanation_depth if prefs else "balanced",
            "teaching_styles": prefs.teaching_styles if prefs else [],
            "preferred_formats": prefs.preferred_formats if prefs else [],
            "graph_detail_level": prefs.graph_detail_level if prefs else "semi-detailed",
            "mindmap_detail_level": prefs.mindmap_detail_level if prefs else "semi-detailed",
            "custom_other_responses": prefs.custom_other_responses if prefs else {},
            "language": prefs.language if prefs else "en",
            "daily_study_time_minutes": prefs.daily_study_time_minutes if prefs else 45,
            "notifications_enabled": prefs.notifications_enabled if prefs else True,
            "quiet_hours_start": prefs.quiet_hours_start if prefs else "22:00",
            "quiet_hours_end": prefs.quiet_hours_end if prefs else "08:00",
            "quiz_difficulty": prefs.quiz_difficulty if prefs else "adaptive",
            "preferred_study_hours": prefs.preferred_study_hours if prefs else "evening",
            "notification_categories": prefs.notification_categories if prefs else ["review_due", "weak_recall", "upcoming_exams"],
            "auto_review_reminders": prefs.auto_review_reminders if prefs else True,
            "auto_quiz_prep": prefs.auto_quiz_prep if prefs else True,
            "auto_exam_revision": prefs.auto_exam_revision if prefs else True,
            "custom_subjects": prefs.custom_subjects if prefs else [],
            "custom_instructions": prefs.custom_instructions if prefs else "",
            "onboarding_completed": prefs.onboarding_completed if prefs else False
        }
    }

@app.put(f"{settings.API_V1_STR}/users/preferences")
def update_user_preferences(payload: UserPreferencesUpdate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
    
    if payload.user_roles is not None:
        prefs.user_roles = payload.user_roles
    if payload.learning_goals is not None:
        prefs.learning_goals = payload.learning_goals
    if payload.learning_goals_list is not None:
        prefs.learning_goals_list = payload.learning_goals_list
    if payload.target_exam is not None:
        prefs.target_exam = payload.target_exam
    if payload.curriculum is not None:
        prefs.curriculum = payload.curriculum
    if payload.learning_context is not None:
        prefs.learning_context = payload.learning_context
    if payload.subjects_of_interest is not None:
        prefs.subjects_of_interest = payload.subjects_of_interest
    if payload.explanation_depth is not None:
        prefs.explanation_depth = payload.explanation_depth
    if payload.teaching_styles is not None:
        prefs.teaching_styles = payload.teaching_styles
    if payload.preferred_formats is not None:
        prefs.preferred_formats = payload.preferred_formats
    if payload.graph_detail_level is not None:
        prefs.graph_detail_level = payload.graph_detail_level
    if payload.mindmap_detail_level is not None:
        prefs.mindmap_detail_level = payload.mindmap_detail_level
    if payload.custom_other_responses is not None:
        prefs.custom_other_responses = payload.custom_other_responses
    if payload.language is not None:
        prefs.language = payload.language
    if payload.daily_study_time_minutes is not None:
        prefs.daily_study_time_minutes = payload.daily_study_time_minutes
    if payload.notifications_enabled is not None:
        prefs.notifications_enabled = payload.notifications_enabled
    if payload.quiet_hours_start is not None:
        prefs.quiet_hours_start = payload.quiet_hours_start
    if payload.quiet_hours_end is not None:
        prefs.quiet_hours_end = payload.quiet_hours_end
    if payload.quiz_difficulty is not None:
        prefs.quiz_difficulty = payload.quiz_difficulty
    if payload.preferred_study_hours is not None:
        prefs.preferred_study_hours = payload.preferred_study_hours
    if payload.notification_categories is not None:
        prefs.notification_categories = payload.notification_categories
    if payload.auto_review_reminders is not None:
        prefs.auto_review_reminders = payload.auto_review_reminders
    if payload.auto_quiz_prep is not None:
        prefs.auto_quiz_prep = payload.auto_quiz_prep
    if payload.auto_exam_revision is not None:
        prefs.auto_exam_revision = payload.auto_exam_revision
    if payload.custom_subjects is not None:
        prefs.custom_subjects = payload.custom_subjects
    if payload.custom_instructions is not None:
        prefs.custom_instructions = payload.custom_instructions
    if payload.onboarding_completed is not None:
        prefs.onboarding_completed = payload.onboarding_completed

    # Auto-curate non-duplicate study categories based on selected subjects
    all_subjects = list(prefs.subjects_of_interest or [])
    if prefs.custom_subjects:
        all_subjects.extend(prefs.custom_subjects)
    
    if all_subjects:
        existing_cats = {c.name.strip().lower(): c for c in db.query(Category).filter(Category.user_id == user_id).all()}
        subject_palette = {
            "physics": "#38bdf8",
            "chemistry": "#10b981",
            "mathematics": "#6366f1",
            "biology": "#f43f5e",
            "computer science": "#8b5cf6",
            "programming": "#06b6d4",
            "artificial intelligence": "#ec4899",
            "business": "#f59e0b",
            "finance": "#d97706",
            "economics": "#10b981",
            "accountancy": "#eab308",
            "history": "#f97316",
            "psychology": "#a855f7",
            "political": "#6366f1",
            "geography": "#14b8a6",
            "sociology": "#f43f5e",
            "philosophy": "#8b5cf6",
            "law": "#7c3aed",
            "medical": "#ef4444",
            "anatomy": "#dc2626",
            "music": "#d946ef",
            "writing": "#0284c7",
            "speaking": "#059669",
            "art": "#ea580c",
            "general knowledge": "#64748b"
        }
        for subj in all_subjects:
            s_name = subj.strip()
            if not s_name:
                continue
            s_lower = s_name.lower()
            # Avoid duplicate if existing category contains this subject or vice versa
            already_exists = any(s_lower in ec or ec in s_lower for ec in existing_cats.keys())
            if not already_exists:
                cat_color = "#4f46e5"
                for kw, col in subject_palette.items():
                    if kw in s_lower:
                        cat_color = col
                        break
                new_cat = Category(
                    user_id=user_id,
                    name=s_name,
                    description=f"Auto-curated category for {s_name}",
                    color=cat_color
                )
                db.add(new_cat)
                existing_cats[s_lower] = new_cat

    db.commit()
    db.refresh(prefs)
    return {"message": "Preferences and study categories updated successfully."}

# --- 3. DASHBOARD OVERVIEW ---
@app.get(f"{settings.API_V1_STR}/dashboard/overview")
def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id
    refresh_user_memory_states(db, user_id)
    run_proactive_notification_cycle(db, user_id)

    total_docs = db.query(Document).filter(Document.user_id == user_id).count()
    total_cats = db.query(Category).filter(Category.user_id == user_id).count()
    topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    mem_states = db.query(TopicMemoryState).filter(TopicMemoryState.user_id == user_id).all()

    learned_count = sum(1 for m in mem_states if m.status in ["learned", "review_due", "overdue"])
    unlearned_count = sum(1 for m in mem_states if m.status == "unlearned")
    review_due_count = sum(1 for m in mem_states if m.status == "review_due")
    overdue_count = sum(1 for m in mem_states if m.status == "overdue")

    avg_retention = 0.0
    if mem_states:
        avg_retention = sum(m.estimated_retention for m in mem_states) / len(mem_states)

    today_tasks = db.query(StudyTask).filter(
        StudyTask.user_id == user_id,
        StudyTask.is_completed == False
    ).limit(5).all()

    upcoming_exams = db.query(Exam).filter(Exam.user_id == user_id).order_by(Exam.exam_date.asc()).limit(3).all()

    review_due_topics = [
        {"id": m.topic_id, "name": m.topic.canonical_name if m.topic else "Concept", "retention": m.estimated_retention, "stability": m.stability}
        for m in mem_states if m.status in ["review_due", "overdue"]
    ]

    learn_again_topics = [
        {"id": m.topic_id, "name": m.topic.canonical_name if m.topic else "Concept", "retention": m.estimated_retention}
        for m in mem_states if m.status == "relearning" or m.estimated_retention < 0.65
    ]

    left_to_learn_topics = [
        {"id": m.topic_id, "name": m.topic.canonical_name if m.topic else "Concept"}
        for m in mem_states if m.status == "unlearned"
    ]

    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    focus_data = generate_dashboard_focus(
        prefs=prefs,
        topics=topics,
        mem_states=mem_states,
        upcoming_exams=upcoming_exams,
        total_docs=total_docs
    )

    # Calculate real consecutive active study streak based on calendar days
    active_dates = set()
    quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).all()
    for qa in quiz_attempts:
        if qa.created_at:
            active_dates.add(qa.created_at.date())

    learning_events = db.query(LearningEvent).filter(LearningEvent.user_id == user_id).all()
    for le in learning_events:
        if le.created_at:
            active_dates.add(le.created_at.date())

    completed_tasks = db.query(StudyTask).filter(StudyTask.user_id == user_id, StudyTask.is_completed == True).all()
    for st in completed_tasks:
        if st.completed_at:
            active_dates.add(st.completed_at.date())

    streak = 0
    today = datetime.utcnow().date()
    check_date = today
    # Allow streak to continue if activity occurred today or yesterday
    if check_date not in active_dates:
        check_date = today - timedelta(days=1)

    while check_date in active_dates:
        streak += 1
        check_date = check_date - timedelta(days=1)

    # Compile genuine recent activity records
    activity_items = []
    for qa in quiz_attempts:
        t_name = "Knowledge Drill"
        if qa.quiz:
            if getattr(qa.quiz, "topic", None):
                t_name = qa.quiz.topic.canonical_name
            elif qa.quiz.topic_id:
                t_obj = db.query(Topic).filter(Topic.id == qa.quiz.topic_id).first()
                if t_obj:
                    t_name = t_obj.canonical_name
        score_pct = int(round((qa.score_percentage or 0) * 100)) if (qa.score_percentage or 0) <= 1.0 else int(round(qa.score_percentage or 0))
        activity_items.append({
            "action": "Active Recall Drill",
            "topic": t_name,
            "score": f"{score_pct}%",
            "timestamp": qa.created_at
        })

    user_docs = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).limit(5).all()
    for doc in user_docs:
        activity_items.append({
            "action": "Document Ingested",
            "topic": doc.title,
            "timestamp": doc.created_at
        })

    user_notes = db.query(Note).filter(Note.user_id == user_id).order_by(Note.created_at.desc()).limit(5).all()
    for note in user_notes:
        activity_items.append({
            "action": "Note Created",
            "topic": note.title,
            "timestamp": note.created_at
        })

    activity_items.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)

    def format_relative_time(dt: Optional[datetime]) -> str:
        if not dt:
            return "Recently"
        diff = datetime.utcnow() - dt
        seconds = diff.total_seconds()
        if seconds < 120:
            return "Just now"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        elif seconds < 172800:
            return "Yesterday"
        else:
            return f"{int(seconds // 86400)}d ago"

    formatted_activity = [
        {
            "action": a["action"],
            "topic": a["topic"],
            "time": format_relative_time(a.get("timestamp")),
            **({"score": a["score"]} if "score" in a else {})
        }
        for a in activity_items[:5]
    ]

    flashcard_count = db.query(Flashcard).join(FlashcardDeck).filter(FlashcardDeck.user_id == user_id).count()
    mind_map_count = db.query(MindMap).filter(MindMap.user_id == user_id).count()
    note_count = len(user_notes)
    user_first_name = current_user.name.split()[0] if current_user.name else "Learner"

    return {
        "welcome_name": user_first_name,
        "daily_study_focus": focus_data["focus_title"],
        "cognitive_focus_prompt": focus_data["focus_prompt"],
        "cognitive_focus_message": focus_data["full_message"],
        "total_documents": total_docs,
        "total_categories": total_cats,
        "topics_discovered": len(topics),
        "topics_learned": learned_count,
        "topics_left_to_learn": unlearned_count,
        "review_due_count": review_due_count,
        "overdue_count": overdue_count,
        "retention_average": round(avg_retention * 100, 1),
        "learning_streak_days": streak,
        "flashcard_count": flashcard_count,
        "mind_map_count": mind_map_count,
        "note_count": note_count,
        "today_tasks": [
            {"id": t.id, "title": t.title, "minutes": t.allocated_minutes, "priority": t.priority, "is_completed": t.is_completed}
            for t in today_tasks
        ],
        "upcoming_exams": [
            {"id": e.id, "subject": e.subject, "date": e.exam_date.strftime("%b %d, %Y"), "time": e.exam_time_str}
            for e in upcoming_exams
        ],
        "review_due_topics": review_due_topics[:5],
        "learn_again_topics": learn_again_topics[:5],
        "left_to_learn_topics": left_to_learn_topics[:5],
        "recent_activity": formatted_activity
    }

# --- 4. CATEGORIES & FILE UPLOADS ---
@app.get(f"{settings.API_V1_STR}/categories")
def list_categories(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    cats = db.query(Category).filter(Category.user_id == user_id, Category.is_archived == False).all()
    res = []
    for c in cats:
        doc_count = db.query(Document).filter(Document.category_id == c.id).count()
        res.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "color": c.color,
            "document_count": doc_count,
            "created_at": c.created_at
        })
    return res

@app.post(f"{settings.API_V1_STR}/categories")
def create_category(payload: CategoryCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    cat = Category(
        user_id=user_id,
        name=payload.name,
        description=payload.description or "",
        color=payload.color or "#4f46e5"
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@app.get(f"{settings.API_V1_STR}/documents")
def list_documents(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).all()
    res = []
    for d in docs:
        topic_count = db.query(DocumentTopic).filter(DocumentTopic.document_id == d.id).count()
        res.append({
            "id": d.id,
            "title": d.title,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size_bytes": d.file_size_bytes,
            "category_id": d.category_id,
            "category_name": d.category.name if d.category else "Unassigned",
            "processing_status": d.processing_status,
            "resource_prep_status": getattr(d, "resource_prep_status", "completed") or "completed",
            "coverage_summary": getattr(d, "coverage_summary", "{}") or "{}",
            "extracted_topics_count": topic_count,
            "created_at": d.created_at,
            "is_demo": d.is_demo
        })
    return res


@app.post(f"{settings.API_V1_STR}/documents/{{document_id}}/prepare-resources")
def trigger_document_resource_preparation(
    document_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    On-demand or retry trigger for learning suite preparation
    (quizzes, flashcard decks, mind maps, study guides).
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.resource_prep_status = "processing"
    db.commit()
    background_tasks.add_task(run_background_resource_prep, user_id, doc.id)

    return {
        "status": "processing",
        "message": f"Resource preparation initiated for '{doc.title}'.",
        "document_id": doc.id
    }

def execute_document_ingestion_pipeline(
    db: Session,
    user_id: str,
    file_path: str,
    safe_filename: str,
    assigned_category_id: Optional[str],
    custom_title: Optional[str] = None,
    timings_accumulator: Optional[Dict[str, float]] = None
) -> Tuple[Document, int, Dict[str, float], Dict[str, Any]]:
    """
    Unified, reusable document processing pipeline with granular instrumentation.
    Reused by direct file upload and confirmed captures.
    """
    timings = timings_accumulator if timings_accumulator is not None else {}
    ext = os.path.splitext(safe_filename)[1].lower()
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    doc_title = custom_title or os.path.splitext(safe_filename)[0].replace("_", " ").title()

    t_db_init_start = time.perf_counter()
    doc = Document(
        user_id=user_id,
        category_id=assigned_category_id,
        title=doc_title,
        filename=safe_filename,
        file_type=ext.replace(".", "") or "txt",
        file_path=file_path,
        file_size_bytes=file_size,
        processing_status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    timings["db_init_ms"] = round((time.perf_counter() - t_db_init_start) * 1000, 2)

    try:
        # 1. Text extraction & page audit
        t_extract_start = time.perf_counter()
        raw_text, pages_data = extract_raw_pages_and_text(file_path, safe_filename)
        doc.raw_text = raw_text
        coverage_metrics = compute_page_coverage(pages_data)
        doc.coverage_summary = json.dumps(coverage_metrics)
        doc.resource_prep_status = "pending"
        timings["text_extraction_ms"] = round((time.perf_counter() - t_extract_start) * 1000, 2)

        # 2. Chunking
        t_chunk_start = time.perf_counter()
        chunks_data = chunk_pages_and_text(pages_data, raw_text)
        timings["chunking_ms"] = round((time.perf_counter() - t_chunk_start) * 1000, 2)

        # 3. Store chunks
        t_db_chunks_start = time.perf_counter()
        retrieval_svc = RetrievalService(db)
        chunk_records = []
        for idx, ch in enumerate(chunks_data):
            chunk_rec = SourceChunk(
                document_id=doc.id,
                chunk_index=idx,
                page_number=ch.get("page_number", 1),
                section_heading=ch.get("section_heading"),
                content=ch["content"],
                char_count=len(ch["content"])
            )
            db.add(chunk_rec)
            chunk_records.append(chunk_rec)
        db.commit()
        timings["db_chunks_ms"] = round((time.perf_counter() - t_db_chunks_start) * 1000, 2)

        # 4. Uniform vector embeddings for all chunks across all pages (no arbitrary limits)
        t_emb_start = time.perf_counter()
        try:
            retrieval_svc.index_chunks_batch(
                user_id=user_id,
                document_id=doc.id,
                chunk_records=chunk_records
            )
        except Exception as emb_err:
            logger.warning(f"Batch vector indexing error for doc {doc.id}: {emb_err}")
        timings["vector_embedding_ms"] = round((time.perf_counter() - t_emb_start) * 1000, 2)

        # 5. Extract topics and knowledge graph elements
        t_graph_start = time.perf_counter()
        rag_engine = RAGIntelligenceEngine(db)
        graph_data = rag_engine.extract_graph_elements_from_document(
            user_id=user_id,
            document_id=doc.id,
            filename=safe_filename,
            title=doc.title,
            raw_text=raw_text
        )
        timings["graph_extraction_ms"] = round((time.perf_counter() - t_graph_start) * 1000, 2)

        # 6. Database graph writes
        t_db_graph_start = time.perf_counter()
        new_topic_objects = []
        for item in graph_data.get("nodes", []):
            canonical = item["name"].strip().title()
            existing = db.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.canonical_name == canonical
            ).first()

            if not existing:
                existing = Topic(
                    user_id=user_id,
                    name=item["name"].strip(),
                    canonical_name=canonical,
                    description=item.get("description", f"Concept from {safe_filename}"),
                    topic_type=item.get("topic_type", "concept"),
                    aliases=item.get("aliases", []),
                    is_demo=False
                )
                db.add(existing)
                db.commit()
                db.refresh(existing)
                new_topic_objects.append(existing)

                # Initialize memory state
                mem = TopicMemoryState(
                    user_id=user_id,
                    topic_id=existing.id,
                    status="unlearned",
                    stability=1.0,
                    difficulty=0.3,
                    estimated_retention=1.0
                )
                db.add(mem)

            # Link doc to topic
            doc_topic = DocumentTopic(
                document_id=doc.id,
                topic_id=existing.id,
                relevance_score=1.0,
                evidence_snippet=item.get("description", "")[:200]
            )
            db.add(doc_topic)

        connect_new_topics_heuristic(db, user_id, new_topic_objects)
        for edge in graph_data.get("edges", []):
            s_t = db.query(Topic).filter(Topic.user_id == user_id, Topic.canonical_name == edge["source"].strip().title()).first()
            t_t = db.query(Topic).filter(Topic.user_id == user_id, Topic.canonical_name == edge["target"].strip().title()).first()
            if s_t and t_t and s_t.id != t_t.id:
                existing_rel = db.query(TopicRelationship).filter(
                    TopicRelationship.user_id == user_id,
                    TopicRelationship.source_topic_id == s_t.id,
                    TopicRelationship.target_topic_id == t_t.id
                ).first()
                if not existing_rel:
                    new_rel = TopicRelationship(
                        user_id=user_id,
                        source_topic_id=s_t.id,
                        target_topic_id=t_t.id,
                        relationship_type=edge.get("relationship_type", "relates_to"),
                        confidence=edge.get("confidence", 0.85),
                        evidence_text=edge.get("evidence", f"Direct association from {safe_filename}")
                    )
                    db.add(new_rel)

        doc.processing_status = "completed"
        db.commit()
        timings["db_graph_ms"] = round((time.perf_counter() - t_db_graph_start) * 1000, 2)

        node_count = len(graph_data.get("nodes", []))
        dispatch_notification(
            db=db,
            user_id=user_id,
            notification_type="document_processed",
            title=f"📄 Material Ready: {doc.title}",
            message=f"'{safe_filename}' was analyzed successfully. Extracted {node_count} concept nodes ready for learning & recall.",
            action_url="/uploads",
            entity_type="document",
            entity_id=doc.id,
            priority="normal",
            dedup_key=f"doc_processed_{doc.id}",
            meta={"extracted_topics": node_count, "filename": safe_filename}
        )

        extra_metrics = {
            "page_count": len(pages_data),
            "chunk_count": len(chunk_records),
            "raw_text_len": len(raw_text)
        }
        return doc, node_count, timings, extra_metrics

    except Exception as e:
        logger.error(f"Document pipeline processing failed for {safe_filename}: {e}", exc_info=True)
        doc.processing_status = "failed"
        doc.error_message = str(e)
        db.commit()

        dispatch_notification(
            db=db,
            user_id=user_id,
            notification_type="document_failed",
            title=f"❌ Processing Failed: {safe_filename}",
            message=f"Unable to process '{safe_filename}': {str(e)[:150]}",
            action_url="/uploads",
            entity_type="document",
            entity_id=doc.id,
            priority="high",
            dedup_key=f"doc_failed_{doc.id}",
            meta={"error": str(e)[:200]}
        )
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post(f"{settings.API_V1_STR}/documents/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category_id: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Secure, instrumented file upload pipeline:
    1. Validates format (PDF, DOCX, TXT, MD) & size (max 25MB) using streaming chunks.
    2. Inspects magic byte signatures on the initial chunk to reject executables and malformed files.
    3. Saves locally into user-isolated storage.
    4. Extracts text, chunks, computes embeddings, and builds knowledge graph.
    5. Measures and logs separate timings without private content.
    6. Automatically schedules asynchronous resource preparation (summary note, quiz, flashcards, mind map).
    """
    t_start = time.perf_counter()
    timings: Dict[str, float] = {}

    safe_filename = sanitize_filename(file.filename or "uploaded_document")
    ext = os.path.splitext(safe_filename)[1].lower()

    user_storage = os.path.abspath(os.path.join(settings.STORAGE_DIR, user_id))
    os.makedirs(user_storage, exist_ok=True)
    file_path = os.path.abspath(os.path.join(user_storage, safe_filename))

    if not file_path.startswith(user_storage):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    assigned_category_id = None
    if category_id and category_id.strip():
        valid_cat = db.query(Category).filter(Category.id == category_id.strip(), Category.user_id == user_id).first()
        if valid_cat:
            assigned_category_id = valid_cat.id
        else:
            user_default_cat = db.query(Category).filter(Category.user_id == user_id).first()
            if user_default_cat:
                assigned_category_id = user_default_cat.id

    t_save_start = time.perf_counter()
    file_size, safe_filename, ext = stream_save_and_validate(
        upload_file=file,
        dest_path=file_path,
        allowed_extensions=[".pdf", ".docx", ".txt", ".md"],
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB
    )
    timings["upload_save_ms"] = round((time.perf_counter() - t_save_start) * 1000, 2)

    doc, node_count, pipeline_timings, extra_metrics = execute_document_ingestion_pipeline(
        db=db,
        user_id=user_id,
        file_path=file_path,
        safe_filename=safe_filename,
        assigned_category_id=assigned_category_id,
        timings_accumulator=timings
    )

    # Schedule automated background learning resource preparation
    background_tasks.add_task(run_background_resource_prep, user_id, doc.id)

    timings["total_duration_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

    perf_metrics = {
        "event": "document_ingestion_completed",
        "document_id": doc.id,
        "filename": safe_filename,
        "file_type": ext,
        "file_size_bytes": file_size,
        "page_count": extra_metrics.get("page_count", 1),
        "chunk_count": extra_metrics.get("chunk_count", 0),
        "topics_extracted": node_count,
        "timings_ms": timings
    }
    logger.info("PDF_PERF_METRICS: %s", json.dumps(perf_metrics))

    return {
        "message": f"Successfully processed '{safe_filename}'",
        "document_id": doc.id,
        "extracted_topics": node_count,
        "status": doc.processing_status,
        "performance_metrics": perf_metrics
    }


# --- 4B. SECURE CAPTURE INBOX & SMART SHARE ENDPOINTS ---

@app.post(f"{settings.API_V1_STR}/capture/url", response_model=CaptureResponse)
def capture_url(
    payload: CaptureUrlRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    SSRF-protected endpoint to ingest a web URL into the user's Capture Inbox.
    Extracts sanitized text and runs AI category recommendation.
    """
    clean_url = payload.url.strip()
    fetch_res = fetch_url_content_ssrf_safe(clean_url)

    if not fetch_res.get("success"):
        # If server-side fetch failed (e.g. 403 anti-bot policy), check if client provided page_content
        if payload.page_content and payload.page_content.strip():
            logger.info("Server-side fetch failed (%s); falling back to client-provided tab content for %s", fetch_res.get("error"), clean_url)
            content_text = payload.page_content.strip()[:50000]
            title = (payload.title or "").strip() or clean_url.split("/")[-1] or "Web Resource"
            file_path = None
            file_type = "web_article"
            file_size = len(content_text.encode("utf-8"))
        else:
            raise HTTPException(
                status_code=fetch_res.get("status_code", 400),
                detail=fetch_res.get("error", "Failed to retrieve URL content safely.")
            )
    else:
        title = fetch_res.get("title") or (payload.title.strip() if payload.title else "Web Resource")
        if fetch_res.get("is_pdf"):
            # Save temporary PDF in user storage
            user_storage = os.path.abspath(os.path.join(settings.STORAGE_DIR, user_id, "captures"))
            os.makedirs(user_storage, exist_ok=True)
            pdf_filename = f"capture_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{re.sub(r'[^a-zA-Z0-9]', '_', title)[:30]}.pdf"
            file_path = os.path.join(user_storage, pdf_filename)
            with open(file_path, "wb") as f:
                f.write(fetch_res["content_bytes"])

            raw_text, _ = extract_text_from_file(file_path, pdf_filename)
            content_text = raw_text[:50000] # Cap text size
            file_type = "pdf"
            file_size = os.path.getsize(file_path)
        else:
            content_text = fetch_res.get("content_text", "")
            if len(content_text.strip()) < 100 and payload.page_content and len(payload.page_content.strip()) > len(content_text.strip()):
                content_text = payload.page_content.strip()[:50000]
            file_path = None
            file_type = "web_article"
            file_size = len(content_text.encode("utf-8"))

    # AI Category Recommendation
    rec = recommend_category_for_content(db, user_id, title, content_text)

    capture = CaptureItem(
        user_id=user_id,
        source_type=payload.source_type or "web_url",
        source_url=clean_url,
        title=title[:255],
        content_text=content_text,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size,
        recommended_category_id=rec.get("recommended_category_id"),
        recommended_category_name=rec.get("recommended_category_name"),
        recommendation_confidence=rec.get("confidence", 0.0),
        recommendation_reason=rec.get("explanation"),
        alternative_categories=rec.get("alternative_categories", []),
        status="pending_review",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    return {
        "id": capture.id,
        "user_id": capture.user_id,
        "source_type": capture.source_type,
        "source_url": capture.source_url,
        "title": capture.title,
        "content_preview": capture.content_text[:400] + ("..." if len(capture.content_text) > 400 else ""),
        "file_type": capture.file_type,
        "file_size_bytes": capture.file_size_bytes,
        "recommended_category_id": capture.recommended_category_id,
        "recommended_category_name": capture.recommended_category_name,
        "recommendation_confidence": capture.recommendation_confidence,
        "recommendation_reason": capture.recommendation_reason,
        "alternative_categories": capture.alternative_categories or [],
        "status": capture.status,
        "error_message": capture.error_message,
        "document_id": capture.document_id,
        "created_at": capture.created_at
    }


@app.post(f"{settings.API_V1_STR}/capture/text", response_model=CaptureResponse)
def capture_text(
    payload: CaptureTextRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Ingests text, selection, or clipboard snippet into the user's Capture Inbox.
    Runs AI category recommendation.
    """
    content = payload.content_text.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Captured content cannot be empty.")

    # Determine title
    title = (payload.title or "").strip()
    if not title:
        first_line = content.splitlines()[0].strip()
        title = first_line[:60] if len(first_line) > 5 else "Shared Text Snippet"

    rec = recommend_category_for_content(db, user_id, title, content)

    capture = CaptureItem(
        user_id=user_id,
        source_type=payload.source_type or "selection",
        source_url=payload.source_url,
        title=title[:255],
        content_text=content,
        file_path=None,
        file_type="text",
        file_size_bytes=len(content.encode("utf-8")),
        recommended_category_id=rec.get("recommended_category_id"),
        recommended_category_name=rec.get("recommended_category_name"),
        recommendation_confidence=rec.get("confidence", 0.0),
        recommendation_reason=rec.get("explanation"),
        alternative_categories=rec.get("alternative_categories", []),
        status="pending_review",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    return {
        "id": capture.id,
        "user_id": capture.user_id,
        "source_type": capture.source_type,
        "source_url": capture.source_url,
        "title": capture.title,
        "content_preview": capture.content_text[:400] + ("..." if len(capture.content_text) > 400 else ""),
        "file_type": capture.file_type,
        "file_size_bytes": capture.file_size_bytes,
        "recommended_category_id": capture.recommended_category_id,
        "recommended_category_name": capture.recommended_category_name,
        "recommendation_confidence": capture.recommendation_confidence,
        "recommendation_reason": capture.recommendation_reason,
        "alternative_categories": capture.alternative_categories or [],
        "status": capture.status,
        "error_message": capture.error_message,
        "document_id": capture.document_id,
        "created_at": capture.created_at
    }


@app.post(f"{settings.API_V1_STR}/capture/file", response_model=CaptureResponse)
def capture_file_upload(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_type: str = Form("file"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Accepts a shared file (PDF, DOCX, TXT, MD, image) into the user's Capture Inbox.
    """
    supported_exts = [".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"]
    safe_filename = sanitize_filename(file.filename or "shared_file")
    user_storage = os.path.abspath(os.path.join(settings.STORAGE_DIR, user_id, "captures"))
    os.makedirs(user_storage, exist_ok=True)
    file_path = os.path.abspath(os.path.join(user_storage, f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_filename}"))

    file_size, safe_filename, ext = stream_save_and_validate(
        upload_file=file,
        dest_path=file_path,
        allowed_extensions=supported_exts,
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB
    )
    is_image = ext in [".png", ".jpg", ".jpeg", ".webp"]

    if is_image:
        content_text = f"[Image capture: {safe_filename}] Screenshot or image captured for visual review."
        file_type = "image"
    else:
        raw_text, _ = extract_text_from_file(file_path, safe_filename)
        content_text = raw_text[:50000]
        file_type = ext.replace(".", "")

    doc_title = title.strip() if title and title.strip() else os.path.splitext(safe_filename)[0].replace("_", " ").title()
    rec = recommend_category_for_content(db, user_id, doc_title, content_text)

    capture = CaptureItem(
        user_id=user_id,
        source_type=source_type,
        source_url=None,
        title=doc_title[:255],
        content_text=content_text,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size,
        recommended_category_id=rec.get("recommended_category_id"),
        recommended_category_name=rec.get("recommended_category_name"),
        recommendation_confidence=rec.get("confidence", 0.0),
        recommendation_reason=rec.get("explanation"),
        alternative_categories=rec.get("alternative_categories", []),
        status="pending_review",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    return {
        "id": capture.id,
        "user_id": capture.user_id,
        "source_type": capture.source_type,
        "source_url": capture.source_url,
        "title": capture.title,
        "content_preview": capture.content_text[:400] + ("..." if len(capture.content_text) > 400 else ""),
        "file_type": capture.file_type,
        "file_size_bytes": capture.file_size_bytes,
        "recommended_category_id": capture.recommended_category_id,
        "recommended_category_name": capture.recommended_category_name,
        "recommendation_confidence": capture.recommendation_confidence,
        "recommendation_reason": capture.recommendation_reason,
        "alternative_categories": capture.alternative_categories or [],
        "status": capture.status,
        "error_message": capture.error_message,
        "document_id": capture.document_id,
        "created_at": capture.created_at
    }


@app.get(f"{settings.API_V1_STR}/capture/inbox", response_model=List[CaptureResponse])
def get_capture_inbox(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns pending captures for the authenticated user.
    """
    captures = db.query(CaptureItem).filter(
        CaptureItem.user_id == user_id,
        CaptureItem.status == "pending_review"
    ).order_by(CaptureItem.created_at.desc()).all()

    res = []
    for c in captures:
        res.append({
            "id": c.id,
            "user_id": c.user_id,
            "source_type": c.source_type,
            "source_url": c.source_url,
            "title": c.title,
            "content_preview": c.content_text[:400] + ("..." if len(c.content_text) > 400 else ""),
            "file_type": c.file_type,
            "file_size_bytes": c.file_size_bytes,
            "recommended_category_id": c.recommended_category_id,
            "recommended_category_name": c.recommended_category_name,
            "recommendation_confidence": c.recommendation_confidence,
            "recommendation_reason": c.recommendation_reason,
            "alternative_categories": c.alternative_categories or [],
            "status": c.status,
            "error_message": c.error_message,
            "document_id": c.document_id,
            "created_at": c.created_at
        })
    return res


@app.post(f"{settings.API_V1_STR}/capture/{{capture_id}}/confirm")
def confirm_capture(
    capture_id: str,
    payload: CaptureConfirmRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Explicit user confirmation to save captured content into the persistent knowledge vault.
    Idempotent: if already confirmed, returns the existing document.
    """
    capture = db.query(CaptureItem).filter(
        CaptureItem.id == capture_id,
        CaptureItem.user_id == user_id
    ).first()

    if not capture:
        raise HTTPException(status_code=404, detail="Capture item not found or does not belong to user.")

    # Idempotent retry check
    if capture.status == "confirmed" and capture.document_id:
        existing_doc = db.query(Document).filter(Document.id == capture.document_id, Document.user_id == user_id).first()
        if existing_doc:
            return {
                "message": "Capture was already confirmed.",
                "document_id": existing_doc.id,
                "document_title": existing_doc.title,
                "status": "completed"
            }

    # Resolve or create target category
    target_category_id = None
    if payload.new_category_name and payload.new_category_name.strip():
        new_name = payload.new_category_name.strip()
        # Check if already exists for this user
        existing_cat = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name.ilike(new_name)
        ).first()
        if existing_cat:
            target_category_id = existing_cat.id
        else:
            new_cat = Category(
                user_id=user_id,
                name=new_name,
                description=f"Category created for '{payload.custom_title or capture.title}'",
                color="#6366f1"
            )
            db.add(new_cat)
            db.commit()
            db.refresh(new_cat)
            target_category_id = new_cat.id
    elif payload.category_id and payload.category_id.strip():
        # Validate ownership of specified category
        valid_cat = db.query(Category).filter(
            Category.id == payload.category_id.strip(),
            Category.user_id == user_id
        ).first()
        if not valid_cat:
            raise HTTPException(status_code=400, detail="Invalid category ID. Category does not belong to user.")
        target_category_id = valid_cat.id
    elif capture.recommended_category_id:
        # User accepted the recommended existing category
        valid_cat = db.query(Category).filter(
            Category.id == capture.recommended_category_id,
            Category.user_id == user_id
        ).first()
        if valid_cat:
            target_category_id = valid_cat.id

    # If still unassigned, assign user's first category if one exists
    if not target_category_id:
        default_cat = db.query(Category).filter(Category.user_id == user_id).first()
        if default_cat:
            target_category_id = default_cat.id

    # Title resolution
    final_title = payload.custom_title.strip() if payload.custom_title and payload.custom_title.strip() else capture.title

    # File path resolution
    user_storage = os.path.abspath(os.path.join(settings.STORAGE_DIR, user_id))
    os.makedirs(user_storage, exist_ok=True)

    if capture.file_path and os.path.exists(capture.file_path):
        # Move temporary file to persistent user storage
        dest_filename = os.path.basename(capture.file_path)
        dest_file_path = os.path.join(user_storage, dest_filename)
        shutil.copy2(capture.file_path, dest_file_path)
        final_file_path = dest_file_path
    else:
        # Create text file from captured content
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', final_title)[:40]
        dest_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_name}.txt"
        dest_file_path = os.path.join(user_storage, dest_filename)
        with open(dest_file_path, "w", encoding="utf-8") as f:
            f.write(capture.content_text)
        final_file_path = dest_file_path

    # Run the unified document ingestion pipeline
    try:
        doc, node_count, *_ = execute_document_ingestion_pipeline(
            db=db,
            user_id=user_id,
            file_path=final_file_path,
            safe_filename=os.path.basename(final_file_path),
            assigned_category_id=target_category_id,
            custom_title=final_title
        )

        capture.status = "confirmed"
        capture.document_id = doc.id
        db.commit()

        # Schedule automated background learning resource preparation
        background_tasks.add_task(run_background_resource_prep, user_id, doc.id)

        return {
            "message": f"Successfully confirmed and ingested '{doc.title}'.",
            "document_id": doc.id,
            "document_title": doc.title,
            "category_id": target_category_id,
            "extracted_topics": node_count,
            "status": doc.processing_status
        }
    except Exception as e:
        capture.status = "failed"
        capture.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to ingest capture: {str(e)}")


@app.delete(f"{settings.API_V1_STR}/capture/{{capture_id}}")
def discard_capture(
    capture_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Discards a pending capture without saving it to the permanent knowledge library.
    Removes temporary file if one was generated.
    """
    capture = db.query(CaptureItem).filter(
        CaptureItem.id == capture_id,
        CaptureItem.user_id == user_id
    ).first()

    if not capture:
        raise HTTPException(status_code=404, detail="Capture item not found or does not belong to user.")

    # Remove temporary capture file if present
    if capture.file_path and os.path.exists(capture.file_path):
        try:
            # Make sure we only delete inside user's captures directory
            if "captures" in capture.file_path:
                os.remove(capture.file_path)
        except Exception as e:
            logger.warning(f"Error removing temporary capture file: {e}")

    db.delete(capture)
    db.commit()
    return {"message": "Capture discarded successfully."}


# --- 5. TOPICS & KNOWLEDGE GRAPH ---
@app.get(f"{settings.API_V1_STR}/topics")
def list_topics(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    refresh_user_memory_states(db, user_id)
    topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    mem_states = {
        m.topic_id: m 
        for m in db.query(TopicMemoryState).filter(TopicMemoryState.user_id == user_id).all()
    }

    res = []
    for t in topics:
        m = mem_states.get(t.id)
        res.append({
            "id": t.id,
            "name": t.name,
            "canonical_name": t.canonical_name,
            "description": t.description,
            "topic_type": t.topic_type,
            "status": m.status if m else "unlearned",
            "estimated_retention": round((m.estimated_retention if m else 1.0) * 100, 1),
            "stability_days": m.stability if m else 1.0,
            "next_review_at": m.next_review_at if m else None,
            "is_muted": m.is_muted if m else False,
            "is_demo": t.is_demo
        })
    return res

@app.get(f"{settings.API_V1_STR}/knowledge-graph")
def get_knowledge_graph(
    detail_level: str = "simple",
    focus_topic_id: Optional[str] = None,
    category_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    refresh_user_memory_states(db, user_id)
    return build_user_knowledge_graph(
        db,
        user_id,
        detail_level=detail_level,
        focus_topic_id=focus_topic_id,
        category_id=category_id
    )

@app.get(f"{settings.API_V1_STR}/knowledge-graph/concepts/{{topic_id}}/details")
def get_concept_details(
    topic_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    details = get_concept_details_payload(db, user_id, topic_id)
    if not details:
        raise HTTPException(status_code=404, detail="Concept not found or access denied.")
    return details

@app.post(f"{settings.API_V1_STR}/topics/{{topic_id}}/mute")
def toggle_mute_topic(topic_id: str, mute: bool = True, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    handle_mute_topic(db, user_id, topic_id, mute=mute)
    return {"message": f"Topic {'muted' if mute else 'unmuted'} successfully."}

# --- 6. LEARN & AI TUTOR ---
@app.post(f"{settings.API_V1_STR}/learn/explain")
def learn_topic(payload: LearnRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Generates grounded academic explanation using source chunks from linked documents.
    Updates memory state upon completion.
    """
    topic_name = "Core Concept"
    resolved_doc_ids = list(payload.document_ids or [])

    if payload.topic_ids:
        target_id = payload.topic_ids[0]
        t = db.query(Topic).filter(Topic.id == target_id, Topic.user_id == user_id).first()
        if t:
            topic_name = t.canonical_name
            # Retrieve source chunks linked to this topic
            doc_assocs = db.query(DocumentTopic).filter(DocumentTopic.topic_id == t.id).all()
            for da in doc_assocs:
                if da.document_id not in resolved_doc_ids:
                    resolved_doc_ids.append(da.document_id)

            # Mark topic as learned / baseline established
            update_memory_on_learning(db, user_id, t.id)
    elif payload.query:
        topic_name = payload.query

    # Fetch user personalization context
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    p_ctx = {
        "user_roles": prefs.user_roles if prefs else [],
        "learning_goals_list": prefs.learning_goals_list if prefs else [],
        "target_exam": prefs.target_exam if prefs else "",
        "curriculum": prefs.curriculum if prefs else "",
        "learning_context": prefs.learning_context if prefs else {},
        "custom_other_responses": prefs.custom_other_responses if prefs else {},
        "teaching_styles": prefs.teaching_styles if prefs else [],
    }

    rag_engine = RAGIntelligenceEngine(db)
    res = rag_engine.explain_topic(
        user_id=user_id,
        topic_name=topic_name,
        depth=payload.depth or (prefs.explanation_depth if prefs else "semi-detailed"),
        user_query=payload.query,
        personalization_context=p_ctx,
        document_ids=resolved_doc_ids or None
    )
    return res

@app.post(f"{settings.API_V1_STR}/learn/save-note")
def save_learn_note(payload: SaveLearnAsNoteRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    note = Note(
        user_id=user_id,
        category_id=payload.category_id,
        topic_id=payload.topic_id,
        document_id=payload.document_id,
        title=payload.title,
        content=payload.content,
        source_type="ai_tutor",
        tags=["ai-tutor", "synthesis"]
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"message": "Note saved successfully.", "note_id": note.id}

@app.post(f"{settings.API_V1_STR}/tutor/chat", response_model=TutorChatResponse)
def tutor_chat_endpoint(
    payload: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dedicated AI Tutor Chat Endpoint with full RAG grounding across user uploads.
    """
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    p_ctx = {
        "user_roles": prefs.user_roles if prefs else [],
        "learning_goals_list": prefs.learning_goals_list if prefs else [],
        "learning_context": prefs.learning_context if prefs else {},
        "target_exam": prefs.target_exam if prefs else "",
    }

    rag_engine = RAGIntelligenceEngine(db)
    result = rag_engine.chat_with_tutor(
        user_id=current_user.id,
        user_name=current_user.name or "Learner",
        user_message=payload.message,
        conversation_history=payload.conversation_history,
        personalization_context=p_ctx
    )
    return result


# --- 6B. AGENTIC AI LEARNING AGENT & CONVERSATIONS ---

@app.post(f"{settings.API_V1_STR}/agent/conversations", response_model=AgentConversationResponse)
def create_agent_conversation(
    payload: Optional[AgentConversationCreate] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = AgentConversationService(db)
    conv = service.create_conversation(
        user_id=user_id,
        title=payload.title if payload else None,
        topic_id=payload.topic_id if payload else None
    )
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "topic_id": conv.topic_id,
        "is_archived": conv.is_archived,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": 0,
        "messages": []
    }


@app.get(f"{settings.API_V1_STR}/agent/conversations", response_model=List[AgentConversationResponse])
def list_agent_conversations(
    skip: int = 0,
    limit: int = 20,
    include_archived: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = AgentConversationService(db)
    convs = service.list_conversations(user_id=user_id, skip=skip, limit=limit, include_archived=include_archived)
    results = []
    for c in convs:
        results.append({
            "id": c.id,
            "user_id": c.user_id,
            "title": c.title,
            "topic_id": c.topic_id,
            "is_archived": c.is_archived,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": len(c.messages) if c.messages else 0
        })
    return results


@app.get(f"{settings.API_V1_STR}/agent/conversations/{{conversation_id}}", response_model=AgentConversationResponse)
def get_agent_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = AgentConversationService(db)
    conv = service.get_conversation(user_id=user_id, conversation_id=conversation_id)
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "topic_id": conv.topic_id,
        "is_archived": conv.is_archived,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": len(conv.messages) if conv.messages else 0,
        "messages": conv.messages or []
    }


@app.patch(f"{settings.API_V1_STR}/agent/conversations/{{conversation_id}}", response_model=AgentConversationResponse)
def update_agent_conversation(
    conversation_id: str,
    payload: AgentConversationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = AgentConversationService(db)
    conv = service.update_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
        title=payload.title,
        is_archived=payload.is_archived
    )
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "topic_id": conv.topic_id,
        "is_archived": conv.is_archived,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": len(conv.messages) if conv.messages else 0,
        "messages": conv.messages or []
    }


@app.delete(f"{settings.API_V1_STR}/agent/conversations/{{conversation_id}}")
def delete_agent_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = AgentConversationService(db)
    service.delete_conversation(user_id=user_id, conversation_id=conversation_id)
    return {"message": "Conversation deleted successfully.", "conversation_id": conversation_id}


@app.post(f"{settings.API_V1_STR}/agent/conversations/{{conversation_id}}/messages", response_model=AgentMessageResponse)
def post_agent_message(
    conversation_id: str,
    payload: AgentMessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = AgentConversationService(db)
    assistant_msg = service.post_user_message_and_respond(
        user_id=user_id,
        conversation_id=conversation_id,
        content=payload.content,
        language=payload.language,
        document_ids=payload.document_ids
    )
    return assistant_msg


@app.get(f"{settings.API_V1_STR}/agent/tools", response_model=List[AgentToolInfo])
def list_registered_agent_tools(
    user_id: str = Depends(get_current_user_id)
):
    """Returns registry of typed, permission-aware tools available to the Agent."""
    return tool_registry.list_tools()


@app.post(f"{settings.API_V1_STR}/agent/tools/{{tool_name}}/execute", response_model=AgentToolExecuteResponse)
def execute_agent_tool(
    tool_name: str,
    payload: AgentToolExecuteRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Executes a registered agent tool with user scoping, input schema validation,
    and consequential-action protection.
    """
    result = tool_registry.execute(
        tool_name=tool_name,
        user_id=user_id,
        db=db,
        arguments=payload.arguments,
        confirmed=payload.confirmed
    )
    return result

# --- 7. RECALL & QUIZZES ---
@app.post(f"{settings.API_V1_STR}/recall/generate")
def generate_quiz(payload: QuizGenerateRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    topic_name = "Core Academic Topics"
    target_topic_id = None
    resolved_doc_ids = []

    if payload.topic_ids:
        target_topic_id = payload.topic_ids[0]
        t = db.query(Topic).filter(Topic.id == target_topic_id, Topic.user_id == user_id).first()
        if t:
            topic_name = t.canonical_name
            doc_assocs = db.query(DocumentTopic).filter(DocumentTopic.topic_id == t.id).all()
            for da in doc_assocs:
                resolved_doc_ids.append(da.document_id)

    rag_engine = RAGIntelligenceEngine(db)
    quiz_data = rag_engine.generate_quiz(
        user_id=user_id,
        topic_name=topic_name,
        question_count=payload.question_count,
        difficulty=payload.difficulty,
        document_ids=resolved_doc_ids or None
    )

    quiz = Quiz(
        user_id=user_id,
        title=quiz_data.get("title", f"Active Recall: {topic_name}"),
        description=f"Automated grounded quiz on {topic_name}.",
        topic_id=target_topic_id,
        difficulty=payload.difficulty,
        questions=quiz_data.get("questions", [])
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return {
        "id": quiz.id,
        "title": quiz.title,
        "topic_id": quiz.topic_id,
        "questions": quiz.questions,
        "created_at": quiz.created_at
    }

@app.post(f"{settings.API_V1_STR}/recall/submit")
def submit_quiz(payload: QuizSubmitRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == payload.quiz_id, Quiz.user_id == user_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    correct_count = 0
    total = len(quiz.questions)
    results = {}
    weak_topics = []

    for q in quiz.questions:
        qid = q["id"]
        user_ans = str(payload.user_answers.get(qid, "")).strip().lower()
        corr_ans = str(q.get("correct_answer", "")).strip().lower()

        # Grade
        is_corr = (user_ans == corr_ans) or (q["type"] == "short" and len(user_ans) > 5)
        if is_corr:
            correct_count += 1
        else:
            if quiz.topic_id:
                weak_topics.append(quiz.topic_id)

        results[qid] = {
            "user_answer": payload.user_answers.get(qid, ""),
            "correct_answer": q.get("correct_answer"),
            "is_correct": is_corr,
            "explanation": q.get("explanation", "")
        }

    score_pct = round(correct_count / max(1, total), 2)

    # Persist attempt
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user_id,
        score_percentage=score_pct,
        total_questions=total,
        correct_count=correct_count,
        user_answers=results,
        weak_topics_identified=weak_topics
    )
    db.add(attempt)

    # Update Spaced Repetition Memory State!
    if quiz.topic_id:
        update_memory_on_recall(db, user_id, quiz.topic_id, score_pct)

    db.commit()
    db.refresh(attempt)

    suggestion = "Retention reinforced! Interval extended." if score_pct >= 0.8 else "Needs quick refresh; re-scheduled in 12 hours."

    # Event Notification: Quiz Result Available
    pct_int = int(round(score_pct * 100))
    dispatch_notification(
        db=db,
        user_id=user_id,
        notification_type="quiz_completed",
        title=f"🎯 Quiz Completed: {quiz.title} ({pct_int}%)",
        message=f"You answered {correct_count}/{total} questions correctly. {suggestion}",
        action_url="/recall",
        entity_type="quiz",
        entity_id=quiz.id,
        topic_id=quiz.topic_id,
        priority="normal",
        dedup_key=f"quiz_result_{attempt.id}",
        meta={"score_pct": pct_int, "attempt_id": attempt.id}
    )

    # Event Notification: Weak areas alert if score was below 75% and weak topics identified
    if score_pct < 0.75 and weak_topics:
        t_obj = db.query(Topic).filter(Topic.id == weak_topics[0]).first()
        t_name = t_obj.canonical_name if t_obj else "Identified Concept"
        dispatch_notification(
            db=db,
            user_id=user_id,
            notification_type="weak_topics_identified",
            title=f"⚠️ Focus Area: {t_name}",
            message=f"Missed questions in {quiz.title} indicate retention decay for {t_name}. Review this concept before your next drill.",
            action_url="/recall",
            entity_type="topic",
            entity_id=t_obj.id if t_obj else None,
            topic_id=t_obj.id if t_obj else None,
            priority="high",
            dedup_key=f"weak_topic_{attempt.id}",
            meta={"quiz_id": quiz.id, "weak_topics": weak_topics}
        )

    return {
        "attempt_id": attempt.id,
        "quiz_id": quiz.id,
        "score_percentage": score_pct * 100,
        "total_questions": total,
        "correct_count": correct_count,
        "results": results,
        "weak_topics": weak_topics,
        "next_review_suggestion": suggestion
    }

# --- 8. FLASHCARDS & MIND MAPS ---
@app.get(f"{settings.API_V1_STR}/flashcards/decks")
def list_flashcard_decks(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    decks = db.query(FlashcardDeck).filter(FlashcardDeck.user_id == user_id).all()
    res = []
    for d in decks:
        card_count = db.query(Flashcard).filter(Flashcard.deck_id == d.id).count()
        res.append({
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "detail_level": getattr(d, "detail_level", "semi-detailed") or "semi-detailed",
            "card_count": card_count,
            "created_at": d.created_at
        })
    return res

@app.get(f"{settings.API_V1_STR}/flashcards/decks/{{deck_id}}/cards")
def get_deck_cards(deck_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    cards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()
    return cards

@app.post(f"{settings.API_V1_STR}/flashcards/generate")
def generate_flashcard_deck(
    topic_id: str,
    detail_level: str = "semi-detailed",
    card_count: Optional[int] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    doc_assocs = db.query(DocumentTopic).filter(DocumentTopic.topic_id == topic.id).all()
    resolved_doc_ids = [da.document_id for da in doc_assocs]

    rag_engine = RAGIntelligenceEngine(db)
    deck_data = rag_engine.generate_flashcards(
        user_id=user_id,
        topic_name=topic.canonical_name,
        card_count=card_count,
        detail_level=detail_level,
        document_ids=resolved_doc_ids or None
    )

    cards_data = deck_data.get("cards", [])

    deck = FlashcardDeck(
        user_id=user_id,
        title=f"Deck: {topic.canonical_name} ({detail_level.title()})",
        description=f"Adaptive {detail_level} retrieval cards for {topic.canonical_name}",
        topic_id=topic.id,
        detail_level=detail_level,
        version=1
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)

    for c in cards_data:
        fc = Flashcard(
            deck_id=deck.id,
            front=c["front"],
            back=c["back"],
            hint=c.get("hint") or "",
            topic_id=topic.id,
            detail_level=c.get("detail_level", detail_level),
            concept_id=c.get("concept_id"),
            section_name=c.get("section_name"),
            source_citation=c.get("source_citation")
        )
        db.add(fc)
    db.commit()
    return {
        "message": "Deck generated successfully",
        "deck_id": deck.id,
        "detail_level": detail_level,
        "cards_count": len(cards_data),
        "coverage_status": deck_data.get("coverage_status", "verified")
    }

@app.get(f"{settings.API_V1_STR}/mind-maps")
def list_mind_maps(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    maps = db.query(MindMap).filter(MindMap.user_id == user_id).order_by(MindMap.created_at.desc()).all()
    res = []
    for m in maps:
        struct = m.structure_json or {}
        res.append({
            "id": m.id,
            "title": m.title,
            "central_topic": m.central_topic,
            "topic_id": m.topic_id,
            "document_id": m.document_id,
            "structure_json": struct,
            "detail_level": struct.get("detail_level", "semi-detailed"),
            "is_grounded": struct.get("is_grounded", False),
            "created_at": m.created_at
        })
    return res

@app.post(f"{settings.API_V1_STR}/mind-maps/generate")
def generate_mind_map(payload: MindMapGenerateRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    detail = payload.detail_level or "semi-detailed"
    central_topic = payload.central_topic.strip()
    if not central_topic:
        raise HTTPException(status_code=400, detail="Central topic is required.")

    # 1. Validate ownership of topic_id or document_id if provided
    matched_topic = None
    matched_doc = None
    source_text_parts = []
    subtopics = []
    relationships = []

    if payload.topic_id:
        matched_topic = db.query(Topic).filter(Topic.id == payload.topic_id, Topic.user_id == user_id).first()
        if not matched_topic:
            raise HTTPException(status_code=404, detail="Selected topic not found or does not belong to your account.")

    if payload.document_id:
        matched_doc = db.query(Document).filter(Document.id == payload.document_id, Document.user_id == user_id).first()
        if not matched_doc:
            raise HTTPException(status_code=404, detail="Selected document not found or does not belong to your account.")

    # 2. If topic_id not explicitly given, try resolving topic by central_topic name for this user
    if not matched_topic:
        matched_topic = db.query(Topic).filter(
            Topic.user_id == user_id,
            Topic.canonical_name.ilike(central_topic)
        ).first()

    # 3. If document_id not explicitly given, try resolving via document title or topic associations
    if matched_topic and not matched_doc:
        doc_assoc = db.query(DocumentTopic).filter(DocumentTopic.topic_id == matched_topic.id).first()
        if doc_assoc:
            matched_doc = db.query(Document).filter(Document.id == doc_assoc.document_id, Document.user_id == user_id).first()

    if not matched_doc and not matched_topic:
        # Search if any user document title contains or matches the central topic
        matched_doc = db.query(Document).filter(
            Document.user_id == user_id,
            (Document.title.ilike(f"%{central_topic}%") | Document.filename.ilike(f"%{central_topic}%"))
        ).first()

    # If still not matched, use Semantic Retrieval to find the most relevant document
    if not matched_doc:
        retrieval_svc = RetrievalService(db)
        top_chunks = retrieval_svc.retrieve(user_id=user_id, query=central_topic, top_k=1)
        if top_chunks:
            matched_doc = db.query(Document).filter(Document.id == top_chunks[0]["document_id"], Document.user_id == user_id).first()


    # 4. Gather real source text and structured subtopics
    if matched_doc:
        # Fetch actual source chunks
        chunks = db.query(SourceChunk).filter(SourceChunk.document_id == matched_doc.id).limit(6).all()
        for c in chunks:
            if c.content:
                source_text_parts.append(c.content)
        if not source_text_parts and matched_doc.raw_text:
            source_text_parts.append(matched_doc.raw_text[:4000])

        # Get topics associated with this document
        doc_topics = db.query(Topic).join(DocumentTopic, DocumentTopic.topic_id == Topic.id).filter(
            DocumentTopic.document_id == matched_doc.id,
            Topic.user_id == user_id
        ).all()
        for dt in doc_topics:
            subtopics.append({
                "name": dt.name,
                "canonical_name": dt.canonical_name,
                "description": dt.description or ""
            })

    if matched_topic:
        if matched_topic.description:
            source_text_parts.append(matched_topic.description)

        # Retrieve topic relationships
        rels = db.query(TopicRelationship).filter(
            TopicRelationship.user_id == user_id,
            (TopicRelationship.source_topic_id == matched_topic.id) | (TopicRelationship.target_topic_id == matched_topic.id)
        ).all()
        all_topic_ids = set()
        for r in rels:
            all_topic_ids.add(r.source_topic_id)
            all_topic_ids.add(r.target_topic_id)
        all_topics_map = {t.id: t for t in db.query(Topic).filter(Topic.id.in_(all_topic_ids)).all()} if all_topic_ids else {}

        for r in rels:
            s_t = all_topics_map.get(r.source_topic_id)
            t_t = all_topics_map.get(r.target_topic_id)
            if s_t and t_t:
                relationships.append({
                    "source_name": s_t.canonical_name,
                    "target_name": t_t.canonical_name,
                    "relationship_type": r.relationship_type
                })
                # If target or source is not current topic, treat as subtopic
                other = t_t if s_t.id == matched_topic.id else s_t
                if other.canonical_name.lower() != central_topic.lower():
                    subtopics.append({
                        "name": other.name,
                        "canonical_name": other.canonical_name,
                        "description": other.description or ""
                    })

    # 5. Check if user has ANY documents or topics if nothing matched
    user_has_any_materials = (
        db.query(Document).filter(Document.user_id == user_id).count() > 0 or
        db.query(Topic).filter(Topic.user_id == user_id).count() > 0
    )

    combined_source = "\n\n".join(source_text_parts)

    # If the user has NO materials at all, or the query has no relation to user's materials,
    # reject with clear 400 error rather than fabricating fake mind maps.
    if not source_text_parts and not subtopics:
        if not user_has_any_materials:
            raise HTTPException(
                status_code=400,
                detail="Insufficient structured content: You haven't uploaded any documents or saved study topics yet. Upload study materials first to generate a grounded concept mind map."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient structured content: No relevant source notes, documents, or topics found for '{central_topic}'. Please select an existing topic or upload material covering this concept."
            )

    # 6. Generate grounded mind map via RAG
    rag_engine = RAGIntelligenceEngine(db)
    structure = rag_engine.generate_mind_map(
        user_id=user_id,
        central_topic=central_topic,
        detail_level=detail,
        document_ids=[matched_doc.id] if matched_doc else None,
        source_text=combined_source if combined_source else None,
        subtopics=subtopics if subtopics else None,
        relationships=relationships if relationships else None
    )

    mm = MindMap(
        user_id=user_id,
        title=f"Mind Map: {central_topic} ({detail.title()})",
        central_topic=central_topic,
        topic_id=matched_topic.id if matched_topic else payload.topic_id,
        document_id=matched_doc.id if matched_doc else payload.document_id,
        structure_json=structure
    )
    db.add(mm)
    db.commit()
    db.refresh(mm)

    # Dispatch mind map notification
    dispatch_notification(
        db=db,
        user_id=user_id,
        notification_type="mindmap_ready",
        title=f"🧠 Mind Map Created: {central_topic}",
        message=f"Interactive hierarchical schema ready for '{central_topic}'. Explore concept connections on canvas.",
        action_url="/mindmaps",
        entity_type="mind_map",
        entity_id=mm.id,
        priority="low",
        dedup_key=f"{user_id}_mindmap_{mm.id}"
    )

    return {
        "id": mm.id,
        "title": mm.title,
        "central_topic": mm.central_topic,
        "structure_json": mm.structure_json,
        "created_at": mm.created_at
    }

# --- 9. EXAM TOMORROW & DATE-SHEET PARSER ---
@app.post(f"{settings.API_V1_STR}/exams/date-sheet/extract")
def extract_date_sheet(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    Parses date sheet PDF or text, extracts subject, dates, and times,
    and returns them for user confirmation before saving.
    """
    text_to_parse = raw_text or ""
    if file:
        safe_filename = sanitize_filename(file.filename or "datesheet.pdf")
        temp_path = os.path.abspath(os.path.join(settings.STORAGE_DIR, f"temp_{safe_filename}"))
        try:
            stream_save_and_validate(
                upload_file=file,
                dest_path=temp_path,
                allowed_extensions=[".pdf", ".docx", ".txt", ".md"],
                max_size_mb=settings.MAX_UPLOAD_SIZE_MB
            )
            text_to_parse, _ = extract_text_from_file(temp_path, safe_filename)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    extracted = parse_date_sheet_text(text_to_parse)
    return {
        "extracted_exams": extracted,
        "confidence": "high" if len(extracted) > 1 else "medium",
        "raw_snippet": text_to_parse[:300]
    }

@app.get(f"{settings.API_V1_STR}/exams")
def list_exams(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    exams = db.query(Exam).filter(Exam.user_id == user_id).order_by(Exam.exam_date.asc()).all()
    res = []
    for e in exams:
        tasks = db.query(StudyTask).filter(StudyTask.exam_id == e.id).all()
        res.append({
            "id": e.id,
            "subject": e.subject,
            "exam_date": e.exam_date,
            "exam_time_str": e.exam_time_str,
            "location": e.location,
            "syllabus_summary": e.syllabus_summary,
            "days_left": max(0, (e.exam_date - datetime.utcnow()).days),
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.is_completed)
        })
    return res

@app.post(f"{settings.API_V1_STR}/exams")
def create_exam(payload: ExamCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    exam = Exam(
        user_id=user_id,
        subject=payload.subject,
        exam_date=payload.exam_date,
        exam_time_str=payload.exam_time_str or "09:00 AM",
        location=payload.location or "Main Campus",
        syllabus_summary=payload.syllabus_summary or "",
        total_preparation_days=payload.total_preparation_days or 7
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # Automatically generate revision study plan
    generate_exam_revision_plan(db, user_id, exam.id)

    # Dispatch exam creation alert
    days_left = max(0, (exam.exam_date.date() - datetime.utcnow().date()).days)
    dispatch_notification(
        db=db,
        user_id=user_id,
        notification_type="exam_alert",
        title=f"📅 Exam Added: {exam.subject}",
        message=f"Exam scheduled for {exam.exam_date.strftime('%b %d, %Y')} ({days_left} days away). Study plan tasks have been generated.",
        action_url="/exam",
        entity_type="exam",
        entity_id=exam.id,
        priority="high",
        dedup_key=f"{user_id}_exam_created_{exam.id}"
    )

    return {
        "id": exam.id,
        "subject": exam.subject,
        "exam_date": exam.exam_date,
        "exam_time_str": exam.exam_time_str,
        "location": exam.location,
        "syllabus_summary": exam.syllabus_summary,
        "total_preparation_days": exam.total_preparation_days
    }

@app.post(f"{settings.API_V1_STR}/exams/{{exam_id}}/generate-plan")
def generate_study_plan(exam_id: str, payload: GenerateStudyPlanRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    tasks = generate_exam_revision_plan(db, user_id, exam_id, payload.daily_available_minutes or 60)
    return {"message": "Plan generated successfully", "tasks_count": len(tasks)}

@app.get(f"{settings.API_V1_STR}/exams/{{exam_id}}/tasks")
def get_exam_tasks(exam_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return db.query(StudyTask).filter(StudyTask.exam_id == exam_id, StudyTask.user_id == user_id).order_by(StudyTask.scheduled_for.asc()).all()

@app.post(f"{settings.API_V1_STR}/tasks/{{task_id}}/toggle")
def toggle_task_completion(task_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    task = db.query(StudyTask).filter(StudyTask.id == task_id, StudyTask.user_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = not task.is_completed
    task.completed_at = datetime.utcnow() if task.is_completed else None
    db.commit()
    db.refresh(task)
    return task

# --- 10. NOTES ---
@app.get(f"{settings.API_V1_STR}/notes")
def list_notes(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return db.query(Note).filter(Note.user_id == user_id).order_by(Note.updated_at.desc()).all()

@app.post(f"{settings.API_V1_STR}/notes")
def create_note(payload: NoteCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    note = Note(
        user_id=user_id,
        title=payload.title,
        content=payload.content,
        category_id=payload.category_id,
        topic_id=payload.topic_id,
        document_id=payload.document_id,
        tags=payload.tags or []
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

@app.delete(f"{settings.API_V1_STR}/notes/{{note_id}}")
def delete_note(note_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if note:
        db.delete(note)
        db.commit()
    return {"message": "Note deleted"}

# --- 11. NOTIFICATIONS ENGINE & PROACTIVE MEMORY COACH ---
@app.get(f"{settings.API_V1_STR}/notifications")
def list_notifications(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    run_proactive_notification_cycle(db, user_id)
    now = datetime.utcnow()
    # Filter out dismissed and currently snoozed
    notifs = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_dismissed == False
    ).order_by(Notification.created_at.desc()).all()

    active_notifs = []
    for n in notifs:
        if n.is_snoozed and n.snooze_until and n.snooze_until > now:
            continue
        active_notifs.append(n)
    return active_notifs

@app.post(f"{settings.API_V1_STR}/notifications/{{notif_id}}/start")
def start_notification(notif_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    res = handle_start_notification(db, notif_id, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Notification not found")
    return res

@app.post(f"{settings.API_V1_STR}/notifications/{{notif_id}}/dismiss")
def dismiss_notification(notif_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    notif = handle_dismiss_notification(db, notif_id, user_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification dismissed.", "id": notif.id, "action_state": "dismissed"}

@app.post(f"{settings.API_V1_STR}/notifications/{{notif_id}}/snooze")
def snooze_notification(notif_id: str, payload: Optional[SnoozeNotificationRequest] = None, minutes: Optional[int] = None, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    snooze_min = 60
    if payload and payload.snooze_minutes:
        snooze_min = payload.snooze_minutes
    elif minutes is not None:
        snooze_min = minutes
    res = handle_snooze_notification(db, notif_id, user_id, snooze_min)
    if not res:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": f"Notification snoozed for {snooze_min} minutes.", "id": res.id, "action_state": "snoozed", "is_snoozed": res.is_snoozed, "snooze_until": res.snooze_until}

@app.post(f"{settings.API_V1_STR}/notifications/{{notif_id}}/no-need")
def no_need_notification(notif_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    res = handle_no_need_notification(db, notif_id, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Notification not found")
    return res

@app.get(f"{settings.API_V1_STR}/topics/suppressed")
def list_suppressed_topics(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    suppressed_states = db.query(TopicMemoryState).filter(
        TopicMemoryState.user_id == user_id,
        TopicMemoryState.no_need_suppressed == True
    ).all()
    results = []
    for s in suppressed_states:
        top = db.query(Topic).filter(Topic.id == s.topic_id, Topic.user_id == user_id).first()
        if top:
            cat_name = "General"
            doc_assoc = db.query(DocumentTopic).filter(DocumentTopic.topic_id == top.id).first()
            if doc_assoc:
                doc = db.query(Document).filter(Document.id == doc_assoc.document_id).first()
                if doc and doc.category_id:
                    cat = db.query(Category).filter(Category.id == doc.category_id).first()
                    if cat:
                        cat_name = cat.name
            results.append({
                "topic_id": top.id,
                "canonical_name": top.canonical_name,
                "suppressed_at": s.suppressed_at,
                "category_name": cat_name,
                "stability_days": s.stability or 1.0
            })
    return results

@app.post(f"{settings.API_V1_STR}/topics/{{topic_id}}/unsuppress")
def unsuppress_topic(topic_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    success = handle_unmute_concept(db, user_id, topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Suppressed topic not found")
    return {"message": "Concept reminders re-enabled successfully.", "topic_id": topic_id}

@app.post(f"{settings.API_V1_STR}/notifications/push/subscribe")
def subscribe_web_push(payload: WebPushSubscriptionCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # Check if subscription already exists for this endpoint
    existing = db.query(WebPushSubscription).filter(
        WebPushSubscription.user_id == user_id,
        WebPushSubscription.endpoint == payload.endpoint
    ).first()
    if existing:
        existing.p256dh = payload.p256dh
        existing.auth = payload.auth
        existing.user_agent = payload.user_agent or ""
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id}

    sub = WebPushSubscription(
        user_id=user_id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
        user_agent=payload.user_agent or ""
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"status": "subscribed", "id": sub.id}

@app.post(f"{settings.API_V1_STR}/notifications/push/unsubscribe")
def unsubscribe_web_push(payload: dict, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    endpoint = payload.get("endpoint")
    if endpoint:
        db.query(WebPushSubscription).filter(
            WebPushSubscription.user_id == user_id,
            WebPushSubscription.endpoint == endpoint
        ).delete()
        db.commit()
    return {"status": "unsubscribed"}

@app.post(f"{settings.API_V1_STR}/notifications/{{notif_id}}/read")
def mark_notification_read(notif_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    notif = handle_mark_read_notification(db, notif_id, user_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read", "id": notif.id, "is_read": True}

@app.post(f"{settings.API_V1_STR}/notifications/read-all")
def mark_all_notifications_read(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    count = handle_mark_all_read(db, user_id)
    return {"message": f"Marked {count} notifications as read", "count": count}

@app.delete(f"{settings.API_V1_STR}/exams/{{exam_id}}")
def delete_exam(exam_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    # Clean up associated study tasks and notifications
    db.query(StudyTask).filter(StudyTask.exam_id == exam_id, StudyTask.user_id == user_id).delete()
    db.query(Notification).filter(Notification.entity_id == exam_id, Notification.entity_type == "exam", Notification.user_id == user_id).delete()
    db.delete(exam)
    db.commit()
    return {"message": "Exam deleted successfully"}

# --- 12. CROSS-DOCUMENT CONNECTIVITY ---
@app.get(f"{settings.API_V1_STR}/connectivity")
def get_connectivity_insights(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Discovers cross-resource conceptual connections, prerequisites, and contrasts.
    Identifies source and target documents to distinguish same-document vs cross-document bridges.
    """
    relationships = db.query(TopicRelationship).filter(TopicRelationship.user_id == user_id).all()
    res = []
    
    # Pre-fetch document associations
    doc_assocs = db.query(DocumentTopic).all()
    topic_docs_map: Dict[str, Set[str]] = {}
    for da in doc_assocs:
        topic_docs_map.setdefault(da.topic_id, set()).add(da.document_id)
        
    user_docs = {d.id: d for d in db.query(Document).filter(Document.user_id == user_id).all()}

    def generate_simple_reason(s_name: str, t_name: str, rel_type: str, is_cross: bool) -> str:
        clean = rel_type.lower()
        if "prerequisite" in clean:
            return f"Mastering {s_name} provides the necessary foundation before studying {t_name}."
        elif "builds on" in clean or "extends" in clean:
            return f"{t_name} deepens and builds upon core mechanisms in {s_name}."
        elif "contrast" in clean:
            return f"{s_name} and {t_name} offer contrasting approaches to solving similar problems."
        elif is_cross:
            return f"Bridges knowledge across documents: principles from {s_name} directly apply to {t_name}."
        else:
            return f"Reinforces conceptual understanding: {s_name} connects directly with {t_name}."

    for r in relationships:
        source_t = db.query(Topic).filter(Topic.id == r.source_topic_id).first()
        target_t = db.query(Topic).filter(Topic.id == r.target_topic_id).first()
        if source_t and target_t:
            s_doc_ids = topic_docs_map.get(source_t.id, set())
            t_doc_ids = topic_docs_map.get(target_t.id, set())
            is_cross = bool(s_doc_ids and t_doc_ids and s_doc_ids.isdisjoint(t_doc_ids))
            
            s_doc_title = user_docs[next(iter(s_doc_ids))].title if s_doc_ids and next(iter(s_doc_ids)) in user_docs else "Vault Notes"
            t_doc_title = user_docs[next(iter(t_doc_ids))].title if t_doc_ids and next(iter(t_doc_ids)) in user_docs else "Vault Notes"

            simple_reason = generate_simple_reason(source_t.canonical_name, target_t.canonical_name, r.relationship_type, is_cross)

            res.append({
                "id": r.id,
                "source_topic": source_t.canonical_name,
                "source_topic_id": source_t.id,
                "source_document_title": s_doc_title,
                "target_topic": target_t.canonical_name,
                "target_topic_id": target_t.id,
                "target_document_title": t_doc_title,
                "relationship_type": r.relationship_type.replace("_", " ").title(),
                "confidence": r.confidence or 0.8,
                "is_cross_document": is_cross,
                "simple_reason": simple_reason,
                "evidence_text": r.evidence_text or simple_reason
            })
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
