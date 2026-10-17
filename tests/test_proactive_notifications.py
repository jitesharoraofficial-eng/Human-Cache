import os
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.database import get_db
from backend.models import (
    User, Category, Document, Topic, DocumentTopic,
    Quiz, FlashcardDeck, Flashcard, TopicMemoryState, Notification
)
from backend.scheduler import memory_coach_scheduler
from tests.test_auth_and_isolation import client, TestingSessionLocal

@pytest.fixture(autouse=True)
def reset_rate_limit():
    AUTH_RATE_LIMIT_STORE.clear()

def register_and_login(client: TestClient, email: str, name: str = "Test Learner"):
    res = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!"}
    )
    assert res.status_code == 200, res.text
    return res.json()["user"]


def test_autonomous_scheduler_cycle_without_manual_visit():
    """Verify that memory_coach_scheduler runs autonomously across users and triggers notifications."""
    user = register_and_login(client, "sched_user@example.com", "Scheduler User")

    # Upload document to create real topic and memory state
    cat = client.post("/api/v1/categories", json={"name": "Thermodynamics", "color": "#F59E0B"}).json()
    content = b"The second law of thermodynamics asserts that the total entropy of an isolated system always increases over time."
    doc = client.post(
        "/api/v1/documents/upload",
        files={"file": ("thermo.txt", content, "text/plain")},
        data={"category_id": cat["id"]}
    ).json()

    topic_id = None
    db = TestingSessionLocal()
    try:
        topic = db.query(Topic).filter(Topic.user_id == user["id"]).first()
        assert topic is not None
        topic_id = topic.id
        mem = db.query(TopicMemoryState).filter(TopicMemoryState.topic_id == topic.id).first()
        assert mem is not None

        # Simulate that review is overdue (next_review_at in the past, retention decayed)
        mem.next_review_at = datetime.utcnow() - timedelta(days=2)
        mem.status = "overdue"
        mem.estimated_retention = 0.45
        db.commit()
    finally:
        db.close()

    # Execute scheduler cycle directly
    stats = memory_coach_scheduler.run_cycle_for_all_users(db_session=TestingSessionLocal())
    assert stats["users_scanned"] >= 1

    # Check that proactive review notification was created with prepared resources
    notifs = client.get("/api/v1/notifications").json()
    review_notifs = [n for n in notifs if n.get("topic_id") == topic_id]
    assert len(review_notifs) >= 1
    assert "review" in review_notifs[0]["notification_type"] or "risk" in review_notifs[0]["notification_type"]
    assert review_notifs[0]["action_state"] in ["active", "pending"]
    # Grounded resources pre-prepared
    assert review_notifs[0]["meta"] is not None
    assert "quiz_id" in review_notifs[0]["meta"] or "deck_id" in review_notifs[0]["meta"]


def test_action_start_notification():
    """Verify ACTION A (START) updates action_state, marks read, and returns target drill metadata."""
    user = register_and_login(client, "start_action_user@example.com", "Start Action User")

    # Create exam to get notification
    client.post("/api/v1/exams", json={"subject": "Electromagnetism Exam", "exam_date": (datetime.utcnow() + timedelta(days=2)).isoformat()})
    notifs = client.get("/api/v1/notifications").json()
    assert len(notifs) >= 1
    notif_id = notifs[0]["id"]

    start_res = client.post(f"/api/v1/notifications/{notif_id}/start")
    assert start_res.status_code == 200
    data = start_res.json()
    assert data["action"] == "start"
    assert data["notification_id"] == notif_id
    assert "action_url" in data

    # Verify notification in DB has action_state = "started" and is_read = True
    db = TestingSessionLocal()
    try:
        n = db.query(Notification).filter(Notification.id == notif_id).first()
        assert n.action_state == "started"
        assert n.is_read is True
    finally:
        db.close()


def test_action_dismiss_notification():
    """Verify ACTION B (DISMISS) persists dismissed state, removes from active list without muting topic."""
    user = register_and_login(client, "dismiss_user@example.com", "Dismiss User")

    client.post("/api/v1/exams", json={"subject": "Fluid Mechanics", "exam_date": (datetime.utcnow() + timedelta(days=3)).isoformat()})
    notifs = client.get("/api/v1/notifications").json()
    notif_id = notifs[0]["id"]

    dismiss_res = client.post(f"/api/v1/notifications/{notif_id}/dismiss")
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["action_state"] == "dismissed"

    # Not visible in active list
    refreshed = client.get("/api/v1/notifications").json()
    assert all(n["id"] != notif_id for n in refreshed)


def test_action_snooze_custom_intervals():
    """Verify ACTION C (REMIND ME LATER) accepts custom intervals and hides until expiration."""
    user = register_and_login(client, "snooze_user@example.com", "Snooze User")

    client.post("/api/v1/exams", json={"subject": "Optics Exam", "exam_date": (datetime.utcnow() + timedelta(days=2)).isoformat()})
    notifs = client.get("/api/v1/notifications").json()
    notif_id = notifs[0]["id"]

    # Snooze for tomorrow (1440 minutes)
    snooze_res = client.post(f"/api/v1/notifications/{notif_id}/snooze", json={"snooze_minutes": 1440})
    assert snooze_res.status_code == 200
    assert snooze_res.json()["action_state"] == "snoozed"

    # Notification must not appear in active list while snoozed
    refreshed = client.get("/api/v1/notifications").json()
    assert all(n["id"] != notif_id for n in refreshed)


def test_action_no_need_permanent_suppression_and_unsuppress():
    """Verify ACTION D (NO NEED) permanently mutes topic memory state, survives cycles, and allows re-enabling from Settings."""
    user = register_and_login(client, "noneed_user@example.com", "No Need User")

    cat = client.post("/api/v1/categories", json={"name": "Genetics", "color": "#3B82F6"}).json()
    content = b"Mendelian inheritance refers to biological traits that follow Gregor Mendel's laws of segregation and independent assortment."
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("genetics.txt", content, "text/plain")},
        data={"category_id": cat["id"]}
    )

    topic_id = None
    db = TestingSessionLocal()
    try:
        topic = db.query(Topic).filter(Topic.user_id == user["id"]).first()
        assert topic is not None
        topic_id = topic.id
        mem = db.query(TopicMemoryState).filter(TopicMemoryState.topic_id == topic_id).first()
        mem.next_review_at = datetime.utcnow() - timedelta(days=1)
        mem.status = "overdue"
        mem.estimated_retention = 0.50
        db.commit()
    finally:
        db.close()

    # Trigger proactive cycle to produce review notification
    memory_coach_scheduler.run_cycle_for_all_users(db_session=TestingSessionLocal())
    notifs = client.get("/api/v1/notifications").json()
    target_notif = next(n for n in notifs if n.get("topic_id") == topic_id)

    # Click NO NEED
    no_need_res = client.post(f"/api/v1/notifications/{target_notif['id']}/no-need")
    assert no_need_res.status_code == 200
    res_data = no_need_res.json()
    assert res_data["action"] == "no_need"

    # Verify TopicMemoryState is marked no_need_suppressed in DB
    db = TestingSessionLocal()
    try:
        refreshed_mem = db.query(TopicMemoryState).filter(TopicMemoryState.topic_id == topic_id).first()
        assert refreshed_mem.no_need_suppressed is True
        assert refreshed_mem.status == "suppressed"
    finally:
        db.close()

    # Run scheduler cycle again: must NOT produce any new notifications for this concept
    memory_coach_scheduler.run_cycle_for_all_users(db_session=TestingSessionLocal())
    active_notifs = client.get("/api/v1/notifications").json()
    assert all(n.get("topic_id") != topic_id for n in active_notifs)

    # Verify concept appears in GET /topics/suppressed
    suppressed_list = client.get("/api/v1/topics/suppressed").json()
    assert any(s["topic_id"] == topic_id for s in suppressed_list)

    # Re-enable in settings (unsuppress)
    unmute_res = client.post(f"/api/v1/topics/{topic_id}/unsuppress")
    assert unmute_res.status_code == 200

    # Verify no longer in suppressed list
    after_unsuppress = client.get("/api/v1/topics/suppressed").json()
    assert all(s["topic_id"] != topic_id for s in after_unsuppress)


def test_web_push_subscription_persistence_and_isolation():
    """Verify Web Push subscribe and unsubscribe endpoints persist correctly and respect user isolation."""
    user_a = register_and_login(client, "push_a@example.com", "Push User A")

    sub_data = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/fake-endpoint-user-a-12345",
        "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9h0Re9",
        "auth": "tBHItJI5svbpez7KI4CCXg",
        "user_agent": "Mozilla/5.0 TestBrowser"
    }

    # Subscribe User A
    sub_res = client.post("/api/v1/notifications/push/subscribe", json=sub_data)
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] in ["subscribed", "updated"]

    # Verify in DB
    db = TestingSessionLocal()
    try:
        from backend.models import WebPushSubscription
        sub_record = db.query(WebPushSubscription).filter(WebPushSubscription.user_id == user_a["id"]).first()
        assert sub_record is not None
        assert sub_record.endpoint == sub_data["endpoint"]
    finally:
        db.close()

    # User B cannot see or manipulate User A's subscription
    user_b = register_and_login(client, "push_b@example.com", "Push User B")
    unsub_res = client.post("/api/v1/notifications/push/unsubscribe", json={"endpoint": sub_data["endpoint"]})
    assert unsub_res.status_code == 200

    # User A's subscription must still exist because User B was requesting
    db = TestingSessionLocal()
    try:
        sub_record_a = db.query(WebPushSubscription).filter(WebPushSubscription.user_id == user_a["id"]).first()
        assert sub_record_a is not None
    finally:
        db.close()
