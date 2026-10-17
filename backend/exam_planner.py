import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models import Exam, StudyTask, Topic, TopicMemoryState

def parse_date_sheet_text(text: str) -> List[Dict[str, Any]]:
    """
    Parses date sheet / timetable text or PDF extraction to detect:
    Subject, Date, Time, Room.
    Supports formats like:
    '15/10/2026 - Data Structures - 10:00 AM'
    'Oct 18, 2026: Operating Systems'
    '2026-10-22 | Machine Learning | 02:00 PM'
    'Chemistry - 25th October 2026'
    """
    extracted = []
    lines = text.split("\n")

    # Patterns for date detection
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})'
    ]

    time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)'

    for line in lines:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 6:
            continue

        matched_date_str = None
        for dp in date_patterns:
            m = re.search(dp, line_clean, re.IGNORECASE)
            if m:
                matched_date_str = m.group(1)
                break

        if matched_date_str:
            time_m = re.search(time_pattern, line_clean)
            time_str = time_m.group(1) if time_m else "09:00 AM"

            # Remove date and time from line to extract subject name
            subject_candidate = line_clean.replace(matched_date_str, "").replace(time_str, "")
            subject_candidate = re.sub(r'[-–—|:,]', ' ', subject_candidate).strip()
            subject_candidate = re.sub(r'\s+', ' ', subject_candidate)

            if len(subject_candidate) < 3:
                subject_candidate = "Academic Examination"

            # Parse date into datetime object with fallback to upcoming date
            parsed_dt = None
            for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
                try:
                    clean_dt_str = re.sub(r'(st|nd|rd|th)', '', matched_date_str)
                    parsed_dt = datetime.strptime(clean_dt_str, fmt)
                    break
                except Exception:
                    continue

            if not parsed_dt:
                parsed_dt = datetime.utcnow() + timedelta(days=7)

            extracted.append({
                "subject": subject_candidate.title(),
                "exam_date": parsed_dt,
                "exam_time_str": time_str,
                "confidence": "high" if parsed_dt else "medium",
                "raw_line": line_clean
            })

    # If nothing detected with strict patterns, return empty list rather than fabricating mock exams
    return extracted

def generate_exam_revision_plan(
    db: Session,
    user_id: str,
    exam_id: str,
    daily_available_minutes: int = 60
) -> List[StudyTask]:
    """
    Builds a realistic spaced revision study plan leading up to the examination date.
    Prioritizes:
    1. Unlearned topics
    2. Overdue/weak topics
    3. Review sessions
    4. Mock quiz simulation the day before
    """
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user_id).first()
    if not exam:
        return []

    # Clear previous tasks for this exam
    db.query(StudyTask).filter(StudyTask.exam_id == exam_id).delete()

    topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    memory_states = {
        ms.topic_id: ms 
        for ms in db.query(TopicMemoryState).filter(TopicMemoryState.user_id == user_id).all()
    }

    # Sort topics: unlearned or low stability first
    def topic_priority(t: Topic):
        mem = memory_states.get(t.id)
        if not mem or mem.status == "unlearned":
            return 0
        if mem.status in ["overdue", "relearning"]:
            return 1
        return 2

    sorted_topics = sorted(topics, key=topic_priority)

    now = datetime.utcnow()
    days_until_exam = max(1, (exam.exam_date - now).days)
    created_tasks = []

    # Distribute tasks across available days
    current_day = now + timedelta(days=1)
    topic_idx = 0

    for day_offset in range(min(days_until_exam, 14)):
        scheduled_date = now + timedelta(days=day_offset + 1)
        scheduled_date = scheduled_date.replace(hour=18, minute=0, second=0)

        if day_offset == days_until_exam - 1:
            # Day before exam: Full Comprehensive Mock Review
            task = StudyTask(
                user_id=user_id,
                exam_id=exam_id,
                title=f"⚡ Final Comprehensive Simulation: {exam.subject}",
                description="Simulate complete exam conditions with active recall quizzes and high-yield flashcard drills.",
                scheduled_for=scheduled_date,
                allocated_minutes=daily_available_minutes,
                priority="high"
            )
            db.add(task)
            created_tasks.append(task)
            break

        # Assign 1 or 2 targeted topics for this day
        if sorted_topics:
            topic = sorted_topics[topic_idx % len(sorted_topics)]
            topic_idx += 1
            task = StudyTask(
                user_id=user_id,
                exam_id=exam_id,
                topic_id=topic.id,
                title=f"Targeted Focus: {topic.canonical_name}",
                description=f"Deep dive explanation review, concept connectivity, and 5-minute active recall drill for {topic.canonical_name}.",
                scheduled_for=scheduled_date,
                allocated_minutes=min(45, daily_available_minutes),
                priority="high" if day_offset < 3 else "medium"
            )
            db.add(task)
            created_tasks.append(task)

    db.commit()
    for t in created_tasks:
        db.refresh(t)
    return created_tasks
