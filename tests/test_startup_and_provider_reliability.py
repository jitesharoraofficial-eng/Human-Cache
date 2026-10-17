"""
Regression and reliability tests for Backend Startup, Concept Inventory parsing,
Gemini Provider resilience, secret redaction, and startup safety.
"""
import logging
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import (
    Base, User, Document, SourceChunk, DocumentConceptInventory,
    Topic, TopicMemoryState, Notification, Quiz, FlashcardDeck
)
from backend.concept_inventory import ConceptInventoryBuilder, HEADING_PATTERNS
from backend.logging_config import SensitiveDataFilter, sanitize_text
from backend.ai.gemini_provider import (
    GeminiProvider, GeminiAuthError, GeminiQuotaExceededError,
    GeminiRateLimitError, GeminiServiceUnavailableError
)
from backend.notification_engine import run_proactive_notification_cycle
from backend.resource_prep_service import prepare_or_reuse_learning_resources


@pytest.fixture
def isolated_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_user(isolated_db):
    user = User(
        email="test_learner@humancache.ai",
        name="Reliability Test Learner",
        hashed_password="hashed_pw_secret"
    )
    isolated_db.add(user)
    isolated_db.commit()
    isolated_db.refresh(user)
    return user


# --- TASK A: INVENTORY PARSING & NO SUCH GROUP FIX ---

def test_concept_inventory_regex_heading_patterns_safe():
    """Verify that every pattern in HEADING_PATTERNS can be matched and grouped without IndexError."""
    test_cases = [
        ("Introduction:\nText here", "Introduction"),
        ("Chapter 1: Quantum Mechanics\nText here", "Quantum Mechanics"),
        ("Section 10: Thermodynamics Laws\nText here", "Thermodynamics Laws"),
        ("THERMODYNAMICS OVERVIEW\nText here", "THERMODYNAMICS OVERVIEW"),
        ("# Fundamental Axioms\nText here", "Fundamental Axioms"),
    ]
    for text, expected_sub in test_cases:
        matched = False
        for p in HEADING_PATTERNS:
            m = p.search(text)
            if m:
                matched = True
                heading = (m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)).strip().rstrip(':')
                assert expected_sub.lower() in heading.lower()
                break
        assert matched, f"Failed to match heading in: {text!r}"


def test_concept_inventory_builder_end_to_end_no_such_group(isolated_db, sample_user):
    """Reproduce the original document extraction structure and verify no 'no such group' exception occurs."""
    doc = Document(
        user_id=sample_user.id,
        title="Modern Physics & Relativity",
        filename="modern_physics.pdf",
        file_type="pdf",
        processing_status="completed"
    )
    isolated_db.add(doc)
    isolated_db.commit()

    chunk1 = SourceChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Introduction:\nThis section introduces the foundational postulates of special relativity.",
        page_number=1,
        section_heading=None
    )
    chunk2 = SourceChunk(
        document_id=doc.id,
        chunk_index=1,
        content="Inertial Frame: A reference frame in which an object remains at rest unless acted upon.\nFormula: E = mc^2\nStep 1: Measure proper length in rest frame.",
        page_number=2,
        section_heading=None
    )
    isolated_db.add_all([chunk1, chunk2])
    isolated_db.commit()

    builder = ConceptInventoryBuilder(isolated_db)
    # This must not raise IndexError: no such group
    inv = builder.build_or_get_inventory(doc.id, sample_user.id)
    assert inv is not None
    assert inv.sections_count >= 1
    assert any("introduction" in s["heading"].lower() for s in inv.outline_json)
    assert inv.concepts_count >= 1


# --- TASK B: GEMINI PROVIDER RELIABILITY & ERROR DIFFERENTIATION ---

def test_gemini_provider_auth_failure_raises_immediately():
    """Verify 401/403 fails fast with GeminiAuthError and does not cascade through other models."""
    provider = GeminiProvider(api_key="invalid_test_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": {"code": 401, "message": "API_KEY_INVALID"}}'

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        with pytest.raises(GeminiAuthError) as exc_info:
            provider.generate_text("test prompt")
        assert "Gemini authentication failed" in str(exc_info.value)
        # Verify it did NOT retry or cascade to other models
        assert mock_post.call_count == 1


def test_gemini_provider_quota_exhaustion_raises_without_cascading():
    """Verify 429 quota exhaustion raises GeminiQuotaExceededError immediately without cascading."""
    provider = GeminiProvider(api_key="valid_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = '{"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota)."}}'

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        with pytest.raises(GeminiQuotaExceededError) as exc_info:
            provider.generate_text("test prompt")
        assert "quota" in str(exc_info.value).lower()
        # Verify it halted fallback cascade immediately to prevent quota worsening
        assert mock_post.call_count == 1


def test_gemini_provider_503_retries_with_backoff():
    """Verify 503 triggers bounded retry with backoff before advancing."""
    provider = GeminiProvider(api_key="valid_key")
    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_503.headers = {"retry-after": "0.1"}
    resp_503.text = '{"error": {"code": 503, "message": "High demand spike."}}'

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Success after backoff"}]}}]
    }

    # First call returns 503, second attempt on same model returns 200
    with patch("httpx.Client.post", side_effect=[resp_503, resp_200]) as mock_post:
        with patch("time.sleep") as mock_sleep:
            res = provider.generate_text("test prompt")
            assert res == "Success after backoff"
            assert mock_post.call_count == 2
            mock_sleep.assert_called_with(0.1)


def test_explain_topic_returns_provider_unavailable_on_failure(isolated_db, sample_user):
    """Verify explain_topic returns clear provider-unavailable status instead of canned text when provider fails."""
    from backend.ai.generation import RAGIntelligenceEngine
    engine = RAGIntelligenceEngine(isolated_db)

    with patch.object(engine.provider, "is_available", return_value=True):
        with patch.object(engine.provider, "generate_structured", side_effect=GeminiServiceUnavailableError("High demand 503")):
            res = engine.explain_topic(
                user_id=sample_user.id,
                topic_name="Quantum Entanglement"
            )
            assert res.get("coverage_status") == "provider_unavailable"
            assert res.get("provider_unavailable") is True
            assert "temporarily unavailable" in res.get("explanation", "").lower()


# --- TASK C: SECRET REDACTION ---

def test_secret_redaction_in_urls_and_headers():
    """Verify GeminiProvider does not pass API keys in URL query parameters."""
    provider = GeminiProvider(api_key="AIzaSySecretTestKey123456")
    headers = provider._get_auth_headers()
    assert headers["x-goog-api-key"] == "AIzaSySecretTestKey123456"

    # Verify candidate URLs do not contain query parameter ?key=
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        provider.generate_text("hello")
        call_url = mock_post.call_args[0][0]
        assert "?key=" not in call_url
        assert "&key=" not in call_url
        assert "AIzaSySecretTestKey123456" not in call_url


def test_sensitive_data_logging_filter():
    """Verify SensitiveDataFilter redacts query parameters, headers, and secrets in logs."""
    test_key = "AIzaSyFakeSecretKey998877"
    flt = SensitiveDataFilter(sensitive_keys=[test_key])

    # Test query param sanitization
    log_text = f"Request to https://generativelanguage.googleapis.com/v1beta/models?key={test_key}&api_key=token123"
    sanitized = flt.sanitize(log_text)
    assert test_key not in sanitized
    assert "key=[REDACTED]" in sanitized

    # Test header sanitization
    header_text = f"Sending request with x-goog-api-key: {test_key} and Authorization: Bearer secret_jwt_token"
    sanitized_header = flt.sanitize(header_text)
    assert test_key not in sanitized_header
    assert "x-goog-api-key: [REDACTED]" in sanitized_header
    assert "Authorization: Bearer [REDACTED]" in sanitized_header


# --- TASK D: STARTUP SAFETY & NO UNPROMPTED LLM REQUESTS ---

def test_startup_notification_cycle_does_not_trigger_ai_generation(isolated_db, sample_user):
    """Verify run_proactive_notification_cycle evaluates retention and emits notifications without triggering LLM calls."""
    topic = Topic(
        user_id=sample_user.id,
        name="Newton First Law",
        canonical_name="Newton First Law",
        topic_type="concept"
    )
    isolated_db.add(topic)
    isolated_db.commit()

    # Create an overdue memory state with low retention (which previously triggered auto_generate quiz/deck)
    mem = TopicMemoryState(
        user_id=sample_user.id,
        topic_id=topic.id,
        estimated_retention=0.45,
        status="overdue",
        stability=1.0,
        is_muted=False,
        no_need_suppressed=False
    )
    isolated_db.add(mem)
    isolated_db.commit()

    # Mock RAGIntelligenceEngine to assert generate_quiz and generate_flashcards are NOT called
    with patch("backend.ai.generation.RAGIntelligenceEngine.generate_quiz") as mock_quiz:
        with patch("backend.ai.generation.RAGIntelligenceEngine.generate_flashcards") as mock_cards:
            notifs = run_proactive_notification_cycle(isolated_db, sample_user.id)
            assert len(notifs) >= 1
            assert notifs[0].notification_type == "high_forgetting_risk"
            # Crucial assertion: ZERO unprompted LLM calls on startup / notification cycle
            mock_quiz.assert_not_called()
            mock_cards.assert_not_called()


def test_prepare_or_reuse_learning_resources_deferred_when_auto_generate_false(isolated_db, sample_user):
    """Verify prepare_or_reuse_learning_resources returns deferred without calling LLM when auto_generate=False."""
    topic = Topic(
        user_id=sample_user.id,
        name="Thermodynamics Entropy",
        canonical_name="Thermodynamics Entropy",
        topic_type="concept"
    )
    isolated_db.add(topic)
    isolated_db.commit()

    with patch("backend.ai.generation.RAGIntelligenceEngine.generate_quiz") as mock_quiz:
        res = prepare_or_reuse_learning_resources(isolated_db, sample_user.id, topic.id, auto_generate=False)
        assert res["status"] == "deferred"
        assert res["quiz_id"] is None
        assert f"/learn?topic_id={topic.id}" in res["action_url"]
        mock_quiz.assert_not_called()
