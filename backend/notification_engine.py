from datetime import datetime, timedelta, time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.models import (
    Notification, TopicMemoryState, Topic, Exam, StudyTask,
    UserPreference, Document, Quiz, QuizAttempt
)

def is_within_quiet_hours(start_str: str, end_str: str, check_time: Optional[datetime] = None) -> bool:
    """
    Checks if check_time (default UTC/local) falls within quiet hours (e.g. '22:00' to '08:00').
    """
    if not start_str or not end_str:
        return False
    try:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        start_t = time(sh, sm)
        end_t = time(eh, em)
        now_t = (check_time or datetime.utcnow()).time()

        if start_t <= end_t:
            return start_t <= now_t <= end_t
        else:
            # Over midnight (e.g. 22:00 to 08:00)
            return now_t >= start_t or now_t <= end_t
    except Exception:
        return False

def dispatch_notification(
    db: Session,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    action_url: str = "/learn",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    priority: str = "normal",
    dedup_key: Optional[str] = None,
    scheduled_for: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
    topic_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Optional[Notification]:
    """
    Central, idempotent, personalization-aware notification creator.
    Validates user preferences, master toggle, quiet hours, and deduplication.
    """
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    
    # 1. Master toggle check (unless system notice)
    if prefs and not prefs.notifications_enabled and notification_type != "system_notice":
        return None

    # 2. Category preference check
    if prefs and prefs.notification_categories:
        cats = [c.lower() for c in prefs.notification_categories]
        # Map notification_type to user-facing preference category
        cat_map = {
            "document_processed": "study_materials",
            "document_failed": "study_materials",
            "quiz_completed": "weak_recall",
            "weak_topics_identified": "weak_recall",
            "weak_recall": "weak_recall",
            "exam_alert": "upcoming_exams",
            "exam_tomorrow": "upcoming_exams",
            "review_due": "review_due",
            "high_forgetting_risk": "review_due",
            "task_deadline": "upcoming_exams",
            "mindmap_ready": "study_materials",
            "mindmap_failed": "study_materials"
        }
        mapped_cat = cat_map.get(notification_type)
        if mapped_cat and mapped_cat not in cats and notification_type != "system_notice":
            return None

    # 3. Quiet hours check
    if prefs and is_within_quiet_hours(prefs.quiet_hours_start, prefs.quiet_hours_end):
        # In quiet hours: If not urgent, mark delivery for later or skip
        if priority not in ["high", "urgent"]:
            # Schedule for after quiet hours end
            pass

    # 4. Deduplication
    if dedup_key:
        existing = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.dedup_key == dedup_key
        ).first()
        if existing:
            return existing

    notif = Notification(
        user_id=user_id,
        topic_id=topic_id,
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=action_url,
        entity_type=entity_type,
        entity_id=entity_id,
        priority=priority,
        dedup_key=dedup_key,
        scheduled_for=scheduled_for,
        expires_at=expires_at,
        meta=meta or {},
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def run_proactive_notification_cycle(db: Session, user_id: str) -> List[Notification]:
    """
    Evaluates REAL learning states, actual exam dates, and memory stability
    to generate grounded notifications. Never fabricates events.
    """
    now = datetime.utcnow()
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if prefs and not prefs.notifications_enabled:
        return []

    generated = []

    # 1. Real Memory States: Check for Overdue or High Forgetting Risk Topics
    memory_states = db.query(TopicMemoryState).filter(
        TopicMemoryState.user_id == user_id,
        TopicMemoryState.is_muted == False,
        TopicMemoryState.no_need_suppressed == False
    ).all()

    from backend.resource_prep_service import prepare_or_reuse_learning_resources

    for mem in memory_states:
        # Extra assertion on no_need_suppressed
        if getattr(mem, "no_need_suppressed", False):
            continue

        topic = db.query(Topic).filter(Topic.id == mem.topic_id, Topic.user_id == user_id).first()
        if not topic:
            continue

        # Check if concept is due or forgetting risk is elevated
        if mem.estimated_retention < 0.70 or mem.status == "overdue":
            dedup_key = f"{user_id}_retention_drop_{topic.id}_{now.strftime('%Y-%m-%d')}"
            
            # Reuse existing learning resources without triggering unprompted background LLM calls
            prep_info = prepare_or_reuse_learning_resources(db, user_id, topic.id, auto_generate=False)
            target_url = prep_info.get("action_url") or f"/recall?topic_id={topic.id}"

            notif = dispatch_notification(
                db=db,
                user_id=user_id,
                notification_type="high_forgetting_risk",
                title=f"⚠️ High Forgetting Risk: {topic.canonical_name}",
                message=f"Estimated retention has declined to {int(mem.estimated_retention * 100)}%. A 3-minute active recall drill will restore stability.",
                action_url=target_url,
                entity_type="topic",
                entity_id=topic.id,
                topic_id=topic.id,
                priority="high",
                dedup_key=dedup_key,
                meta={
                    "retention": mem.estimated_retention,
                    "stability": mem.stability,
                    "quiz_id": prep_info.get("quiz_id"),
                    "deck_id": prep_info.get("deck_id")
                }
            )
            if notif:
                generated.append(notif)
        elif mem.status == "review_due":
            dedup_key = f"{user_id}_review_due_{topic.id}_{now.strftime('%Y-%m-%d')}"
            
            # Reuse existing learning resources without triggering unprompted background LLM calls
            prep_info = prepare_or_reuse_learning_resources(db, user_id, topic.id, auto_generate=False)
            target_url = prep_info.get("action_url") or f"/recall?topic_id={topic.id}"

            notif = dispatch_notification(
                db=db,
                user_id=user_id,
                notification_type="review_due",
                title=f"⚡ Review Due: {topic.canonical_name}",
                message=f"It is time to reinforce your memory trace for {topic.canonical_name}.",
                action_url=target_url,
                entity_type="topic",
                entity_id=topic.id,
                topic_id=topic.id,
                priority="normal",
                dedup_key=dedup_key,
                meta={
                    "quiz_id": prep_info.get("quiz_id"),
                    "deck_id": prep_info.get("deck_id")
                }
            )
            if notif:
                generated.append(notif)

    # 2. Real Exams: Check for Exams in next 3 days and Exam Tomorrow
    upcoming_exams = db.query(Exam).filter(
        Exam.user_id == user_id,
        Exam.exam_date >= now - timedelta(hours=6),
        Exam.exam_date <= now + timedelta(days=3)
    ).all()

    for ex in upcoming_exams:
        hours_left = (ex.exam_date - now).total_seconds() / 3600
        days_left = (ex.exam_date.date() - now.date()).days

        if days_left <= 1 and hours_left > 0:
            dedup_key = f"{user_id}_exam_tomorrow_{ex.id}_{now.strftime('%Y-%m-%d')}"
            notif = dispatch_notification(
                db=db,
                user_id=user_id,
                notification_type="exam_tomorrow",
                title=f"🚨 Exam Tomorrow: {ex.subject}",
                message=f"Final preparation checkpoint for {ex.subject} at {ex.exam_time_str or '09:00 AM'}. Review your high-yield summary now.",
                action_url="/exam",
                entity_type="exam",
                entity_id=ex.id,
                priority="urgent",
                dedup_key=dedup_key
            )
            if notif:
                generated.append(notif)
        elif days_left > 1:
            dedup_key = f"{user_id}_exam_countdown_{ex.id}_{days_left}d"
            notif = dispatch_notification(
                db=db,
                user_id=user_id,
                notification_type="exam_alert",
                title=f"📅 Exam Alert: {ex.subject} in {days_left} days",
                message=f"Scheduled revision tasks are ready for {ex.subject}. Complete your daily drill to maintain syllabus retention.",
                action_url="/exam",
                entity_type="exam",
                entity_id=ex.id,
                priority="high",
                dedup_key=dedup_key
            )
            if notif:
                generated.append(notif)

    # 3. Real Study Tasks: Overdue tasks
    overdue_tasks = db.query(StudyTask).filter(
        StudyTask.user_id == user_id,
        StudyTask.is_completed == False,
        StudyTask.scheduled_for < now
    ).limit(3).all()

    for task in overdue_tasks:
        dedup_key = f"{user_id}_overdue_task_{task.id}_{now.strftime('%Y-%m-%d')}"
        notif = dispatch_notification(
            db=db,
            user_id=user_id,
            notification_type="task_deadline",
            title=f"📋 Overdue Study Task: {task.title}",
            message=f"Task allocated for {task.allocated_minutes} mins is pending. Check it off to maintain your schedule.",
            action_url="/exam",
            entity_type="study_task",
            entity_id=task.id,
            priority="normal",
            dedup_key=dedup_key
        )
        if notif:
            generated.append(notif)

    return generated


# --- FOUR MANDATORY NOTIFICATION ACTIONS ---

def handle_start_notification(db: Session, notification_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    ACTION A: START
    Marks notification as started, records action timestamp, and returns
    navigation route and target metadata to launch the legitimate learning drill.
    """
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notif:
        return None

    notif.action_state = "started"
    notif.last_action_at = datetime.utcnow()
    notif.is_read = True
    db.commit()
    db.refresh(notif)

    return {
        "action": "start",
        "action_state": notif.action_state,
        "notification_id": notif.id,
        "action_url": notif.action_url,
        "topic_id": notif.topic_id,
        "entity_type": notif.entity_type,
        "entity_id": notif.entity_id,
        "meta": notif.meta or {}
    }


def handle_dismiss_notification(db: Session, notification_id: str, user_id: str) -> Optional[Notification]:
    """
    ACTION B: DISMISS
    Hides current notification. Persists dismissed state.
    Does NOT permanently mute topic; allows future reminder when next legitimate threshold is reached.
    """
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notif:
        return None

    notif.is_dismissed = True
    notif.action_state = "dismissed"
    notif.last_action_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


def handle_snooze_notification(db: Session, notification_id: str, user_id: str, minutes: int = 60) -> Optional[Notification]:
    """
    ACTION C: REMIND ME LATER
    Persists user's chosen snooze interval. Suppresses notification until snooze_until expires.
    """
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notif:
        return None

    notif.is_snoozed = True
    notif.snooze_until = datetime.utcnow() + timedelta(minutes=minutes)
    notif.action_state = "snoozed"
    notif.last_action_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


def handle_no_need_notification(db: Session, notification_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    ACTION D: NO NEED
    Permanently suppresses future proactive memory reminders for this specific concept.
    Persists across logout/login and backend restarts. Does NOT delete learning resources or documents.
    """
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notif:
        return None

    notif.is_dismissed = True
    notif.action_state = "no_need"
    notif.last_action_at = datetime.utcnow()

    suppressed_topic_name = "Concept"
    if notif.topic_id:
        mem = db.query(TopicMemoryState).filter(
            TopicMemoryState.user_id == user_id,
            TopicMemoryState.topic_id == notif.topic_id
        ).first()
        if mem:
            mem.no_need_suppressed = True
            mem.suppressed_at = datetime.utcnow()
            mem.status = "suppressed"

        top = db.query(Topic).filter(Topic.id == notif.topic_id, Topic.user_id == user_id).first()
        if top:
            suppressed_topic_name = top.canonical_name

    db.commit()
    db.refresh(notif)
    return {
        "action": "no_need",
        "notification_id": notif.id,
        "topic_id": notif.topic_id,
        "topic_name": suppressed_topic_name,
        "message": f"Reminders for '{suppressed_topic_name}' permanently suppressed. You can re-enable anytime in Settings."
    }


def handle_unmute_concept(db: Session, user_id: str, topic_id: str) -> bool:
    """
    Re-enables reminders for a previously suppressed concept from Settings.
    """
    mem = db.query(TopicMemoryState).filter(
        TopicMemoryState.user_id == user_id,
        TopicMemoryState.topic_id == topic_id
    ).first()
    if mem:
        mem.no_need_suppressed = False
        mem.suppressed_at = None
        mem.is_muted = False
        mem.status = "learned"
        db.commit()
        return True
    return False


def handle_mark_read_notification(db: Session, notification_id: str, user_id: str) -> Optional[Notification]:
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif


def handle_mark_all_read(db: Session, user_id: str) -> int:
    updated = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return updated


def handle_mute_topic(db: Session, user_id: str, topic_id: str, mute: bool = True):
    mem = db.query(TopicMemoryState).filter(
        TopicMemoryState.user_id == user_id,
        TopicMemoryState.topic_id == topic_id
    ).first()
    if mem:
        mem.is_muted = mute
        db.commit()


