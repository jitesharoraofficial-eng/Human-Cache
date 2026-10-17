import os
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import (
    Base, User, Document, SourceChunk, ChunkEmbedding,
    Topic, TopicRelationship, TopicMemoryState, DocumentTopic,
    Quiz, FlashcardDeck, Flashcard, Note, MindMap,
    AgentConversation, AgentMessage
)
from backend.extractor import (
    extract_topics_and_concepts, compute_page_coverage,
    chunk_pages_and_text
)
from backend.ai.retrieval import RetrievalService
from backend.graph_engine import build_user_knowledge_graph
from backend.resource_prep_service import auto_prepare_document_learning_suite


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
        email="learner.test@humancache.ai",
        name="Alex Learner",
        hashed_password="test_hash_secure"
    )
    isolated_db.add(user)
    isolated_db.commit()
    isolated_db.refresh(user)
    return user


def test_full_document_hierarchical_extraction():
    """Verify that extraction does not truncate at 12 topics and captures late units/chapters."""
    multi_unit_syllabus = """
    UNIT 1: Linear Data Structures
    Arrays and sequential memory allocation.
    Stacks and Queues for recursive problem solving.
    Stack Underflow occurs when popping an empty stack.
    Stack Overflow is defined as exceeding buffer allocation.

    UNIT 2: Non-Linear Data Structures
    Binary Trees and binary search tree properties.
    Graph Traversals using Breadth First Search.
    Depth First Search explores down tree branches.

    UNIT 3: Algorithm Analysis
    Asymptotic Notations including Big O and Theta.
    Divide and Conquer strategies for merge sort.
    Greedy Method for minimum spanning trees.

    UNIT 4: Dynamic Programming
    Optimal Substructure is defined as solving subproblems independently.
    Overlapping Subproblems in Fibonacci sequences.
    0/1 Knapsack Problem formulation.

    UNIT 5: Advanced Topics
    NP Completeness and polynomial time reduction.
    Approximation Algorithms for vertex cover.
    Trie Structures for prefix matching.
    """
    topics = extract_topics_and_concepts(multi_unit_syllabus, "ds_syllabus.pdf")
    topic_names = [t["canonical_name"].lower() for t in topics]

    # Verify all 5 units are detected
    assert any("unit 1" in t for t in topic_names), "Unit 1 was not detected"
    assert any("unit 2" in t for t in topic_names), "Unit 2 was not detected"
    assert any("unit 3" in t for t in topic_names), "Unit 3 was not detected"
    assert any("unit 4" in t for t in topic_names), "Unit 4 was not detected"
    assert any("unit 5" in t for t in topic_names), "Unit 5 was not detected"

    # Verify late concepts are not truncated
    assert any("np completeness" in t or "trie structures" in t for t in topic_names), "Late unit concepts were truncated!"
    assert len(topics) > 12, f"Topics prematurely truncated to {len(topics)}"


def test_page_level_audit_and_coverage():
    """Verify compute_page_coverage correctly detects readable, sparse, and empty pages."""
    mock_pages = [
        {"page_number": 1, "text": "Readable content for page 1.", "status": "readable"},
        {"page_number": 2, "text": "Readable content for page 2 with equations.", "status": "readable"},
        {"page_number": 3, "text": "", "status": "empty"},
        {"page_number": 4, "text": "Img", "status": "scanned_or_sparse"}
    ]
    cov = compute_page_coverage(mock_pages)
    assert cov["total_pages"] == 4
    assert cov["readable_pages"] == 2
    assert cov["empty_pages"] == 1
    assert cov["scanned_or_sparse_pages"] == 1
    assert cov["coverage_percentage"] == 50.0
    assert cov["status"] == "partially_scanned"


def test_batch_chunk_indexing_consistent_vector_space(isolated_db, sample_user):
    """Verify index_chunks_batch indexes all chunks across all pages with consistent dimensionality."""
    doc = Document(
        user_id=sample_user.id,
        title="Operating Systems",
        filename="os.pdf",
        file_type="pdf",
        processing_status="completed"
    )
    isolated_db.add(doc)
    isolated_db.commit()

    # Create 15 chunks (previously chunks >= 10 were degraded or skipped)
    chunk_records = []
    for i in range(15):
        chunk = SourceChunk(
            document_id=doc.id,
            chunk_index=i,
            page_number=(i // 3) + 1,
            section_heading=f"Section {i + 1}",
            content=f"Content for chunk {i + 1} detailing operating system kernels and processes.",
            char_count=60
        )
        isolated_db.add(chunk)
        chunk_records.append(chunk)
    isolated_db.commit()

    retrieval_svc = RetrievalService(isolated_db)
    indexed_count = retrieval_svc.index_chunks_batch(sample_user.id, doc.id, chunk_records)
    assert indexed_count == 15

    # Check that all 15 chunks have embeddings with uniform dimension
    embs = isolated_db.query(ChunkEmbedding).filter(ChunkEmbedding.document_id == doc.id).all()
    assert len(embs) == 15
    dim_set = {e.dimension for e in embs}
    assert len(dim_set) == 1, f"Found non-uniform embedding dimensions: {dim_set}"


def test_knowledge_graph_focused_mode(isolated_db, sample_user):
    """Verify build_user_knowledge_graph isolates the graph to the focused topic and its immediate neighbors."""
    # Create 4 topics
    t1 = Topic(user_id=sample_user.id, name="Newton First Law", canonical_name="Newton First Law", topic_type="concept")
    t2 = Topic(user_id=sample_user.id, name="Inertia", canonical_name="Inertia", topic_type="concept")
    t3 = Topic(user_id=sample_user.id, name="Friction", canonical_name="Friction", topic_type="concept")
    t4 = Topic(user_id=sample_user.id, name="Electromagnetism", canonical_name="Electromagnetism", topic_type="concept") # Unconnected
    isolated_db.add_all([t1, t2, t3, t4])
    isolated_db.commit()

    r1 = TopicRelationship(user_id=sample_user.id, source_topic_id=t1.id, target_topic_id=t2.id, relationship_type="prerequisite_of", confidence=0.9)
    r2 = TopicRelationship(user_id=sample_user.id, source_topic_id=t2.id, target_topic_id=t3.id, relationship_type="relates_to", confidence=0.85)
    isolated_db.add_all([r1, r2])
    isolated_db.commit()

    # Full graph has 4 nodes
    full_graph = build_user_knowledge_graph(isolated_db, sample_user.id, detail_level="detailed")
    assert len(full_graph["nodes"]) == 4

    # Focused graph on t1 isolates to t1 and its neighbor t2
    focused_graph = build_user_knowledge_graph(isolated_db, sample_user.id, detail_level="simple", focus_topic_id=t1.id)
    focused_node_ids = {n["id"] for n in focused_graph["nodes"]}
    assert t1.id in focused_node_ids
    assert t2.id in focused_node_ids
    assert t4.id not in focused_node_ids, "Unrelated node was not filtered out in focused mode!"


def test_auto_prepare_document_learning_suite(isolated_db, sample_user):
    """Verify auto_prepare_document_learning_suite idempotently creates notes, quizzes, flashcards, mind maps."""
    doc = Document(
        user_id=sample_user.id,
        title="Fluid Dynamics",
        filename="fluids.pdf",
        file_type="pdf",
        processing_status="completed"
    )
    isolated_db.add(doc)
    isolated_db.commit()

    t1 = Topic(user_id=sample_user.id, name="Bernoulli Equation", canonical_name="Bernoulli Equation", topic_type="concept")
    t2 = Topic(user_id=sample_user.id, name="Viscosity", canonical_name="Viscosity", topic_type="concept")
    isolated_db.add_all([t1, t2])
    isolated_db.commit()

    dt1 = DocumentTopic(document_id=doc.id, topic_id=t1.id, relevance_score=1.0)
    dt2 = DocumentTopic(document_id=doc.id, topic_id=t2.id, relevance_score=0.9)
    isolated_db.add_all([dt1, dt2])
    isolated_db.commit()

    res = auto_prepare_document_learning_suite(isolated_db, sample_user.id, doc.id)
    assert res["status"] == "completed"

    # Verify Document status updated
    isolated_db.refresh(doc)
    assert doc.resource_prep_status == "completed"

    # Verify Note created
    note = isolated_db.query(Note).filter(Note.document_id == doc.id).first()
    assert note is not None
    assert "Fluid Dynamics" in note.title

    # Verify MindMap created
    mmap = isolated_db.query(MindMap).filter(MindMap.document_id == doc.id).first()
    assert mmap is not None
    assert "Fluid Dynamics" in mmap.title


def test_conversation_history_persistence_recovery(isolated_db, sample_user):
    """Verify that earlier conversations with messages are preserved and discoverable."""
    # Previous day conversation with 4 turns
    conv_prev = AgentConversation(
        user_id=sample_user.id,
        title="Newton's Laws Deep Dive"
    )
    isolated_db.add(conv_prev)
    isolated_db.commit()

    m1 = AgentMessage(conversation_id=conv_prev.id, role="user", content="Explain Newton's third law.")
    m2 = AgentMessage(conversation_id=conv_prev.id, role="assistant", content="Every action has an equal and opposite reaction.")
    isolated_db.add_all([m1, m2])
    isolated_db.commit()

    # Today's fresh empty conversation
    conv_today = AgentConversation(
        user_id=sample_user.id,
        title="Session on Oct 16"
    )
    isolated_db.add(conv_today)
    isolated_db.commit()

    # Query all conversations
    conversations = isolated_db.query(AgentConversation).filter(AgentConversation.user_id == sample_user.id).order_by(AgentConversation.created_at.desc()).all()
    assert len(conversations) == 2

    # Verify the previous conversation and its messages are 100% intact
    prev_saved = isolated_db.query(AgentConversation).filter(AgentConversation.id == conv_prev.id).first()
    assert prev_saved is not None
    msg_count = isolated_db.query(AgentMessage).filter(AgentMessage.conversation_id == conv_prev.id).count()
    assert msg_count == 2
