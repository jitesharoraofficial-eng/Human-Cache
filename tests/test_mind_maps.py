import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import User, Document, SourceChunk, Topic, TopicRelationship, MindMap
from backend.ai_engine import AITutorEngine

# Re-use existing client and database overrides configured in test_auth_and_isolation
from tests.test_auth_and_isolation import client, TestingSessionLocal
from backend.main import AUTH_RATE_LIMIT_STORE

@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Clear in-memory auth rate limiting table between tests."""
    AUTH_RATE_LIMIT_STORE.clear()

def get_auth_headers_for(email: str, name: str):
    AUTH_RATE_LIMIT_STORE.clear()
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "name": name,
        "password": "Password123!"
    })
    if reg_resp.status_code == 200:
        token = reg_resp.json()["session_token"]
    else:
        login_resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "Password123!"
        })
        token = login_resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}

def test_mind_map_empty_for_new_user():
    """Newly registered users have zero mind maps and no pre-seeded Chemical Bonding maps."""
    headers = get_auth_headers_for("empty_map_user@test.com", "Empty Map User")
    resp = client.get("/api/v1/mind-maps", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_generate_mind_map_fails_when_no_source_content():
    """A user with no uploaded documents or topics cannot generate fabricated mind maps."""
    headers = get_auth_headers_for("no_source_user@test.com", "No Source User")
    resp = client.post(
        "/api/v1/mind-maps/generate",
        json={"central_topic": "Quantum Computing", "detail_level": "semi-detailed"},
        headers=headers
    )
    assert resp.status_code == 400
    assert "Insufficient structured content" in resp.json()["detail"]

def test_generate_grounded_mind_map_with_user_document():
    """When a user has an uploaded document, generated mind maps use real concepts without generic boilerplate."""
    headers = get_auth_headers_for("doc_map_user@test.com", "Doc Map User")
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "doc_map_user@test.com").first()

    # Create user document and chunks
    doc = Document(
        user_id=user.id,
        title="Electrochemical Cells and Redox Reactions",
        filename="electrochem.txt",
        file_type="txt",
        raw_text="Galvanic cells convert chemical energy to electrical energy. The Nernst equation calculates cell potential.",
        processing_status="completed"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunk = SourceChunk(
        document_id=doc.id,
        chunk_index=0,
        content="# Galvanic Cells\nAnode oxidation occurs where electrons are released.\n# Nernst Equation\nElectrode potential depends on temperature and reaction quotient Q.\n# Electrolytic Cells\nNon-spontaneous reactions driven by external voltage.",
        char_count=200
    )
    db.add(chunk)

    topic1 = Topic(
        user_id=user.id,
        name="Galvanic Cells",
        canonical_name="Galvanic Cells",
        description="Electrochemical cell generating voltage from spontaneous redox reactions.",
        topic_type="concept"
    )
    topic2 = Topic(
        user_id=user.id,
        name="Nernst Equation",
        canonical_name="Nernst Equation",
        description="Mathematical equation relating reduction potential to standard potential.",
        topic_type="equation"
    )
    db.add_all([topic1, topic2])
    db.commit()
    db.refresh(topic1)
    db.refresh(topic2)

    rel = TopicRelationship(
        user_id=user.id,
        source_topic_id=topic1.id,
        target_topic_id=topic2.id,
        relationship_type="governs"
    )
    db.add(rel)
    db.commit()
    doc_id = doc.id
    topic1_id = topic1.id
    db.close()

    # Generate grounded map
    resp = client.post(
        "/api/v1/mind-maps/generate",
        json={
            "central_topic": "Galvanic Cells",
            "document_id": doc_id,
            "topic_id": topic1_id,
            "detail_level": "semi-detailed"
        },
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["central_topic"] == "Galvanic Cells"
    assert "structure_json" in data
    nodes = data["structure_json"]["nodes"]
    edges = data["structure_json"]["edges"]

    # Verify no fabricated generic software engineering labels exist
    labels = [n["data"]["label"] for n in nodes]
    assert not any("Workflow Execution" in l for l in labels)
    assert not any("Architecture & Methods" in l for l in labels)
    assert not any("Retention Checkpoints" in l for l in labels)

    # Verify subject concepts exist
    assert any("Galvanic Cells" in l for l in labels)
    assert any("Nernst Equation" in l for l in labels)

    # Verify edge connectivity
    node_ids = {n["id"] for n in nodes}
    for e in edges:
        assert e["source"] in node_ids
        assert e["target"] in node_ids

def test_mind_map_user_isolation():
    """User B cannot generate or access mind maps using User A's document or topic IDs."""
    headers_a = get_auth_headers_for("user_a_map@test.com", "User A")
    headers_b = get_auth_headers_for("user_b_map@test.com", "User B")

    db = TestingSessionLocal()
    user_a = db.query(User).filter(User.email == "user_a_map@test.com").first()

    doc_a = Document(
        user_id=user_a.id,
        title="Secret Thermodynamics Guide",
        filename="thermo.txt",
        file_type="txt",
        raw_text="First law of thermodynamics is energy conservation.",
        processing_status="completed"
    )
    db.add(doc_a)
    db.commit()
    db.refresh(doc_a)
    db.close()

    # User B attempts to generate map using User A's doc_id
    resp = client.post(
        "/api/v1/mind-maps/generate",
        json={"central_topic": "Thermodynamics", "document_id": doc_a.id},
        headers=headers_b
    )
    assert resp.status_code == 404
    assert "not found or does not belong to your account" in resp.json()["detail"]

def test_mind_map_detail_levels():
    """Brief, semi-detailed, and detailed levels produce expanding hierarchies."""
    central = "Cell Biology"
    source = "# Mitochondria\nATP synthesis powerhouse.\n# Ribosomes\nProtein synthesis machinery.\n# Nucleus\nGenetic storage library."

    brief = AITutorEngine.generate_mind_map(central, detail_level="brief", source_text=source)
    semi = AITutorEngine.generate_mind_map(central, detail_level="semi-detailed", source_text=source)
    detailed = AITutorEngine.generate_mind_map(central, detail_level="detailed", source_text=source)

    assert len(brief["nodes"]) < len(semi["nodes"])
    assert len(semi["nodes"]) < len(detailed["nodes"])
