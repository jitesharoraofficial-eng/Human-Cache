import os
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.database import Base, get_db
from backend.models import (
    User, UserPreference, Category, Document, Topic, 
    Quiz, Note, Exam, StudyTask, Notification, TopicMemoryState
)
from backend.config import settings

# Re-use shared test database and client
from tests.test_auth_and_isolation import client, TestingSessionLocal

@pytest.fixture(autouse=True)
def reset_rate_limit():
    AUTH_RATE_LIMIT_STORE.clear()



def register_and_login(client: TestClient, email: str, name: str = "Test User"):
    res = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!"}
    )
    assert res.status_code == 200, res.text
    return res.json()["user"]

# =====================================================================
# NOTIFICATION SYSTEM TESTS
# =====================================================================

def test_fresh_user_has_zero_notifications():
    """Verify that a brand new user starts with 0 notifications (no fabricated demo data)."""
    fresh_user = register_and_login(client, "fresh_notif_user@example.com", "Fresh User")
    
    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    notifs = res.json()
    assert isinstance(notifs, list)
    assert len(notifs) == 0

def test_document_upload_triggers_notification():
    """Verify that uploading a real document creates a document_processed notification."""
    user = register_and_login(client, "doc_notif_user@example.com", "Doc User")
    
    # Create category
    cat_res = client.post("/api/v1/categories", json={"name": "Organic Chemistry", "color": "#10B981"})
    assert cat_res.status_code == 200
    cat_id = cat_res.json()["id"]

    # Upload document
    doc_content = b"Benzene is an aromatic hydrocarbon with the molecular formula C6H6. Resonance stabilization gives it exceptional stability."
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("benzene_notes.txt", doc_content, "text/plain")},
        data={"category_id": cat_id}
    )
    assert res.status_code == 200

    # Fetch notifications
    notif_res = client.get("/api/v1/notifications")
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) >= 1
    
    doc_notifs = [n for n in notifs if n["notification_type"] == "document_processed"]
    assert len(doc_notifs) == 1
    assert "Benzene" in doc_notifs[0]["title"]
    assert doc_notifs[0]["entity_type"] == "document"
    assert doc_notifs[0]["is_read"] is False

def test_exam_creation_triggers_notification():
    """Verify that creating an exam generates an exam_alert notification with study tasks."""
    user = register_and_login(client, "exam_notif_user@example.com", "Exam User")
    
    exam_date = (datetime.utcnow() + timedelta(days=5)).isoformat()
    res = client.post(
        "/api/v1/exams",
        json={
            "subject": "Organic Chemistry Midterm",
            "exam_date": exam_date,
            "exam_time_str": "10:00 AM",
            "total_preparation_days": 5
        }
    )
    assert res.status_code == 200
    exam_id = res.json()["id"]

    # Fetch notifications
    notif_res = client.get("/api/v1/notifications")
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    
    exam_notifs = [n for n in notifs if n["notification_type"] == "exam_alert"]
    assert len(exam_notifs) >= 1
    assert "Organic Chemistry Midterm" in exam_notifs[0]["title"]
    assert exam_notifs[0]["entity_type"] == "exam"
    assert exam_notifs[0]["entity_id"] == exam_id

def test_mark_notification_as_read():
    """Verify that a notification can be marked as read individually."""
    user = register_and_login(client, "mark_read_user@example.com", "Mark Read User")
    
    # Create an exam to get a notification
    client.post(
        "/api/v1/exams",
        json={
            "subject": "Physics Exam",
            "exam_date": (datetime.utcnow() + timedelta(days=4)).isoformat()
        }
    )
    
    notifs = client.get("/api/v1/notifications").json()
    assert len(notifs) >= 1
    notif_id = notifs[0]["id"]
    assert notifs[0]["is_read"] is False

    # Mark as read
    read_res = client.post(f"/api/v1/notifications/{notif_id}/read")
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Verify updated state in list
    updated_notifs = client.get("/api/v1/notifications").json()
    target = next(n for n in updated_notifs if n["id"] == notif_id)
    assert target["is_read"] is True

def test_mark_all_notifications_as_read():
    """Verify mark all notifications as read bulk endpoint."""
    user = register_and_login(client, "bulk_read_user@example.com", "Bulk User")
    
    # Create multiple exams
    client.post("/api/v1/exams", json={"subject": "Calculus I", "exam_date": (datetime.utcnow() + timedelta(days=3)).isoformat()})
    client.post("/api/v1/exams", json={"subject": "Linear Algebra", "exam_date": (datetime.utcnow() + timedelta(days=6)).isoformat()})

    notifs = client.get("/api/v1/notifications").json()
    assert len(notifs) >= 2
    assert any(not n["is_read"] for n in notifs)

    # Bulk read
    bulk_res = client.post("/api/v1/notifications/read-all")
    assert bulk_res.status_code == 200
    assert bulk_res.json()["count"] >= 2

    # Verify all are read
    refreshed_notifs = client.get("/api/v1/notifications").json()
    for n in refreshed_notifs:
        assert n["is_read"] is True

def test_snooze_and_dismiss_notification():
    """Verify snooze suppresses notification temporarily, and dismiss permanently removes it from active list."""
    user = register_and_login(client, "snooze_dismiss_user@example.com", "Snooze User")
    
    client.post("/api/v1/exams", json={"subject": "History Final", "exam_date": (datetime.utcnow() + timedelta(days=2)).isoformat()})
    notifs = client.get("/api/v1/notifications").json()
    assert len(notifs) >= 1
    target_id = notifs[0]["id"]

    # Snooze for 60 minutes
    snooze_res = client.post(f"/api/v1/notifications/{target_id}/snooze", json={"snooze_minutes": 60})
    assert snooze_res.status_code == 200

    # Notification should now be hidden from active list
    after_snooze = client.get("/api/v1/notifications").json()
    assert all(n["id"] != target_id for n in after_snooze)

    # Dismiss another notification
    client.post("/api/v1/exams", json={"subject": "Art History", "exam_date": (datetime.utcnow() + timedelta(days=4)).isoformat()})
    notifs2 = client.get("/api/v1/notifications").json()
    target_id2 = notifs2[0]["id"]

    dismiss_res = client.post(f"/api/v1/notifications/{target_id2}/dismiss")
    assert dismiss_res.status_code == 200

    after_dismiss = client.get("/api/v1/notifications").json()
    assert all(n["id"] != target_id2 for n in after_dismiss)

def test_user_notification_isolation():
    """Verify User B cannot see, read, or modify User A's notifications."""
    user_a = register_and_login(client, "isolation_a@example.com", "User A")
    client.post("/api/v1/exams", json={"subject": "User A Private Exam", "exam_date": (datetime.utcnow() + timedelta(days=2)).isoformat()})
    notifs_a = client.get("/api/v1/notifications").json()
    assert len(notifs_a) >= 1
    notif_a_id = notifs_a[0]["id"]

    # Switch to User B
    user_b = register_and_login(client, "isolation_b@example.com", "User B")
    notifs_b = client.get("/api/v1/notifications").json()
    # User B should see 0 notifications
    assert len(notifs_b) == 0

    # User B attempts to mark User A's notification as read -> 404
    hack_res = client.post(f"/api/v1/notifications/{notif_a_id}/read")
    assert hack_res.status_code == 404

    # User B attempts to dismiss User A's notification -> 404
    hack_dismiss = client.post(f"/api/v1/notifications/{notif_a_id}/dismiss")
    assert hack_dismiss.status_code == 404


def test_notification_action_state_active_contract():
    """
    Regression Test: Verify consistent action_state='active' contract.
    Ensures newly created notifications arrive with action_state='active'
    and are eligible for in-app toast display under the frontend filter condition.
    """
    user = register_and_login(client, "toast_active_contract@example.com", "Toast User")
    client.post("/api/v1/exams", json={"subject": "Quantum Computing", "exam_date": (datetime.utcnow() + timedelta(days=3)).isoformat()})

    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    notifs = res.json()
    assert len(notifs) >= 1

    target = notifs[0]
    # State contract verification
    assert target["action_state"] == "active"
    assert target["is_read"] is False
    assert target["is_snoozed"] is False

    # Frontend toast eligibility check simulation
    is_eligible = (
        not target["is_read"]
        and not target["is_snoozed"]
        and (not target.get("action_state") or target.get("action_state") in ["active", "pending"])
    )
    assert is_eligible is True, f"Notification failed toast eligibility with action_state='{target.get('action_state')}'"


def test_notification_four_way_actions_lifecycle():
    """
    Verify all four action states: Start, Dismiss, Snooze, No Need.
    Ensures that each action correctly mutates action_state and suppresses subsequent toast pop-ups.
    """
    user = register_and_login(client, "four_actions_user@example.com", "Action User")
    db = TestingSessionLocal()
    try:
        # Create a topic and memory state for testing No Need
        topic = Topic(id=f"top_{uuid.uuid4().hex[:8]}", user_id=user["id"], name="Fluid Mechanics", canonical_name="Fluid Mechanics")
        db.add(topic)
        db.commit()

        mem = TopicMemoryState(user_id=user["id"], topic_id=topic.id, status="learned", stability=1.0)
        db.add(mem)
        db.commit()

        # 1. Action: Start
        client.post("/api/v1/exams", json={"subject": "Test Exam 1", "exam_date": (datetime.utcnow() + timedelta(days=2)).isoformat()})
        notifs = client.get("/api/v1/notifications").json()
        n1 = [n for n in notifs if n["action_state"] == "active"][0]

        start_res = client.post(f"/api/v1/notifications/{n1['id']}/start")
        assert start_res.status_code == 200
        data1 = start_res.json()
        assert data1["action_state"] == "started"

        # 2. Action: Snooze
        client.post("/api/v1/exams", json={"subject": "Test Exam 2", "exam_date": (datetime.utcnow() + timedelta(days=3)).isoformat()})
        notifs2 = client.get("/api/v1/notifications").json()
        n2 = [n for n in notifs2 if n["action_state"] == "active"][0]

        snooze_res = client.post(f"/api/v1/notifications/{n2['id']}/snooze?minutes=120")
        assert snooze_res.status_code == 200
        data2 = snooze_res.json()
        assert data2["is_snoozed"] is True
        assert data2["action_state"] == "snoozed"

        # 3. Action: Dismiss
        client.post("/api/v1/exams", json={"subject": "Test Exam 3", "exam_date": (datetime.utcnow() + timedelta(days=4)).isoformat()})
        notifs3 = client.get("/api/v1/notifications").json()
        n3 = [n for n in notifs3 if n["action_state"] == "active"][0]

        dismiss_res = client.post(f"/api/v1/notifications/{n3['id']}/dismiss")
        assert dismiss_res.status_code == 200

        # Verify n3 is no longer in active list
        active_list = client.get("/api/v1/notifications").json()
        assert all(n["id"] != n3["id"] for n in active_list)

        # 4. Action: No Need (permanently suppresses concept reminders)
        from backend.notification_engine import dispatch_notification
        dispatch_notification(
            db=db,
            user_id=user["id"],
            notification_type="review_due",
            title="Review Due: Fluid Mechanics",
            message="Time to review Fluid Mechanics",
            topic_id=topic.id,
            action_url="/recall"
        )
        notifs4 = client.get("/api/v1/notifications").json()
        n4 = [n for n in notifs4 if n.get("topic_id") == topic.id][0]

        noneed_res = client.post(f"/api/v1/notifications/{n4['id']}/no-need")
        assert noneed_res.status_code == 200

        # Verify topic memory state has no_need_suppressed=True
        db.expire_all()
        mem_updated = db.query(TopicMemoryState).filter(TopicMemoryState.topic_id == topic.id).first()
        assert mem_updated.no_need_suppressed is True
    finally:
        db.close()

