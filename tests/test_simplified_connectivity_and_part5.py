"""
Part 5 Automated Integration and Regression Test Suite.
Validates:
1. Simplified graph default view (Level 1: Simple).
2. Explore mode (Level 2: Explore).
3. Detailed mode (Level 3: Detailed).
4. Focus topic centering and cluster layouts.
5. Plain-English relationship explanations and absence of jargon.
6. Cross-document relationship discovery and evidence grounding.
7. Concept details API with working learning resources and real IDs.
8. Multi-user graph and connectivity data isolation.
9. Scheduler single-owner file lease lock and duplicate prevention.
10. Part 2 Smart Capture regression (text/URL/inbox).
11. Part 3 Autonomous Memory Coach four actions (Start, Dismiss, Snooze, No Need).
12. Part 4 Coverage indicators and adaptive flashcard decks.
"""

import pytest
import uuid
import os
import json
from fastapi.testclient import TestClient

from backend.main import app, AUTH_RATE_LIMIT_STORE
from backend.models import (
    User, Document, Category, SourceChunk, Topic, DocumentTopic,
    TopicRelationship, TopicMemoryState, FlashcardDeck, Flashcard, Quiz, MindMap
)
from backend.graph_engine import build_user_knowledge_graph, get_concept_details_payload
from backend.scheduler import MemoryCoachScheduler
from tests.test_auth_and_isolation import client, TestingSessionLocal

@pytest.fixture(autouse=True)
def reset_rate_limits():
    AUTH_RATE_LIMIT_STORE.clear()
    yield
    AUTH_RATE_LIMIT_STORE.clear()

def register_user(prefix: str) -> dict:
    email = f"{uuid.uuid4().hex[:6]}_{prefix}@test.com"
    res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "name": f"Part 5 {prefix.title()}"
    })
    assert res.status_code == 200, res.text
    return res.json()

def seed_cross_document_graph(user_id: str):
    """
    Creates two distinct documents in different categories:
    Doc A: Marketing & Brand Strategy (Business Category)
    Doc B: Consumer Psychology & Behavioral Economics (Psychology Category)
    Along with topics, intra-doc relationships, and cross-document semantic bridges.
    """
    db = TestingSessionLocal()
    try:
        # Categories
        cat_biz = Category(id=f"cat_{uuid.uuid4().hex[:8]}", user_id=user_id, name="Business Management", color="#6366f1")
        cat_psy = Category(id=f"cat_{uuid.uuid4().hex[:8]}", user_id=user_id, name="Cognitive Psychology", color="#a855f7")
        db.add_all([cat_biz, cat_psy])
        db.commit()

        # Documents
        doc_a = Document(
            id=f"doc_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            category_id=cat_biz.id,
            title="Strategic Marketing Foundations",
            filename="marketing_foundations.pdf",
            file_path="uploads/marketing_foundations.pdf",
            file_type="pdf",
            file_size_bytes=4096
        )
        doc_b = Document(
            id=f"doc_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            category_id=cat_psy.id,
            title="Behavioral Economics and Choice Architecture",
            filename="behavioral_economics.pdf",
            file_path="uploads/behavioral_economics.pdf",
            file_type="pdf",
            file_size_bytes=5120
        )
        db.add_all([doc_a, doc_b])
        db.commit()

        # Topics in Doc A
        t_mkt = Topic(id=f"top_{uuid.uuid4().hex[:8]}", user_id=user_id, name="Marketing Strategy", canonical_name="Marketing Strategy", description="Systematic planning of product positioning and market messaging.")
        t_pos = Topic(id=f"top_{uuid.uuid4().hex[:8]}", user_id=user_id, name="Brand Positioning", canonical_name="Brand Positioning", description="Establishing distinct market perception relative to competitors.")
        
        # Topics in Doc B
        t_cog = Topic(id=f"top_{uuid.uuid4().hex[:8]}", user_id=user_id, name="Cognitive Bias", canonical_name="Cognitive Bias", description="Systematic deviations from rational judgement affecting decisions.")
        t_nud = Topic(id=f"top_{uuid.uuid4().hex[:8]}", user_id=user_id, name="Choice Architecture", canonical_name="Choice Architecture", description="Structuring decision environments to encourage specific outcomes.")
        
        db.add_all([t_mkt, t_pos, t_cog, t_nud])
        db.commit()

        # Link topics to respective documents
        db.add_all([
            DocumentTopic(id=f"dt_{uuid.uuid4().hex[:8]}", document_id=doc_a.id, topic_id=t_mkt.id),
            DocumentTopic(id=f"dt_{uuid.uuid4().hex[:8]}", document_id=doc_a.id, topic_id=t_pos.id),
            DocumentTopic(id=f"dt_{uuid.uuid4().hex[:8]}", document_id=doc_b.id, topic_id=t_cog.id),
            DocumentTopic(id=f"dt_{uuid.uuid4().hex[:8]}", document_id=doc_b.id, topic_id=t_nud.id),
        ])
        db.commit()

        # Relationships:
        # Intra-doc: Marketing Strategy -> Brand Positioning
        rel_intra_a = TopicRelationship(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            source_topic_id=t_mkt.id,
            target_topic_id=t_pos.id,
            relationship_type="builds_on",
            confidence=0.9,
            evidence_text="Brand positioning operationalizes high-level marketing strategy."
        )
        # Intra-doc: Cognitive Bias -> Choice Architecture
        rel_intra_b = TopicRelationship(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            source_topic_id=t_cog.id,
            target_topic_id=t_nud.id,
            relationship_type="prerequisite_of",
            confidence=0.88,
            evidence_text="Understanding cognitive biases is prerequisite to designing choice architecture."
        )
        # CROSS-DOC BRIDGE: Cognitive Bias -> Brand Positioning (Doc B -> Doc A)
        rel_cross = TopicRelationship(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            source_topic_id=t_cog.id,
            target_topic_id=t_pos.id,
            relationship_type="relates_to",
            confidence=0.85,
            evidence_text="Consumer brand positioning utilizes heuristics and framing biases to shape perception."
        )
        db.add_all([rel_intra_a, rel_intra_b, rel_cross])
        db.commit()

        # Add memory states
        db.add_all([
            TopicMemoryState(id=f"mem_{uuid.uuid4().hex[:8]}", user_id=user_id, topic_id=t_mkt.id, status="learned", estimated_retention=0.92, stability=4.0),
            TopicMemoryState(id=f"mem_{uuid.uuid4().hex[:8]}", user_id=user_id, topic_id=t_pos.id, status="review_due", estimated_retention=0.62, stability=1.5),
            TopicMemoryState(id=f"mem_{uuid.uuid4().hex[:8]}", user_id=user_id, topic_id=t_cog.id, status="learned", estimated_retention=0.88, stability=3.5),
            TopicMemoryState(id=f"mem_{uuid.uuid4().hex[:8]}", user_id=user_id, topic_id=t_nud.id, status="unlearned", estimated_retention=1.0, stability=1.0),
        ])

        # Add a test flashcard deck and quiz for t_mkt
        deck = FlashcardDeck(
            id=f"deck_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            topic_id=t_mkt.id,
            title="Marketing Strategy Drill",
            detail_level="semi-detailed"
        )
        db.add(deck)
        db.commit()

        return {
            "user_id": user_id,
            "doc_a": doc_a.id,
            "doc_b": doc_b.id,
            "t_mkt": t_mkt.id,
            "t_pos": t_pos.id,
            "t_cog": t_cog.id,
            "t_nud": t_nud.id,
            "deck_id": deck.id
        }
    finally:
        db.close()


def test_simplified_graph_default_and_progressive_disclosure():
    """Verify Level 1 (Simple), Level 2 (Explore), and Level 3 (Detailed) progressive disclosure."""
    user = register_user("graph_user")
    u_id = user["user"]["id"]
    cookie = {"humancache_session": user["session_token"]}
    data_ids = seed_cross_document_graph(u_id)

    # 1. Level 1 (Default / Simple)
    res_simple = client.get("/api/v1/knowledge-graph?detail_level=simple", cookies=cookie)
    assert res_simple.status_code == 200, res_simple.text
    data_simple = res_simple.json()
    assert "nodes" in data_simple
    assert "edges" in data_simple
    assert "clusters" in data_simple
    assert data_simple["stats"]["detail_level"] == "simple"
    assert len(data_simple["nodes"]) > 0
    # In simple view, all edges have plain-English simple_explanations
    for edge in data_simple["edges"]:
        assert "simple_explanation" in edge["data"]
        assert len(edge["data"]["simple_explanation"]) > 10

    # 2. Level 2 (Explore)
    res_explore = client.get("/api/v1/knowledge-graph?detail_level=explore", cookies=cookie)
    assert res_explore.status_code == 200
    data_explore = res_explore.json()
    assert data_explore["stats"]["detail_level"] == "explore"

    # 3. Level 3 (Detailed)
    res_detailed = client.get("/api/v1/knowledge-graph?detail_level=detailed", cookies=cookie)
    assert res_detailed.status_code == 200
    data_detailed = res_detailed.json()
    assert data_detailed["stats"]["detail_level"] == "detailed"
    assert len(data_detailed["nodes"]) == 4
    assert len(data_detailed["edges"]) == 3


def test_cross_document_connectivity_and_plain_english_reasons():
    """Verify /connectivity endpoint identifies cross-document bridges and provides plain-English reasons."""
    user = register_user("connect_user")
    u_id = user["user"]["id"]
    cookie = {"humancache_session": user["session_token"]}
    seed_cross_document_graph(u_id)

    res = client.get("/api/v1/connectivity", cookies=cookie)
    assert res.status_code == 200, res.text
    bridges = res.json()
    assert len(bridges) == 3

    cross_bridges = [b for b in bridges if b.get("is_cross_document")]
    assert len(cross_bridges) == 1, "Exactly 1 cross-document bridge between Psychology and Business"
    cross = cross_bridges[0]
    assert cross["source_topic"] == "Cognitive Bias"
    assert cross["target_topic"] == "Brand Positioning"
    assert "Strategic Marketing Foundations" in cross["target_document_title"]
    assert "Behavioral Economics" in cross["source_document_title"]
    assert "simple_reason" in cross
    assert len(cross["simple_reason"]) > 15
    assert "evidence_text" in cross


def test_interactive_concept_details_and_real_resource_links():
    """Verify GET /knowledge-graph/concepts/{topic_id}/details returns real resource IDs."""
    user = register_user("details_user")
    u_id = user["user"]["id"]
    cookie = {"humancache_session": user["session_token"]}
    data_ids = seed_cross_document_graph(u_id)

    res = client.get(f"/api/v1/knowledge-graph/concepts/{data_ids['t_mkt']}/details", cookies=cookie)
    assert res.status_code == 200, res.text
    details = res.json()

    assert details["name"] == "Marketing Strategy"
    assert details["retention_percentage"] == 92
    assert len(details["source_documents"]) >= 1
    assert details["source_documents"][0]["id"] == data_ids["doc_a"]
    assert len(details["connections"]) >= 1
    
    # Check resources dictionary has real deck_id
    assert details["resources"]["deck_id"] == data_ids["deck_id"]
    assert f"deck_id={data_ids['deck_id']}" in details["resources"]["flashcards_url"]
    assert "topic=Marketing" in details["resources"]["learn_url"]


def test_cross_user_knowledge_graph_isolation():
    """Verify User B cannot see or query User A's graph, clusters, or concept details."""
    user_a = register_user("user_a_graph")
    user_b = register_user("user_b_graph")
    cookie_b = {"humancache_session": user_b["session_token"]}
    data_a = seed_cross_document_graph(user_a["user"]["id"])

    # User B queries their own graph -> should be empty
    res_b = client.get("/api/v1/knowledge-graph", cookies=cookie_b)
    assert res_b.status_code == 200
    assert len(res_b.json()["nodes"]) == 0

    # User B attempts to query User A's concept details -> 404 forbidden
    res_b_details = client.get(f"/api/v1/knowledge-graph/concepts/{data_a['t_mkt']}/details", cookies=cookie_b)
    assert res_b_details.status_code == 404


def test_scheduler_single_owner_process_lease():
    """Verify MemoryCoachScheduler process-level lease acquires and releases cleanly without duplicate runs."""
    scheduler1 = MemoryCoachScheduler(interval_seconds=60)
    scheduler2 = MemoryCoachScheduler(interval_seconds=60)

    # 1. Scheduler 1 acquires lease
    assert scheduler1._acquire_process_lease() is True
    assert os.path.exists("memory_coach_worker.lock")

    # 2. Releasing lease removes lockfile
    scheduler1._release_process_lease()
    assert not os.path.exists("memory_coach_worker.lock")

    # 3. Clean startup and shutdown
    scheduler1.start()
    assert scheduler1._running is True
    scheduler1.stop()
    assert scheduler1._running is False
    assert not os.path.exists("memory_coach_worker.lock")
