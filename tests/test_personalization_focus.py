import pytest
from unittest.mock import MagicMock
from backend.personalization_focus import (
    derive_preference_learning_focus,
    generate_dashboard_focus
)


class MockPreference:
    def __init__(
        self,
        user_roles=None,
        learning_goals_list=None,
        target_exam="",
        curriculum="",
        learning_context=None,
        subjects_of_interest=None,
        custom_subjects=None,
        custom_other_responses=None,
        onboarding_completed=True
    ):
        self.user_roles = user_roles or []
        self.learning_goals_list = learning_goals_list or []
        self.target_exam = target_exam
        self.curriculum = curriculum
        self.learning_context = learning_context or {}
        self.subjects_of_interest = subjects_of_interest or []
        self.custom_subjects = custom_subjects or []
        self.custom_other_responses = custom_other_responses or {}
        self.onboarding_completed = onboarding_completed


def test_bcom_business_management_learner():
    # Scenario 1: B.Com / Business Management learner
    prefs = MockPreference(
        user_roles=["college_student"],
        learning_goals_list=["commerce_business"],
        target_exam="",
        learning_context={
            "college_degree": "B.Com",
            "college_field": "Business Management"
        },
        subjects_of_interest=["Business Studies & Management", "Accountancy & Bookkeeping"]
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert res["focus_title"] == "Business Management & Commerce"
    assert "Upload your notes" in res["focus_prompt"]
    assert "JEE" not in res["focus_title"]
    assert "High-Yield" not in res["focus_title"]


def test_jee_aspirant_learner():
    # Scenario 2: JEE learner
    prefs = MockPreference(
        user_roles=["competitive_aspirant"],
        learning_goals_list=["competitive_exam"],
        target_exam="JEE Advanced & Main",
        subjects_of_interest=["Physics", "Chemistry", "Mathematics & Statistics"]
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert res["focus_title"] == "JEE Main & Advanced"
    assert "Upload your study materials" in res["focus_prompt"]


def test_arts_history_learner():
    # Scenario 3: Arts / History learner
    prefs = MockPreference(
        user_roles=["college_student"],
        learning_goals_list=["creative_arts"],
        target_exam="",
        learning_context={
            "college_degree": "B.A. History",
            "college_field": "Modern History"
        },
        subjects_of_interest=["History", "Philosophy & Ethics"]
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert res["focus_title"] == "History & Humanities"
    assert "historical concepts" in res["focus_prompt"]


def test_law_learner():
    # Scenario 4: Law learner (LL.B or CLAT)
    prefs = MockPreference(
        user_roles=["college_student"],
        target_exam="",
        learning_context={
            "college_degree": "LL.B",
            "college_field": "Constitutional Law"
        },
        subjects_of_interest=["Constitutional Law & Jurisprudence"]
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert res["focus_title"] == "Legal Studies"
    assert "legal concepts" in res["focus_prompt"]


def test_personal_skill_development_learner():
    # Scenario 5: Personal skill development learner
    prefs = MockPreference(
        user_roles=["self_directed_learner"],
        learning_goals_list=["personal_growth"],
        target_exam="",
        subjects_of_interest=["Public Speaking & Debate", "Productivity & Time Architecture"]
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert "Personal Development" in res["focus_title"]
    assert "Upload your notes or guides" in res["focus_prompt"]


def test_multiple_selected_interests():
    # Scenario 6: Learner with multiple selected interests (Commerce + Tech)
    prefs = MockPreference(
        user_roles=["college_student"],
        learning_goals_list=["commerce_business", "technical_craft"],
        target_exam="",
        subjects_of_interest=["Accountancy & Bookkeeping", "Computer Science & Algorithms"]
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert "Business Management & Technology" in res["focus_title"] or "Commerce & Technology" in res["focus_title"]
    assert "multi-disciplinary" in res["focus_prompt"]


def test_custom_subject_learner():
    # Scenario 7: Learner with custom subject
    prefs = MockPreference(
        user_roles=["self_directed_learner"],
        learning_goals_list=["other"],
        target_exam="",
        custom_subjects=["Astrobiology"],
        custom_other_responses={"goal_other": "Astrobiology & Space Exploration"}
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert "Astrobiology" in res["focus_title"]
    assert "Upload your resources" in res["focus_prompt"]


def test_no_preferences_learner():
    # Scenario 8: Learner with no saved preferences
    prefs = MockPreference()
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert res["focus_title"] == "Your learning journey starts here"
    assert "Upload your first resource" in res["focus_prompt"]


def test_none_preference_object():
    # Scenario 8b: None preference object
    res = generate_dashboard_focus(None, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert res["focus_title"] == "Your learning journey starts here"


def test_no_fabricated_revision_for_empty_account():
    # Scenario 9: Even with JEE selected, if user has 0 documents, NO fabricated 'High-Yield Revision'
    prefs = MockPreference(
        user_roles=["competitive_aspirant"],
        learning_goals_list=["competitive_exam"],
        target_exam="JEE Advanced & Main"
    )
    res = generate_dashboard_focus(prefs, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert "High-Yield Revision" not in res["focus_title"]
    assert res["focus_title"] == "JEE Main & Advanced"


def test_activity_based_recommendation_when_materials_exist():
    # Scenario 10: User with real uploaded materials and review due topic
    prefs = MockPreference(
        user_roles=["college_student"],
        learning_goals_list=["commerce_business"]
    )
    mock_topic = MagicMock()
    mock_topic.canonical_name = "Corporate Finance"

    mock_state = MagicMock()
    mock_state.status = "review_due"
    mock_state.estimated_retention = 0.45
    mock_state.topic = mock_topic

    res = generate_dashboard_focus(
        prefs=prefs,
        topics=[mock_topic],
        mem_states=[mock_state],
        upcoming_exams=[],
        total_docs=3
    )
    assert res["focus_title"] == "Active Recall: Corporate Finance"
    assert "Corporate Finance" in res["focus_prompt"]
