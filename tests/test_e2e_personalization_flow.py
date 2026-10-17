import pytest
import uuid
from starlette.testclient import TestClient
from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.config import settings

from tests.test_auth_and_isolation import client


@pytest.fixture(autouse=True)
def clear_rate_limit():
    AUTH_RATE_LIMIT_STORE.clear()
    yield
    AUTH_RATE_LIMIT_STORE.clear()


def test_scenario_1_bcom_business_management_learner():
    """Scenario 1: Newly registered B.Com / Business Management learner."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"jitesh_bcom_{uid}@example.com",
        "password": "password123",
        "name": "Jitesh Sharma"
    })
    assert reg.status_code == 200
    token = reg.json()["session_token"]

    onboard = client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["commerce_business"],
            "learning_goals": "Business, Finance & Entrepreneurship",
            "target_exam": "",
            "curriculum": "",
            "learning_context": {
                "college_degree": "B.Com",
                "college_field": "Business Management"
            },
            "subjects_of_interest": ["Business Studies & Management", "Accountancy & Bookkeeping"],
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )
    assert onboard.status_code == 200

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    assert dash.status_code == 200
    data = dash.json()

    assert data["welcome_name"] == "Jitesh"
    assert data["daily_study_focus"] == "Business Management & Commerce"
    assert "Upload your notes to start building your personal knowledge graph" in data["cognitive_focus_prompt"]
    assert "JEE" not in data["daily_study_focus"]
    assert "High-Yield" not in data["daily_study_focus"]


def test_scenario_2_jee_learner():
    """Scenario 2: Newly registered JEE learner."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"rohit_jee_{uid}@example.com",
        "password": "password123",
        "name": "Rohit Kumar"
    })
    assert reg.status_code == 200
    token = reg.json()["session_token"]

    onboard = client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["competitive_aspirant"],
            "learning_goals_list": ["competitive_exam"],
            "learning_goals": "Competitive Exam Preparation",
            "target_exam": "JEE Advanced & Main",
            "curriculum": "CBSE / NCERT",
            "learning_context": {"prep_stage": "Mid-syllabus & Problem Solving"},
            "subjects_of_interest": ["Physics", "Chemistry", "Mathematics & Statistics"],
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )
    assert onboard.status_code == 200

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    assert dash.status_code == 200
    data = dash.json()

    assert data["welcome_name"] == "Rohit"
    assert data["daily_study_focus"] == "JEE Main & Advanced"
    assert "Upload your study materials" in data["cognitive_focus_prompt"]
    assert "High-Yield Revision" not in data["daily_study_focus"]


def test_scenario_3_arts_history_learner():
    """Scenario 3: Arts / History learner."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"ananya_arts_{uid}@example.com",
        "password": "password123",
        "name": "Ananya Sen"
    })
    token = reg.json()["session_token"]

    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["creative_arts"],
            "learning_goals": "Humanities, Creative Arts & Languages",
            "target_exam": "",
            "learning_context": {"college_degree": "B.A. History", "college_field": "Modern Indian History"},
            "subjects_of_interest": ["History", "Political Science & Civics"],
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    data = dash.json()
    assert data["welcome_name"] == "Ananya"
    assert data["daily_study_focus"] == "History & Humanities"
    assert "historical concepts" in data["cognitive_focus_prompt"]


def test_scenario_4_law_learner():
    """Scenario 4: Law learner."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"kavita_law_{uid}@example.com",
        "password": "password123",
        "name": "Kavita Rao"
    })
    token = reg.json()["session_token"]

    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["college_university"],
            "target_exam": "",
            "learning_context": {"college_degree": "LL.B", "college_field": "Constitutional Law"},
            "subjects_of_interest": ["Constitutional Law & Jurisprudence", "Criminal Law & Penal Code"],
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    data = dash.json()
    assert data["welcome_name"] == "Kavita"
    assert data["daily_study_focus"] == "Legal Studies"
    assert "legal concepts" in data["cognitive_focus_prompt"]


def test_scenario_5_personal_skills_learner():
    """Scenario 5: Personal skill development learner."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"dev_skills_{uid}@example.com",
        "password": "password123",
        "name": "Dev Kapoor"
    })
    token = reg.json()["session_token"]

    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["self_directed_learner"],
            "learning_goals_list": ["personal_growth"],
            "target_exam": "",
            "subjects_of_interest": ["Public Speaking & Debate", "Personal Financial Literacy & Investing"],
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token} )
    data = dash.json()
    assert data["welcome_name"] == "Dev"
    assert "Personal Development" in data["daily_study_focus"]


def test_scenario_6_multiple_interests_learner():
    """Scenario 6: Multiple selected interests (Commerce + Tech)."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"multi_learner_{uid}@example.com",
        "password": "password123",
        "name": "Sameer V"
    })
    token = reg.json()["session_token"]

    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["commerce_business", "technical_craft"],
            "target_exam": "",
            "subjects_of_interest": ["Accountancy & Bookkeeping", "Computer Science & Algorithms"],
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    data = dash.json()
    assert data["welcome_name"] == "Sameer"
    assert "Business Management & Technology" in data["daily_study_focus"] or "Commerce & Technology" in data["daily_study_focus"]
    assert "multi-disciplinary" in data["cognitive_focus_prompt"]


def test_scenario_7_custom_subject_learner():
    """Scenario 7: Custom user-entered subject."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"custom_sub_{uid}@example.com",
        "password": "password123",
        "name": "Tara Sen"
    })
    token = reg.json()["session_token"]

    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["self_directed_learner"],
            "learning_goals_list": ["other"],
            "target_exam": "",
            "custom_subjects": ["Astrobiology & Space Exploration"],
            "custom_other_responses": {"goal_other": "Astrobiology & Space Exploration"},
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    data = dash.json()
    assert data["welcome_name"] == "Tara"
    assert "Astrobiology" in data["daily_study_focus"]


def test_scenario_8_no_saved_preferences_learner():
    """Scenario 8: Learner with no saved preferences."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"empty_pref_{uid}@example.com",
        "password": "password123",
        "name": "Pooja Hegde"
    })
    token = reg.json()["session_token"]

    dash = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token})
    data = dash.json()
    assert data["welcome_name"] == "Pooja"
    assert data["daily_study_focus"] == "Your learning journey starts here"
    assert "Upload your first resource" in data["cognitive_focus_prompt"]


def test_scenario_9_updating_profile_settings():
    """Scenario 9: Learner updating preferences in Profile Settings."""
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"updater_user_{uid}@example.com",
        "password": "password123",
        "name": "Karan Singhania"
    })
    token = reg.json()["session_token"]

    # Initial onboarding: Commerce
    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["commerce_business"],
            "learning_context": {"college_degree": "B.Com"},
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )

    dash1 = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token}).json()
    assert dash1["daily_study_focus"] == "Business Management & Commerce"

    # User updates Profile Settings to Legal Studies
    update_res = client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["college_university"],
            "target_exam": "CLAT / Law Entrances",
            "learning_context": {"college_degree": "LL.B", "college_field": "Corporate Law"},
            "subjects_of_interest": ["Constitutional Law & Jurisprudence"]
        },
        cookies={settings.SESSION_COOKIE_NAME: token}
    )
    assert update_res.status_code == 200

    dash2 = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token}).json()
    assert dash2["daily_study_focus"] == "Legal Studies"


def test_scenario_10_cross_user_isolation():
    """Scenario 10: User A and User B isolation."""
    uid_a = uuid.uuid4().hex[:8]
    uid_b = uuid.uuid4().hex[:8]

    # User A: B.Com
    reg_a = client.post("/api/v1/auth/register", json={
        "email": f"user_a_{uid_a}@example.com",
        "password": "password123",
        "name": "Alice BCom"
    })
    token_a = reg_a.json()["session_token"]
    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["college_student"],
            "learning_goals_list": ["commerce_business"],
            "learning_context": {"college_degree": "B.Com"},
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token_a}
    )

    # User B: JEE
    reg_b = client.post("/api/v1/auth/register", json={
        "email": f"user_b_{uid_b}@example.com",
        "password": "password123",
        "name": "Bob JEE"
    })
    token_b = reg_b.json()["session_token"]
    client.put(
        "/api/v1/users/preferences",
        json={
            "user_roles": ["competitive_aspirant"],
            "learning_goals_list": ["competitive_exam"],
            "target_exam": "JEE Advanced & Main",
            "onboarding_completed": True
        },
        cookies={settings.SESSION_COOKIE_NAME: token_b}
    )

    dash_a = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token_a}).json()
    dash_b = client.get("/api/v1/dashboard/overview", cookies={settings.SESSION_COOKIE_NAME: token_b}).json()

    assert dash_a["welcome_name"] == "Alice"
    assert dash_a["daily_study_focus"] == "Business Management & Commerce"

    assert dash_b["welcome_name"] == "Bob"
    assert dash_b["daily_study_focus"] == "JEE Main & Advanced"
