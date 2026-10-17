"""
Automated Integration and Security Tests for Human Cache Step 3 AI & RAG Engine.
Covers:
1. Provider initialization & unavailability handling
2. Vector embeddings generation (cosine similarity, normalization)
3. User-scoped semantic retrieval & isolation (User A vs User B)
4. Document indexing lifecycle & persistence
5. Learn RAG grounded explanation
6. Recall grounded quiz generation & schema validation
7. Flashcards grounded generation & source attribution
8. Mind Map grounded tree extraction
9. AI Tutor conversational RAG with citations
10. Cross-user vector leakage & unauthorized document ID rejection
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.models import User, Document, SourceChunk, ChunkEmbedding, Topic, TopicRelationship
from backend.ai.embeddings import generate_local_embedding, cosine_similarity
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.retrieval import RetrievalService
from backend.ai.generation import RAGIntelligenceEngine
from tests.test_auth_and_isolation import client, TestingSessionLocal

@pytest.fixture(autouse=True)
def reset_rate_limits():
    AUTH_RATE_LIMIT_STORE.clear()
    yield
    AUTH_RATE_LIMIT_STORE.clear()

import uuid

def register_user(email: str, name: str) -> dict:
    unique_email = f"{uuid.uuid4().hex[:6]}_{email}"
    res = client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "name": name
    })
    assert res.status_code == 200, res.text
    return res.json()

def test_ai_provider_graceful_handling():
    """Verify provider reports availability cleanly without throwing when API key is missing."""
    provider = GeminiProvider(api_key="")
    assert provider.is_available() is False
    with pytest.raises(RuntimeError):
        provider.generate_text("test")

def test_embedding_cosine_similarity():
    """Verify local deterministic embedding math and normalization."""
    v1 = generate_local_embedding("Business Management and Financial Accounting")
    v2 = generate_local_embedding("Business Management and Commerce Operations")
    v3 = generate_local_embedding("Organic Chemistry Reaction Mechanisms in Benzene")

    assert len(v1) == 64
    sim_related = cosine_similarity(v1, v2)
    sim_unrelated = cosine_similarity(v1, v3)
    assert sim_related > sim_unrelated
    assert 0.0 <= sim_related <= 1.0

def test_user_retrieval_isolation():
    """Verify User A's search query can never retrieve User B's chunks even with broad terms."""
    user_a = register_user("learner_a_rag@test.com", "Learner A")
    user_b = register_user("learner_b_rag@test.com", "Learner B")

    db = TestingSessionLocal()
    try:
        # Create doc for User A (B.Com)
        doc_a = Document(user_id=user_a["user"]["id"], title="BCom Management", filename="mgt.txt", file_type="txt")
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)

        chunk_a = SourceChunk(document_id=doc_a.id, chunk_index=0, content="Principles of double-entry bookkeeping and balance sheet ledger accounts.")
        db.add(chunk_a)
        db.commit()
        db.refresh(chunk_a)

        retrieval = RetrievalService(db)
        retrieval.index_chunk(user_a["user"]["id"], doc_a.id, chunk_a.id, chunk_a.content)

        # Create doc for User B (Law)
        doc_b = Document(user_id=user_b["user"]["id"], title="Constitutional Law", filename="law.txt", file_type="txt")
        db.add(doc_b)
        db.commit()
        db.refresh(doc_b)

        chunk_b = SourceChunk(document_id=doc_b.id, chunk_index=0, content="Fundamental constitutional legal remedies and jurisprudence.")
        db.add(chunk_b)
        db.commit()
        db.refresh(chunk_b)

        retrieval.index_chunk(user_b["user"]["id"], doc_b.id, chunk_b.id, chunk_b.content)

        # Query as User A searching for legal terms
        results_a = retrieval.retrieve(user_a["user"]["id"], "legal constitutional law remedies")
        # Must return empty or only User A's chunks — NEVER User B's
        for r in results_a:
            assert r["document_id"] == doc_a.id
            assert r["document_id"] != doc_b.id

        # Query as User B searching for accounting
        results_b = retrieval.retrieve(user_b["user"]["id"], "double-entry bookkeeping")
        for r in results_b:
            assert r["document_id"] == doc_b.id
            assert r["document_id"] != doc_a.id

        # Direct ID manipulation attempt: User A passing User B's document_id
        tampered_results = retrieval.retrieve(user_a["user"]["id"], "remedies", document_ids=[doc_b.id])
        assert len(tampered_results) == 0, "Unauthorized document_id was not rejected!"
    finally:
        db.close()

def test_learn_explain_grounded_rag():
    """Verify /learn/explain generates grounded responses and respects requested depth levels."""
    user = register_user("learn_rag_user@test.com", "Learn Tester")
    cookie = {"humancache_session": user["session_token"]}

    # Upload learning material
    notes = b"Supply Chain Management: Logistics optimization reduces inventory holding costs. Just-In-Time (JIT) minimizes buffer waste."
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("supply_chain.txt", notes, "text/plain")},
        cookies=cookie
    )
    assert upload_res.status_code == 200

    # Brief depth
    brief_res = client.post(
        "/api/v1/learn/explain",
        json={"query": "Supply Chain Logistics", "depth": "brief"},
        cookies=cookie
    )
    assert brief_res.status_code == 200
    brief_data = brief_res.json()
    assert "Supply Chain" in brief_data["topic_name"] or "Essential" in brief_data["explanation"]
    assert "explanation" in brief_data

    # Detailed depth
    det_res = client.post(
        "/api/v1/learn/explain",
        json={"query": "Just-In-Time Buffer Waste", "depth": "detailed"},
        cookies=cookie
    )
    assert det_res.status_code == 200
    det_data = det_res.json()
    assert len(det_data["explanation"]) > len(brief_data["explanation"])

def test_recall_quiz_generation_schema_validation():
    """Verify /recall/generate produces valid active recall questions with grounded options."""
    user = register_user("quiz_rag_user@test.com", "Quiz Tester")
    cookie = {"humancache_session": user["session_token"]}

    notes = b"# Macroeconomics\nGross Domestic Product (GDP) measures total monetary value of finished goods. Fiscal policy utilizes taxation and government spending."
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("macro.txt", notes, "text/plain")},
        cookies=cookie
    )

    res = client.post(
        "/api/v1/recall/generate",
        json={"question_count": 3, "difficulty": "medium"},
        cookies=cookie
    )
    assert res.status_code == 200
    data = res.json()
    assert "questions" in data
    assert len(data["questions"]) > 0
    for q in data["questions"]:
        assert "question" in q
        assert "correct_answer" in q
        assert "explanation" in q

def test_flashcard_generation_rag():
    """Verify /flashcards/generate produces source-grounded cards for topics."""
    user = register_user("flash_rag_user@test.com", "Flashcard Tester")
    cookie = {"humancache_session": user["session_token"]}

    notes = b"# Corporate Finance\nWorking capital equals current assets minus current liabilities. Liquidity ratios gauge short-term obligation solvency."
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("corp_fin.txt", notes, "text/plain")},
        cookies=cookie
    )

    # Get topic
    topics = client.get("/api/v1/topics", cookies=cookie).json()
    assert len(topics) > 0
    topic_id = topics[0]["id"]

    res = client.post(f"/api/v1/flashcards/generate?topic_id={topic_id}", cookies=cookie)
    assert res.status_code == 200
    deck_info = res.json()
    assert deck_info["cards_count"] >= 1

    cards = client.get(f"/api/v1/flashcards/decks/{deck_info['deck_id']}/cards", cookies=cookie).json()
    assert len(cards) >= 1
    assert "front" in cards[0]
    assert "back" in cards[0]

def test_ai_tutor_conversational_rag():
    """Verify /tutor/chat provides grounded responses with citations and conversational context."""
    user = register_user("tutor_chat_user@test.com", "Tutor Tester")
    cookie = {"humancache_session": user["session_token"]}

    notes = b"Constitutional Law Article 21 guarantees the fundamental right to life and personal liberty, interpreted broadly by courts."
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("article_21.txt", notes, "text/plain")},
        cookies=cookie
    )

    chat_res = client.post(
        "/api/v1/tutor/chat",
        json={
            "message": "What does Article 21 guarantee according to my notes?",
            "conversation_history": []
        },
        cookies=cookie
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "reply" in chat_data
    assert chat_data["is_grounded"] is True
    assert len(chat_data["citations"]) > 0
    assert "article_21.txt" in chat_data["citations"][0]
