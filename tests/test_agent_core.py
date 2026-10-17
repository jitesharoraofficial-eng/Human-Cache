import pytest
import uuid
from fastapi.testclient import TestClient

from backend.models import Topic, Document, SourceChunk, TopicMemoryState, AgentConversation, AgentMessage
from tests.test_auth_and_isolation import client, TestingSessionLocal


def register_user(client: TestClient, prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@humancache.ai"
    res = client.post(
        "/api/v1/auth/register",
        json={"name": f"User {prefix}", "email": email, "password": "Password123!"}
    )
    assert res.status_code == 200, res.text
    return res.json()["user"]


def test_conversation_thread_lifecycle():
    """
    Creates a thread, posts user message, gets assistant reply,
    re-fetches conversation to verify multi-turn persistence across requests.
    """
    user = register_user(client, "lifecycle")

    # 1. Create thread
    conv_res = client.post("/api/v1/agent/conversations", json={"title": "Thermodynamics Revision"})
    assert conv_res.status_code == 200, conv_res.text
    conv_data = conv_res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Thermodynamics Revision"
    assert conv_data["message_count"] == 0

    # 2. Post first user message
    msg1_res = client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "Can you explain the First Law of Thermodynamics?"}
    )
    assert msg1_res.status_code == 200, msg1_res.text
    msg1_data = msg1_res.json()
    assert msg1_data["role"] == "assistant"
    assert len(msg1_data["content"]) > 10
    assert "citations" in msg1_data

    # 3. Post follow-up in the same conversation thread
    msg2_res = client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "How does this apply to an adiabatic process?"}
    )
    assert msg2_res.status_code == 200, msg2_res.text
    msg2_data = msg2_res.json()
    assert msg2_data["role"] == "assistant"

    # 4. Fetch the entire thread
    fetch_res = client.get(f"/api/v1/agent/conversations/{conv_id}")
    assert fetch_res.status_code == 200, fetch_res.text
    thread = fetch_res.json()
    assert thread["id"] == conv_id
    assert thread["message_count"] == 4  # 2 user turns + 2 assistant turns
    roles = [m["role"] for m in thread["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_cross_user_conversation_isolation():
    """
    Ensure User B cannot access, read, or post messages to User A's conversation.
    """
    user_a = register_user(client, "user_a")
    conv_a = client.post("/api/v1/agent/conversations", json={"title": "User A Private Study"}).json()
    conv_id = conv_a["id"]

    # Register and switch to User B
    user_b = register_user(client, "user_b")

    # User B attempts to read User A's thread -> 404
    read_attempt = client.get(f"/api/v1/agent/conversations/{conv_id}")
    assert read_attempt.status_code == 404

    # User B attempts to post message to User A's thread -> 404
    post_attempt = client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "Malicious message injection"}
    )
    assert post_attempt.status_code == 404

    # User B attempts to delete User A's thread -> 404
    del_attempt = client.delete(f"/api/v1/agent/conversations/{conv_id}")
    assert del_attempt.status_code == 404


def test_conversation_rename_archive_and_delete():
    """
    Verify renaming, archiving, and deletion with cascading message cleanup.
    """
    user = register_user(client, "mgmt")
    conv = client.post("/api/v1/agent/conversations", json={"title": "Draft Topic"}).json()
    conv_id = conv["id"]

    # Send a message
    client.post(f"/api/v1/agent/conversations/{conv_id}/messages", json={"content": "Hello"})

    # Rename and archive
    patch_res = client.patch(
        f"/api/v1/agent/conversations/{conv_id}",
        json={"title": "Mastered Topic", "is_archived": True}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Mastered Topic"
    assert patch_res.json()["is_archived"] is True

    # Delete conversation
    del_res = client.delete(f"/api/v1/agent/conversations/{conv_id}")
    assert del_res.status_code == 200

    # Ensure conversation no longer exists
    assert client.get(f"/api/v1/agent/conversations/{conv_id}").status_code == 404

    # Ensure messages were cascade deleted from database
    db = TestingSessionLocal()
    try:
        orphaned = db.query(AgentMessage).filter(AgentMessage.conversation_id == conv_id).all()
        assert len(orphaned) == 0
    finally:
        db.close()


def test_hinglish_and_multilingual_context():
    """
    Ensure Hinglish queries ('Mujhe Carnot engine samjhao') are handled gracefully.
    """
    user = register_user(client, "hinglish")
    conv = client.post("/api/v1/agent/conversations").json()

    res = client.post(
        f"/api/v1/agent/conversations/{conv['id']}/messages",
        json={"content": "Mujhe Carnot cycle aur uski efficiency explain karo", "language": "hinglish"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "assistant"
    assert len(data["content"]) > 20
    assert data["meta"]["language"] == "hinglish"


def test_rag_provenance_citations():
    """
    Verify that when documents match, source_type is 'uploaded_document',
    and when no documents match, source_type is 'general_knowledge'.
    """
    user = register_user(client, "rag_cite")
    db = TestingSessionLocal()
    try:
        # Create an uploaded document for user
        doc = Document(
            user_id=user["id"],
            title="Fluid Dynamics Handout",
            filename="fluids.pdf",
            file_type="pdf",
            file_path="/storage/test/fluids.pdf",
            processing_status="completed"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        chunk = SourceChunk(
            document_id=doc.id,
            chunk_index=0,
            page_number=3,
            section_heading="Bernoulli Principle",
            content="Bernoulli's principle states that an increase in the speed of a fluid occurs simultaneously with a decrease in pressure.",
            char_count=120
        )
        db.add(chunk)
        db.commit()

        # Index chunk into retrieval service
        from backend.ai.retrieval import RetrievalService
        retrieval = RetrievalService(db)
        retrieval.index_chunk(user["id"], doc.id, chunk.id, chunk.content, force_local=True)

        # 1. Query matching uploaded note
        conv = client.post("/api/v1/agent/conversations").json()
        match_res = client.post(
            f"/api/v1/agent/conversations/{conv['id']}/messages",
            json={"content": "What is Bernoulli's principle from my notes?"}
        )
        assert match_res.status_code == 200
        citations = match_res.json()["citations"]
        assert len(citations) > 0
        assert citations[0]["source_type"] == "uploaded_document"
        assert "Fluid Dynamics" in citations[0]["title"] or "fluids.pdf" in citations[0]["title"]

        # 2. Query unrelated concept with no matching documents
        no_match_res = client.post(
            f"/api/v1/agent/conversations/{conv['id']}/messages",
            json={"content": "Explain Renaissance art history in 15th century Florence"}
        )
        assert no_match_res.status_code == 200
        no_match_cites = no_match_res.json()["citations"]
        assert any(c["source_type"] == "general_knowledge" for c in no_match_cites)
    finally:
        db.close()


def test_tool_registry_inspection_and_execution():
    """
    Verify tool registry lists available tools and executes safe tools correctly.
    """
    user = register_user(client, "tools_tester")

    # 1. List tools endpoint
    tools_res = client.get("/api/v1/agent/tools")
    assert tools_res.status_code == 200
    tools = tools_res.json()
    tool_names = [t["name"] for t in tools]
    assert "retrieve_knowledge_chunks" in tool_names
    assert "generate_practice_quiz" in tool_names
    assert "generate_adaptive_flashcards" in tool_names
    assert "generate_mind_map" in tool_names
    assert "query_learner_retention" in tool_names
    assert "modify_study_schedule" in tool_names
    assert "delete_document" in tool_names

    # 2. Execute query_learner_retention
    exec_res = client.post(
        "/api/v1/agent/tools/query_learner_retention/execute",
        json={"arguments": {}}
    )
    assert exec_res.status_code == 200
    res_data = exec_res.json()
    assert res_data["success"] is True
    assert "retention_data" in res_data["result"]


def test_tool_registry_invalid_arguments_rejection():
    """
    Verify Pydantic input schema rejects invalid or out-of-range tool arguments.
    """
    register_user(client, "tool_val")

    # question_count must be between 1 and 10
    res = client.post(
        "/api/v1/agent/tools/generate_practice_quiz/execute",
        json={"arguments": {"question_count": 999}}
    )
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "Invalid arguments" in res.json()["error"]


def test_consequential_tool_safeguard():
    """
    Verify consequential tools (delete_document, modify_study_schedule) require explicit confirmation.
    """
    register_user(client, "consequential")

    # Attempt delete without confirmation
    res = client.post(
        "/api/v1/agent/tools/delete_document/execute",
        json={"arguments": {"document_id": "doc-123"}, "confirmed": False}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["requires_confirmation"] is True
    assert "requires your explicit confirmation" in data["confirmation_prompt"]


def test_tutor_chat_backward_compatibility():
    """
    Verify existing POST /api/v1/tutor/chat continues to work seamlessly.
    """
    register_user(client, "legacy_tutor")

    res = client.post(
        "/api/v1/tutor/chat",
        json={
            "message": "Quick recap of thermodynamics",
            "conversation_history": []
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "citations" in data
    assert "is_grounded" in data
