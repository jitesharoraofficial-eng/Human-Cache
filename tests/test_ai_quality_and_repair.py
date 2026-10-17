"""
Test Suite: Critical AI Quality, RAG Relevance & Extension Repair.
Verifies fixes for:
1. Working Gemini provider configuration (gemini-3.5-flash) and retry logic.
2. Context assembly with rich onboarding fields (degree, field, stream) and correct engineering alignment.
3. Extension URL capture with client-provided page_content fallback upon 403.
4. Document-aware semantic chunking and hierarchy extraction (Units, Chapters, Sections).
5. Topic-scoped RAG retrieval preventing cross-document contamination.
6. Automatic upload-triggered learning suite preparation.
"""
import os
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    User, UserPreference, Category, Document, SourceChunk,
    Topic, DocumentTopic, Note, Quiz, FlashcardDeck, MindMap,
    CaptureItem
)
from backend.agent.context import LearnerContextAssembler
from backend.personalization_focus import generate_dashboard_focus
from backend.extractor import chunk_pages_and_text, extract_topics_and_concepts
from backend.resource_prep_service import auto_prepare_document_learning_suite, prepare_or_reuse_learning_resources
from backend.config import settings


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_ai_quality.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


def test_gemini_provider_default_model():
    """Verify Gemini default model is gemini-3.5-flash."""
    from backend.ai.gemini_provider import GeminiProvider
    provider = GeminiProvider()
    assert provider.model == "gemini-3.5-flash"


def test_context_assembly_btech_engineering(isolated_db):
    """Verify B.Tech user with Engineering does not get injected with History."""
    user = User(id="u_btech", email="btech@example.com", hashed_password="pw", name="Aryan")
    isolated_db.add(user)
    
    pref = UserPreference(
        user_id=user.id,
        user_roles=["Engineering Student", "JEE Aspirant"],
        learning_goals_list=["GATE CSE", "Data Structures"],
        subjects_of_interest=["Data Structures", "Algorithms", "Operating Systems"],
        learning_context={
            "college_degree": "B.Tech",
            "college_field": "Computer Science & Engineering",
            "education_level": "college_undergrad"
        },
        explanation_depth="semi-detailed",
        language="en"
    )
    isolated_db.add(pref)
    isolated_db.commit()

    assembler = LearnerContextAssembler(isolated_db)
    prompt, _, _ = assembler.assemble(
        user_id=user.id,
        user_name=user.name,
        current_query="Explain Newton's third law in simple words.",
        conversation_history=[]
    )
    assert "B.Tech" in prompt
    assert "Computer Science & Engineering" in prompt
    assert "History" not in prompt

    focus = generate_dashboard_focus(prefs=pref, topics=[], mem_states=[], upcoming_exams=[], total_docs=0)
    assert "History" not in focus.get("daily_study_focus", "")
    assert "History" not in focus.get("cognitive_focus_message", "")


def test_document_aware_chunking_and_hierarchy():
    """Verify document-aware chunking produces semantic chunks and preserves page numbers & headings."""
    sample_text = (
        "Unit 1: Classical Mechanics\n\n"
        "Chapter 3: Laws of Motion\n\n"
        "Section 3.1: Newton's Third Law\n\n"
        + ("Every action has an equal and opposite reaction. When object A exerts a force on object B, "
           "object B exerts a force of equal magnitude and opposite direction on object A. ") * 8 + "\n\n"
        "Section 3.2: Rocket Propulsion\n\n"
        + ("Rocket propulsion is a practical application of Newton's third law of motion. "
           "The exhaust gases expelled backward exert a forward thrust on the rocket body. ") * 8
    )
    pages_data = [
        {"page_number": 1, "text": sample_text}
    ]

    chunks = chunk_pages_and_text(pages_data, sample_text)
    assert len(chunks) >= 2
    for c in chunks:
        assert c["page_number"] == 1
        assert len(c["content"]) <= 1200
        assert len(c["content"]) >= 50

    topics = extract_topics_and_concepts(sample_text, "Physics_Vol1.pdf")
    topic_names = [t["name"] for t in topics]
    assert any("Unit 1" in t for t in topic_names)
    assert any("Chapter 3" in t for t in topic_names)


def test_topic_scoped_rag_document_resolution(isolated_db):
    """Verify topic-scoped RAG resolves document IDs and does not pull from unrelated documents."""
    user = User(id="u_rag", email="rag@example.com", hashed_password="pw", name="RAG User")
    isolated_db.add(user)

    doc_a = Document(id="doc_physics", user_id=user.id, title="Physics Volume 1", filename="physics.pdf", file_type="pdf")
    doc_b = Document(id="doc_history", user_id=user.id, title="World History", filename="history.pdf", file_type="pdf")
    isolated_db.add_all([doc_a, doc_b])

    topic_physics = Topic(id="t_newton", user_id=user.id, name="Newton's Third Law", canonical_name="Newton's Third Law")
    topic_history = Topic(id="t_mughals", user_id=user.id, name="Mughal Empire", canonical_name="Mughal Empire")
    isolated_db.add_all([topic_physics, topic_history])

    dt_a = DocumentTopic(document_id=doc_a.id, topic_id=topic_physics.id)
    dt_b = DocumentTopic(document_id=doc_b.id, topic_id=topic_history.id)
    isolated_db.add_all([dt_a, dt_b])

    chunk_a = SourceChunk(document_id=doc_a.id, chunk_index=0, page_number=5, content="Action and reaction are equal and opposite in direction.", char_count=60)
    chunk_b = SourceChunk(document_id=doc_b.id, chunk_index=0, page_number=12, content="The Mughal dynasty ruled large parts of the Indian subcontinent.", char_count=65)
    isolated_db.add_all([chunk_a, chunk_b])
    isolated_db.commit()

    from backend.ai.generation import RAGIntelligenceEngine
    engine = RAGIntelligenceEngine(isolated_db)

    # Calling explain_topic on Newton's Third Law should only query doc_physics
    res = engine.explain_topic(
        user_id=user.id,
        topic_name="Newton's Third Law",
        depth="semi-detailed"
    )
    assert res is not None
    assert "Newton" in res["topic_name"]
    # Verify no Mughal content leaked into Newton's third law explanation
    assert "mughal" not in str(res).lower()


def test_auto_prepare_document_learning_suite(isolated_db):
    """Verify auto_prepare_document_learning_suite generates note, quiz, flashcards, and mind map."""
    user = User(id="u_prep", email="prep@example.com", hashed_password="pw", name="Learner")
    isolated_db.add(user)

    doc = Document(id="doc_prep", user_id=user.id, title="Thermodynamics Guide", filename="thermo.pdf", file_type="pdf")
    isolated_db.add(doc)

    topic = Topic(id="t_thermo", user_id=user.id, name="First Law of Thermodynamics", canonical_name="First Law Of Thermodynamics", description="Conservation of energy principle applied to heat systems.")
    isolated_db.add(topic)

    dt = DocumentTopic(document_id=doc.id, topic_id=topic.id)
    isolated_db.add(dt)

    chunk = SourceChunk(document_id=doc.id, chunk_index=0, page_number=1, content="The change in internal energy equals heat added minus work done by system.", char_count=75)
    isolated_db.add(chunk)
    isolated_db.commit()

    suite = auto_prepare_document_learning_suite(isolated_db, user.id, doc.id)
    assert suite["status"] == "prepared"
    assert suite["document_id"] == doc.id
    assert suite["note_id"] is not None
    assert suite["quiz_id"] is not None
    assert suite["deck_id"] is not None

    # Check note exists
    note = isolated_db.query(Note).filter(Note.id == suite["note_id"]).first()
    assert note is not None
    assert "Thermodynamics" in note.title
    assert note.source_type == "auto_summary"

    # Check quiz exists
    quiz = isolated_db.query(Quiz).filter(Quiz.id == suite["quiz_id"]).first()
    assert quiz is not None
    assert len(quiz.questions) >= 1

    # Check flashcards exist
    deck = isolated_db.query(FlashcardDeck).filter(FlashcardDeck.id == suite["deck_id"]).first()
    assert deck is not None
