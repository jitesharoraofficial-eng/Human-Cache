import math
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from backend.models import TopicMemoryState, LearningEvent, Topic

# Spaced Repetition configuration constants
RETENTION_TARGET = 0.90 # Target 90% recall retention

def calculate_current_retention(memory_state: TopicMemoryState, now: Optional[datetime] = None) -> float:
    """
    Computes current retention estimate using Ebbinghaus exponential forgetting curve:
    R = exp(-t / S) where t is elapsed days since last recall/learning, and S is stability in days.
    """
    if not memory_state.last_learned_at:
        return 1.0

    if not now:
        now = datetime.utcnow()

    reference_time = memory_state.last_recalled_at or memory_state.last_learned_at
    elapsed_days = max(0.0, (now - reference_time).total_seconds() / 86400.0)
    stability = max(0.1, memory_state.stability)

    # R = exp(-elapsed_days / stability)
    retention = math.exp(-elapsed_days / stability)
    return round(min(1.0, max(0.05, retention)), 3)

def update_memory_on_learning(db: Session, user_id: str, topic_id: str) -> TopicMemoryState:
    """
    Called when a user learns a concept in AI Tutor or reads study notes.
    Initializes or resets learning baseline.
    """
    now = datetime.utcnow()
    mem = db.query(TopicMemoryState).filter(
        TopicMemoryState.user_id == user_id,
        TopicMemoryState.topic_id == topic_id
    ).first()

    if not mem:
        mem = TopicMemoryState(
            user_id=user_id,
            topic_id=topic_id,
            status="learned",
            stability=1.5, # 1.5 days initial stability
            difficulty=0.3,
            recall_accuracy=0.0,
            total_reviews=0,
            successful_reviews=0,
            last_learned_at=now,
            next_review_at=now + timedelta(days=1, hours=12),
            estimated_retention=1.0
        )
        db.add(mem)
    else:
        mem.status = "learned"
        mem.last_learned_at = now
        # Schedule review in 1-2 days
        mem.next_review_at = now + timedelta(days=max(1, int(mem.stability)))
        mem.estimated_retention = 1.0

    # Record learning event
    event = LearningEvent(
        user_id=user_id,
        topic_id=topic_id,
        event_type="study_session",
        duration_seconds=180,
        details={"action": "completed_learning_unit"}
    )
    db.add(event)
    db.commit()
    db.refresh(mem)
    return mem

def update_memory_on_recall(db: Session, user_id: str, topic_id: str, score_percentage: float) -> TopicMemoryState:
    """
    Updates stability, difficulty, review status, and next review interval
    based on recall accuracy (score 0.0 to 1.0).
    Algorithm:
    - If score >= 0.8: Successful recall -> Stability multiplied by (1 + difficulty_factor * 1.5).
    - If 0.5 <= score < 0.8: Partial recall -> Modest bump.
    - If score < 0.5: Lapsed / weak -> Stability cut, marked for quick relearning.
    """
    now = datetime.utcnow()
    mem = db.query(TopicMemoryState).filter(
        TopicMemoryState.user_id == user_id,
        TopicMemoryState.topic_id == topic_id
    ).first()

    if not mem:
        mem = TopicMemoryState(
            user_id=user_id,
            topic_id=topic_id,
            status="learned",
            stability=1.0,
            difficulty=0.3,
            last_learned_at=now
        )
        db.add(mem)

    mem.last_recalled_at = now
    mem.total_reviews += 1

    # Update running average recall accuracy
    mem.recall_accuracy = round((mem.recall_accuracy * (mem.total_reviews - 1) + score_percentage) / mem.total_reviews, 2)

    if score_percentage >= 0.8: # Strong recall
        mem.successful_reviews += 1
        # Extend stability
        factor = 2.2 - (mem.difficulty * 0.5)
        mem.stability = round(max(2.0, mem.stability * factor), 1)
        mem.difficulty = max(0.1, round(mem.difficulty - 0.05, 2))
        mem.status = "learned"
        interval_days = max(2, int(mem.stability))
        mem.next_review_at = now + timedelta(days=interval_days)
    elif score_percentage >= 0.5: # Partial recall
        mem.successful_reviews += 1
        mem.stability = round(max(1.0, mem.stability * 1.2), 1)
        mem.status = "learned"
        interval_days = max(1, int(mem.stability))
        mem.next_review_at = now + timedelta(days=interval_days)
    else: # Weak / Failed recall
        mem.stability = 0.5 # 12 hours
        mem.difficulty = min(0.9, round(mem.difficulty + 0.15, 2))
        mem.status = "relearning"
        mem.next_review_at = now + timedelta(hours=12)

    mem.estimated_retention = 1.0

    # Record event
    event = LearningEvent(
        user_id=user_id,
        topic_id=topic_id,
        event_type="quiz_attempt",
        score=score_percentage,
        details={"score": score_percentage, "new_stability": mem.stability}
    )
    db.add(event)
    db.commit()
    db.refresh(mem)
    return mem

def refresh_user_memory_states(db: Session, user_id: str):
    """
    Scans all topic memory states for the user, re-calculates retention percentage,
    and updates status to 'review_due' or 'overdue'.
    """
    now = datetime.utcnow()
    states = db.query(TopicMemoryState).filter(TopicMemoryState.user_id == user_id).all()
    for s in states:
        if getattr(s, "no_need_suppressed", False):
            s.status = "suppressed"
            continue
        if s.is_muted:
            s.status = "muted"
            continue
        s.estimated_retention = calculate_current_retention(s, now)
        if s.next_review_at:
            if now > s.next_review_at + timedelta(days=2):
                s.status = "overdue"
            elif now >= s.next_review_at or s.estimated_retention < 0.75:
                s.status = "review_due"
            elif s.status in ["review_due", "overdue"]:
                s.status = "learned"
    db.commit()

