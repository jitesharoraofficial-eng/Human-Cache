import os
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.database import get_db, Base, engine
from backend.models import User, Category, CaptureItem, Document
from backend.url_capture_service import is_ip_disallowed, validate_target_url, fetch_url_content_ssrf_safe
from backend.category_recommender import recommend_category_for_content

from tests.test_auth_and_isolation import client

@pytest.fixture(autouse=True)
def clear_rate_limits():
    AUTH_RATE_LIMIT_STORE.clear()

def test_ssrf_disallowed_ips():
    """Verify loopback, private RFC 1918, link-local, and cloud metadata IPs are rejected."""
    assert is_ip_disallowed("127.0.0.1") is True
    assert is_ip_disallowed("127.0.0.2") is True
    assert is_ip_disallowed("10.0.0.1") is True
    assert is_ip_disallowed("192.168.1.1") is True
    assert is_ip_disallowed("172.16.0.1") is True
    assert is_ip_disallowed("169.254.169.254") is True # AWS / GCP metadata
    assert is_ip_disallowed("::1") is True
    assert is_ip_disallowed("8.8.8.8") is False # Public IP allowed


def test_ssrf_url_validation_blocks_localhost_and_bad_schemes():
    """Verify scheme and host validation."""
    valid, err, _ = validate_target_url("ftp://example.com/file.txt")
    assert valid is False
    assert "Invalid protocol" in err

    valid, err, _ = validate_target_url("http://localhost:8000/docs")
    assert valid is False
    assert "forbidden" in err or "private" in err

    valid, err, _ = validate_target_url("http://127.0.0.1:8000/api/v1/users")
    assert valid is False

    valid, err, _ = validate_target_url("http://169.254.169.254/latest/meta-data/")
    assert valid is False


def test_capture_url_endpoint_enforces_ssrf_protection():
    """Verify POST /capture/url rejects internal/localhost destinations with 400 Bad Request."""
    import uuid
    email = f"ssrf_tester_{uuid.uuid4().hex[:8]}@humancache.ai"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "SSRF Tester"
    })
    token = reg_res.json()["session_token"]

    # Attempt capture on localhost
    res = client.post(
        "/api/v1/capture/url",
        json={"url": "http://127.0.0.1:8000/health"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 400
    assert "Security verification failed" in res.json()["detail"]


def test_text_capture_and_ai_category_recommendation():
    """Verify text snippet capture and AI category suggestion."""
    import uuid
    email = f"text_capture_{uuid.uuid4().hex[:8]}@humancache.ai"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "Capture User"
    })
    token = reg_res.json()["session_token"]
    user_id = reg_res.json()["user"]["id"]

    # Pre-create category for Physics
    cat_res = client.post(
        "/api/v1/categories",
        json={"name": "Quantum Physics", "color": "#38bdf8"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert cat_res.status_code == 200
    physics_cat_id = cat_res.json()["id"]

    # Submit quantum mechanics text excerpt
    sample_text = (
        "Quantum superposition is a fundamental principle of quantum mechanics. "
        "It states that much like waves in classical physics, any two or more quantum states "
        "can be added together and the result will be another valid quantum state."
    )
    cap_res = client.post(
        "/api/v1/capture/text",
        json={
            "content_text": sample_text,
            "title": "Quantum Superposition Notes",
            "source_type": "selection"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert cap_res.status_code == 200
    cap_data = cap_res.json()
    assert cap_data["status"] == "pending_review"
    assert cap_data["title"] == "Quantum Superposition Notes"
    # Should recommend existing Quantum Physics category
    assert cap_data["recommended_category_id"] == physics_cat_id
    assert "Physics" in cap_data["recommended_category_name"]

    capture_id = cap_data["id"]

    # Verify Capture appears in user's inbox
    inbox_res = client.get("/api/v1/capture/inbox", headers={"Authorization": f"Bearer {token}"})
    assert inbox_res.status_code == 200
    inbox_items = inbox_res.json()
    assert any(item["id"] == capture_id for item in inbox_items)

    # Confirm capture
    confirm_res = client.post(
        f"/api/v1/capture/{capture_id}/confirm",
        json={"category_id": physics_cat_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert confirm_res.status_code == 200
    doc_id = confirm_res.json()["document_id"]
    assert doc_id is not None

    # Verify idempotent confirm: second confirm returns same doc
    confirm_again = client.post(
        f"/api/v1/capture/{capture_id}/confirm",
        json={"category_id": physics_cat_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert confirm_again.status_code == 200
    assert confirm_again.json()["document_id"] == doc_id

    # Verify document now in documents list
    docs_res = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert docs_res.status_code == 200
    assert any(d["id"] == doc_id for d in docs_res.json())


def test_cross_user_capture_isolation():
    """Verify User B cannot access, confirm, or delete User A's capture."""
    import uuid
    # User A
    user_a = client.post("/api/v1/auth/register", json={
        "email": f"user_a_{uuid.uuid4().hex[:8]}@humancache.ai",
        "password": "password123",
        "name": "User A"
    }).json()
    token_a = user_a["session_token"]

    # User B
    user_b = client.post("/api/v1/auth/register", json={
        "email": f"user_b_{uuid.uuid4().hex[:8]}@humancache.ai",
        "password": "password123",
        "name": "User B"
    }).json()
    token_b = user_b["session_token"]


    # User A captures text
    cap_res = client.post(
        "/api/v1/capture/text",
        json={"content_text": "Confidential Study Notes for User A", "title": "Private Notes"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    cap_id = cap_res.json()["id"]

    # User B tries to view inbox -> should not see User A's capture
    inbox_b = client.get("/api/v1/capture/inbox", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert not any(i["id"] == cap_id for i in inbox_b)

    # User B tries to confirm User A's capture -> 404
    confirm_b = client.post(
        f"/api/v1/capture/{cap_id}/confirm",
        json={},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert confirm_b.status_code == 404

    # User B tries to discard User A's capture -> 404
    delete_b = client.delete(
        f"/api/v1/capture/{cap_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert delete_b.status_code == 404

    # User A discards capture -> succeeds
    delete_a = client.delete(
        f"/api/v1/capture/{cap_id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert delete_a.status_code == 200
