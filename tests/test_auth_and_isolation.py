import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.database import Base, get_db
from backend.models import (
    User, UserPreference, Category, Document, Topic, 
    Quiz, Note, Exam, StudyTask, Notification
)
from backend.config import settings

# Test database setup (isolated SQLite file for testing)
TEST_DB_PATH = "test_human_cache.db"
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except:
        pass

SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create tables
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Clear in-memory auth rate limiting table between tests."""
    AUTH_RATE_LIMIT_STORE.clear()

@pytest.fixture(scope="session", autouse=True)
def cleanup():
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except:
            pass

# =====================================================================
# 1. AUTHENTICATION & SESSION TESTS
# =====================================================================

def test_register_new_user():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "securepassword123", "name": "Alice"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["name"] == "Alice"
    assert "session_token" in data
    # Verify HttpOnly session cookie was set
    assert settings.SESSION_COOKIE_NAME in response.cookies

def test_register_duplicate_email():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "anotherpassword", "name": "Alice Duplicate"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()

def test_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()

def test_login_nonexistent_email():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    # Generic message, preventing account enumeration
    assert "invalid email or password" in response.json()["detail"].lower()

def test_login_success_and_auth_me():
    # Login Alice
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"}
    )
    assert response.status_code == 200
    token = response.json()["session_token"]

    # Verify session via cookie
    me_resp = client.get("/api/v1/auth/me", cookies={settings.SESSION_COOKIE_NAME: token})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "alice@example.com"
    assert me_data["name"] == "Alice"

    # Verify session via Authorization Bearer fallback header
    bearer_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert bearer_resp.status_code == 200
    assert bearer_resp.json()["email"] == "alice@example.com"

def test_logout_revokes_session():
    # Login to acquire fresh session
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"}
    )
    token = login_resp.json()["session_token"]

    # Call logout
    logout_resp = client.post("/api/v1/auth/logout", cookies={settings.SESSION_COOKIE_NAME: token})
    assert logout_resp.status_code == 200

    # Ensure session token is now invalid / rejected
    verify_resp = client.get("/api/v1/auth/me", cookies={settings.SESSION_COOKIE_NAME: token})
    assert verify_resp.status_code == 401

def test_unauthenticated_request_rejected():
    # Protected endpoints without session token must be rejected with 401
    resp = client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 401

    resp2 = client.get("/api/v1/categories")
    assert resp2.status_code == 401

# =====================================================================
# 2. MULTI-TENANT USER DATA ISOLATION TESTS
# =====================================================================

def test_user_data_isolation_categories_and_notes():
    # 1. Register User Bob
    client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "passwordbob123", "name": "Bob"}
    )
    bob_login = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "passwordbob123"}
    )
    assert bob_login.status_code == 200, bob_login.text
    bob_token = bob_login.json()["session_token"]

    # 2. Login Alice
    alice_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"}
    )
    assert alice_login.status_code == 200, alice_login.text
    alice_token = alice_login.json()["session_token"]

    # 3. Alice creates a category
    alice_cat_resp = client.post(
        "/api/v1/categories",
        json={"name": "Alice's Secret Biology", "description": "Alice notes", "color": "#10b981"},
        cookies={settings.SESSION_COOKIE_NAME: alice_token}
    )
    assert alice_cat_resp.status_code == 200
    alice_cat_id = alice_cat_resp.json()["id"]

    # 4. Bob lists categories -> Must NOT see Alice's category
    bob_cats = client.get("/api/v1/categories", cookies={settings.SESSION_COOKIE_NAME: bob_token}).json()
    bob_cat_names = [c["name"] for c in bob_cats]
    assert "Alice's Secret Biology" not in bob_cat_names

    # 5. Alice creates a private Note
    alice_note_resp = client.post(
        "/api/v1/notes",
        json={"title": "Alice's Personal Diary", "content": "Private study reflections", "tags": ["confidential"]},
        cookies={settings.SESSION_COOKIE_NAME: alice_token}
    )
    assert alice_note_resp.status_code == 200
    alice_note_id = alice_note_resp.json()["id"]

    # 6. Bob lists notes -> Must NOT see Alice's note
    bob_notes = client.get("/api/v1/notes", cookies={settings.SESSION_COOKIE_NAME: bob_token}).json()
    bob_note_ids = [n["id"] for n in bob_notes]
    assert alice_note_id not in bob_note_ids

    # 7. Bob attempts to DELETE Alice's note -> Must fail / have no effect on Alice's note
    del_resp = client.delete(f"/api/v1/notes/{alice_note_id}", cookies={settings.SESSION_COOKIE_NAME: bob_token})
    # Alice verifies note still exists intact
    alice_notes = client.get("/api/v1/notes", cookies={settings.SESSION_COOKIE_NAME: alice_token}).json()
    assert any(n["id"] == alice_note_id for n in alice_notes)

# =====================================================================
# 3. EXAM & STUDY TASK ISOLATION TESTS
# =====================================================================

def test_exam_and_task_isolation():
    # Login Alice and Bob
    alice_token = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"}
    ).json()["session_token"]

    bob_token = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "passwordbob123"}
    ).json()["session_token"]

    # Alice creates an exam
    alice_exam = client.post(
        "/api/v1/exams",
        json={
            "subject": "Organic Chemistry Final",
            "exam_date": "2026-11-20T09:00:00",
            "exam_time_str": "09:00 AM",
            "total_preparation_days": 10
        },
        cookies={settings.SESSION_COOKIE_NAME: alice_token}
    ).json()
    alice_exam_id = alice_exam["id"]

    # Bob lists exams -> Alice's exam must NOT be present
    bob_exams = client.get("/api/v1/exams", cookies={settings.SESSION_COOKIE_NAME: bob_token}).json()
    assert not any(e["id"] == alice_exam_id for e in bob_exams)

    # Bob attempts to access Alice's exam tasks -> Empty list
    bob_tasks = client.get(f"/api/v1/exams/{alice_exam_id}/tasks", cookies={settings.SESSION_COOKIE_NAME: bob_token}).json()
    assert len(bob_tasks) == 0

# =====================================================================
# 4. PATH TRAVERSAL & STORAGE ISOLATION TEST
# =====================================================================

def test_path_traversal_upload_protection():
    alice_token = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"}
    ).json()["session_token"]

    # Attempt path traversal via filename
    malicious_files = {"file": ("../../etc_passwd.txt", b"secret root contents", "text/plain")}
    resp = client.post(
        "/api/v1/documents/upload",
        files=malicious_files,
        cookies={settings.SESSION_COOKIE_NAME: alice_token}
    )
    # The endpoint should either sanitize the filename to basename or succeed strictly within user's isolated storage
    if resp.status_code == 200:
        doc_data = resp.json()
        assert "document_id" in doc_data
        # Verify file did NOT write to root directory
        assert not os.path.exists("./etc_passwd.txt")

# =====================================================================
# 5. DEMO RESET PROTECTION TEST
# =====================================================================

def test_demo_reset_forbidden_for_regular_users():
    alice_token = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"}
    ).json()["session_token"]

    reset_resp = client.post("/api/v1/demo/reset", cookies={settings.SESSION_COOKIE_NAME: alice_token})
    assert reset_resp.status_code == 403
    assert "restricted to demo accounts" in reset_resp.json()["detail"].lower()

# =====================================================================
# 6. ROUTE REGISTRATION & OPENAPI REGRESSION TEST
# =====================================================================

def test_auth_routes_registered_in_app():
    """Verify that all auth endpoints exist in app routing and openapi schema."""
    registered_routes = [route.path for route in app.routes]
    expected_auth_routes = [
        f"{settings.API_V1_STR}/auth/register",
        f"{settings.API_V1_STR}/auth/login",
        f"{settings.API_V1_STR}/auth/me",
        f"{settings.API_V1_STR}/auth/logout"
    ]
    for route in expected_auth_routes:
        assert route in registered_routes, f"Expected route {route} not registered in FastAPI app"

    openapi_schema = app.openapi()
    for route in expected_auth_routes:
        assert route in openapi_schema["paths"], f"Expected route {route} missing from openapi schema"

# =====================================================================
# 7. UNIVERSAL ONBOARDING & PREFERENCE PERSISTENCE TESTS
# =====================================================================

def test_onboarding_preferences_save_and_category_curation_commerce_music():
    """Tests a user interested in both Commerce and Music (cross-stream learner)."""
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "priya@example.com", "password": "password123", "name": "Priya"}
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["session_token"]

    pref_payload = {
        "user_roles": ["working_professional", "creative_artist"],
        "learning_goals_list": ["commerce_business", "creative_arts"],
        "learning_goals": "Business, Finance, Music Theory",
        "target_exam": "CFA Level 1",
        "curriculum": "Global Standard",
        "subjects_of_interest": [
            "Accountancy & Bookkeeping",
            "Finance & Financial Markets",
            "Music Theory & Instruments"
        ],
        "custom_subjects": ["Vocal Training"],
        "explanation_depth": "detailed",
        "teaching_styles": ["analogies", "practical_applications"],
        "language": "en",
        "quiz_difficulty": "medium",
        "daily_study_time_minutes": 60,
        "preferred_study_hours": "evening",
        "onboarding_completed": True
    }

    # Save preferences via HttpOnly cookie
    pref_resp = client.put(
        "/api/v1/users/preferences",
        json=pref_payload,
        cookies={settings.SESSION_COOKIE_NAME: token}
    )
    assert pref_resp.status_code == 200, pref_resp.text

    # Verify user profile returns saved preferences
    profile_resp = client.get("/api/v1/users/me", cookies={settings.SESSION_COOKIE_NAME: token})
    assert profile_resp.status_code == 200
    prefs = profile_resp.json()["preferences"]
    assert "Accountancy & Bookkeeping" in prefs["subjects_of_interest"]
    assert "Music Theory & Instruments" in prefs["subjects_of_interest"]
    assert "Vocal Training" in prefs["custom_subjects"]
    assert prefs["onboarding_completed"] is True

    # Verify auto-curated categories were created without duplicates
    cats_resp = client.get("/api/v1/categories", cookies={settings.SESSION_COOKIE_NAME: token})
    assert cats_resp.status_code == 200
    cat_names = [c["name"] for c in cats_resp.json()]
    assert any("accountancy" in n.lower() for n in cat_names)
    assert any("music" in n.lower() for n in cat_names)
    assert any("vocal" in n.lower() for n in cat_names)

def test_onboarding_preferences_history_psychology_public_speaking():
    """Tests a user interested in History, Psychology and Public Speaking (Humanities & Skills)."""
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "rahul@example.com", "password": "password123", "name": "Rahul"}
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["session_token"]

    pref_payload = {
        "user_roles": ["self_directed_learner"],
        "learning_goals_list": ["creative_arts", "personal_growth"],
        "learning_goals": "History, Human Psychology and Oratory Skills",
        "subjects_of_interest": [
            "History",
            "Psychology",
            "Public Speaking & Debate"
        ],
        "custom_subjects": ["Ancient Indian Historiography"],
        "explanation_depth": "balanced",
        "teaching_styles": ["simple_first", "examples_first"],
        "language": "hinglish",
        "onboarding_completed": True
    }

    # Save preferences via Authorization Bearer fallback
    pref_resp = client.put(
        "/api/v1/users/preferences",
        json=pref_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert pref_resp.status_code == 200

    # Verify User isolation: Rahul's categories must NOT appear for Priya
    priya_login = client.post(
        "/api/v1/auth/login",
        json={"email": "priya@example.com", "password": "password123"}
    )
    priya_token = priya_login.json()["session_token"]
    priya_cats = client.get("/api/v1/categories", cookies={settings.SESSION_COOKIE_NAME: priya_token}).json()
    priya_cat_names = [c["name"] for c in priya_cats]
    assert not any("ancient indian historiography" in n.lower() for n in priya_cat_names)

def test_fresh_user_dashboard_has_zero_streak_and_no_fabricated_data():
    """Verify that a brand new user has 0 streak, no fake topics, and empty recent activity."""
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "fresh_learner@example.com", "password": "password123", "name": "Maya Verma"}
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["session_token"]

    dash_resp = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    assert dash_resp.status_code == 200
    data = dash_resp.json()

    # Welcome name must match registered user, NOT Alex
    assert data["welcome_name"] == "Maya"
    # Learning streak must be strictly 0, NOT 6
    assert data["learning_streak_days"] == 0
    # Discovered topics must be 0
    assert data["topics_discovered"] == 0
    assert data["topics_learned"] == 0
    assert data["topics_left_to_learn"] == 0
    # Due counts must be 0
    assert data["review_due_count"] == 0
    assert data["overdue_count"] == 0
    # Retention average must be 0.0
    assert data["retention_average"] == 0.0
    # Tool counts must be 0
    assert data["flashcard_count"] == 0
    assert data["mind_map_count"] == 0
    assert data["note_count"] == 0
    # Recent activity must be empty list, NOT seeded fake events
    assert data["recent_activity"] == []
    # Review due topics list must be empty
    assert data["review_due_topics"] == []
    assert data["learn_again_topics"] == []
    assert data["left_to_learn_topics"] == []

def test_fresh_user_knowledge_graph_and_mind_maps_are_empty():
    """Verify that a fresh user does not inherit demo graphs or mind maps."""
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "graph_learner@example.com", "password": "password123", "name": "Arjun"}
    )
    token = reg_resp.json()["session_token"]

    graph_resp = client.get("/api/v1/knowledge-graph", cookies={settings.SESSION_COOKIE_NAME: token})
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert len(graph_data["nodes"]) == 0
    assert len(graph_data["edges"]) == 0
    assert graph_data["stats"]["total_nodes"] == 0

    mm_resp = client.get("/api/v1/mind-maps", cookies={settings.SESSION_COOKIE_NAME: token})
    assert mm_resp.status_code == 200
    assert mm_resp.json() == []

