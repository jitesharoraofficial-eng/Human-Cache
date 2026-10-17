import math
import networkx as nx
from typing import List, Dict, Any, Tuple, Optional, Set
from sqlalchemy.orm import Session
from backend.models import Topic, TopicRelationship, TopicMemoryState, DocumentTopic, Document, Category, Quiz, FlashcardDeck, MindMap

def build_user_knowledge_graph(
    db: Session,
    user_id: str,
    detail_level: str = "brief",
    focus_topic_id: Optional[str] = None,
    category_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs a NetworkX graph from database topics & relationships with progressive disclosure:
    - 'brief' / 'simple' (Default Level 1): Primary cluster hubs, highest-yield relationships, plain-English explanations.
    - 'semi-detailed' / 'explore' (Level 2): Key concepts, immediate subtopics, cross-document connections, prerequisites.
    - 'detailed' (Level 3): Full topology, exhaustive edges, evidence texts, and centrality/density statistics.
    
    Includes cluster grouping, cross-document badges, simple relationship explanations, and deep-link availability.
    """
    # Normalize level aliases
    norm_level = "simple" if detail_level in ["simple", "brief"] else ("explore" if detail_level in ["explore", "semi-detailed"] else "detailed")

    # 1. Fetch user topics and relationships
    topic_query = db.query(Topic).filter(Topic.user_id == user_id)
    topics = topic_query.all()
    if not topics:
        return {
            "nodes": [],
            "edges": [],
            "clusters": [],
            "stats": {"total_nodes": 0, "total_edges": 0, "detail_level": norm_level}
        }

    # Map topics to their documents and categories for cross-document analysis
    doc_assocs = db.query(DocumentTopic).filter(DocumentTopic.topic_id.in_([t.id for t in topics])).all() if topics else []
    topic_doc_ids: Dict[str, Set[str]] = {}
    for da in doc_assocs:
        topic_doc_ids.setdefault(da.topic_id, set()).add(da.document_id)

    # Document details lookup
    user_docs = {d.id: d for d in db.query(Document).filter(Document.user_id == user_id).all()}
    categories = {c.id: c.name for c in db.query(Category).filter(Category.user_id == user_id).all()}

    # Category filter if specified
    if category_id:
        allowed_doc_ids = {d_id for d_id, d in user_docs.items() if d.category_id == category_id}
        topics = [t for t in topics if any(d_id in allowed_doc_ids for d_id in topic_doc_ids.get(t.id, set()))]

    relationships = db.query(TopicRelationship).filter(TopicRelationship.user_id == user_id).all()
    memory_states = {
        ms.topic_id: ms 
        for ms in db.query(TopicMemoryState).filter(TopicMemoryState.user_id == user_id).all()
    }

    # 2. Build complete NetworkX DiGraph
    G = nx.DiGraph()
    for t in topics:
        mem = memory_states.get(t.id)
        status = mem.status if mem else "unlearned"
        retention = mem.estimated_retention if mem else 1.0
        stability = mem.stability if mem else 1.0

        # Primary document & category name for node
        doc_ids = topic_doc_ids.get(t.id, set())
        primary_doc = user_docs.get(next(iter(doc_ids))) if doc_ids else None
        doc_title = primary_doc.title if primary_doc else "Independent Note"
        cat_name = categories.get(primary_doc.category_id, "General") if (primary_doc and primary_doc.category_id) else "General"

        G.add_node(
            t.id,
            id=t.id,
            name=t.name,
            canonical_name=t.canonical_name,
            description=t.description or f"Core concept in {cat_name}.",
            topic_type=t.topic_type or "concept",
            status=status,
            retention=retention,
            stability=stability,
            category_name=cat_name,
            document_title=doc_title,
            doc_ids=list(doc_ids),
            is_demo=t.is_demo
        )

    for r in relationships:
        if G.has_node(r.source_topic_id) and G.has_node(r.target_topic_id):
            s_docs = topic_doc_ids.get(r.source_topic_id, set())
            t_docs = topic_doc_ids.get(r.target_topic_id, set())
            is_cross_doc = bool(s_docs and t_docs and s_docs.isdisjoint(t_docs))

            G.add_edge(
                r.source_topic_id,
                r.target_topic_id,
                id=r.id,
                relationship_type=r.relationship_type or "relates_to",
                confidence=r.confidence or 0.8,
                evidence=r.evidence_text or "",
                is_cross_document=is_cross_doc
            )

    # 3. Compute network metrics
    degrees = dict(G.degree())
    try:
        centrality = nx.degree_centrality(G) if len(G) > 1 else {n: 1.0 for n in G.nodes()}
    except Exception:
        centrality = {n: 0.5 for n in G.nodes()}

    # Group topics into clusters by Category or connected components
    clusters_map: Dict[str, List[str]] = {}
    for n_id, data in G.nodes(data=True):
        c_name = data.get("category_name", "General")
        clusters_map.setdefault(c_name, []).append(n_id)

    # 4. Progressive Disclosure Selection
    all_node_ids = set(G.nodes())
    if focus_topic_id and focus_topic_id in all_node_ids:
        # Focus mode: center on focused topic and its neighbors (up to 2 hops for explore/detailed)
        focused_set = {focus_topic_id}
        focused_set.update(G.predecessors(focus_topic_id))
        focused_set.update(G.successors(focus_topic_id))
        if norm_level == "detailed":
            for nbr in list(focused_set):
                focused_set.update(G.predecessors(nbr))
                focused_set.update(G.successors(nbr))
        selected_node_ids = focused_set
    elif norm_level == "simple":
        # Level 1: Limit to primary hubs (high centrality) + highest confidence connections
        if len(all_node_ids) > 6:
            sorted_by_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            # Pick top 5-7 concepts ensuring major clusters are represented
            selected_node_ids = set()
            for c_name, members in clusters_map.items():
                if members:
                    # Pick highest centrality in cluster
                    best_in_cluster = max(members, key=lambda m: centrality.get(m, 0.0))
                    selected_node_ids.add(best_in_cluster)
            # Fill up to max 7 nodes
            for n_id, _ in sorted_by_centrality:
                if len(selected_node_ids) >= 7:
                    break
                selected_node_ids.add(n_id)
        else:
            selected_node_ids = all_node_ids
    elif norm_level == "explore":
        # Level 2: Include main concepts plus subtopics and direct bridges (up to 12 nodes)
        if len(all_node_ids) > 12:
            sorted_by_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            top_hubs = [n_id for n_id, _ in sorted_by_centrality[:6]]
            selected_node_ids = set(top_hubs)
            for hub in top_hubs:
                selected_node_ids.update(list(G.successors(hub))[:2])
                selected_node_ids.update(list(G.predecessors(hub))[:2])
            # Cap at 14 to maintain clean explore view
            if len(selected_node_ids) > 14:
                selected_node_ids = set(sorted(list(selected_node_ids), key=lambda x: centrality.get(x, 0.0), reverse=True)[:14])
        else:
            selected_node_ids = all_node_ids
    else:
        # Level 3 (Detailed): Full topology
        selected_node_ids = all_node_ids

    # 5. Position Layout (Deterministic Clustered Layout)
    # Positions nodes by cluster to avoid overlapping cards and excessive edge crossings
    active_nodes = [(n_id, G.nodes[n_id]) for n_id in selected_node_ids]
    cluster_names = sorted(list({data.get("category_name", "General") for _, data in active_nodes}))
    cluster_centers: Dict[str, Tuple[float, float]] = {}
    
    num_clusters = len(cluster_names)
    cluster_orbit_radius = max(280.0, num_clusters * 130.0)
    for c_idx, c_name in enumerate(cluster_names):
        c_angle = (2 * math.pi * c_idx) / max(1, num_clusters)
        cx = 500.0 + cluster_orbit_radius * math.cos(c_angle)
        cy = 400.0 + cluster_orbit_radius * math.sin(c_angle)
        cluster_centers[c_name] = (cx, cy)

    # Place nodes around their cluster center
    nodes_by_cluster: Dict[str, List[str]] = {}
    for n_id, data in active_nodes:
        nodes_by_cluster.setdefault(data.get("category_name", "General"), []).append(n_id)

    nodes_data = []
    for c_name, node_list in nodes_by_cluster.items():
        cx, cy = cluster_centers.get(c_name, (500.0, 400.0))
        sub_count = len(node_list)
        sub_radius = max(80.0, sub_count * 45.0)

        for s_idx, n_id in enumerate(node_list):
            data = G.nodes[n_id]
            if sub_count == 1:
                nx_pos, ny_pos = cx, cy
            else:
                s_angle = (2 * math.pi * s_idx) / max(1, sub_count)
                nx_pos = cx + sub_radius * math.cos(s_angle)
                ny_pos = cy + sub_radius * math.sin(s_angle)

            label = data.get("canonical_name", data.get("name", "Concept"))
            desc = data.get("description", "")
            if norm_level == "simple":
                desc = desc[:70] + "..." if len(desc) > 70 else desc

            nodes_data.append({
                "id": n_id,
                "type": "topicNode",
                "position": {"x": round(nx_pos, 1), "y": round(ny_pos, 1)},
                "data": {
                    "id": n_id,
                    "label": label,
                    "description": desc,
                    "type": data.get("topic_type", "concept"),
                    "status": data.get("status", "unlearned"),
                    "retention": data.get("retention", 1.0),
                    "stability": data.get("stability", 1.0),
                    "category": data.get("category_name", "General"),
                    "document_title": data.get("document_title", ""),
                    "degree": degrees.get(n_id, 0),
                    "centrality": round(centrality.get(n_id, 0.0), 2),
                    "detail_level": norm_level,
                    "is_focused": n_id == focus_topic_id,
                    "is_demo": data.get("is_demo", False)
                }
            })

    # 6. Edges with Plain-English Explanations
    def generate_simple_explanation(source_name: str, target_name: str, rel_type: str, is_cross: bool) -> str:
        clean_rel = rel_type.lower().replace("_", " ")
        if "prerequisite" in clean_rel:
            return f"Understanding {source_name} provides the necessary foundation before studying {target_name}."
        elif "builds on" in clean_rel or "extends" in clean_rel:
            return f"{target_name} expands directly upon concepts established in {source_name}."
        elif "contrast" in clean_rel or "difference" in clean_rel:
            return f"{source_name} highlights distinguishing boundaries and contrasting principles against {target_name}."
        elif "part of" in clean_rel or "subset" in clean_rel:
            return f"{source_name} operates as a key component of the broader {target_name} framework."
        elif is_cross:
            return f"Connects ideas between separate study materials: insight from {source_name} applies to {target_name}."
        else:
            return f"Mastering {source_name} helps explain how {target_name} works in this subject."

    edges_data = []
    for u, v, edata in G.edges(data=True):
        if u in selected_node_ids and v in selected_node_ids:
            conf = edata.get("confidence", 0.8)
            # Level 1 filters lower-confidence links to minimize clutter
            if norm_level == "simple" and conf < 0.75:
                continue

            rel_type = edata.get("relationship_type", "relates_to")
            is_cross = edata.get("is_cross_document", False)
            source_label = G.nodes[u].get("canonical_name", "Concept A")
            target_label = G.nodes[v].get("canonical_name", "Concept B")

            simple_expl = generate_simple_explanation(source_label, target_label, rel_type, is_cross)
            edge_label = "prerequisite" if "prerequisite" in rel_type else ("cross-topic" if is_cross else rel_type.replace("_", " "))

            edges_data.append({
                "id": edata.get("id", f"{u}-{v}"),
                "source": u,
                "target": v,
                "label": edge_label,
                "animated": "prerequisite" in rel_type or is_cross,
                "data": {
                    "relationship_type": rel_type,
                    "confidence": conf,
                    "is_cross_document": is_cross,
                    "simple_explanation": simple_expl,
                    "evidence": edata.get("evidence", "") if norm_level != "simple" else simple_expl
                }
            })

    # Format clusters overview
    clusters_info = [
        {"name": c_name, "count": len(members), "center": cluster_centers.get(c_name, (500.0, 400.0))}
        for c_name, members in nodes_by_cluster.items()
    ]

    stats = {
        "total_nodes": len(nodes_data),
        "total_edges": len(edges_data),
        "full_vault_nodes": len(topics),
        "full_vault_edges": len(relationships),
        "detail_level": norm_level,
        "density": round(nx.density(G), 3) if len(topics) > 1 else 0.0,
        "clusters_count": len(clusters_info),
        "most_central_topic": max(centrality.items(), key=lambda x: x[1])[0] if centrality else None
    }

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "clusters": clusters_info,
        "stats": stats
    }

def get_concept_details_payload(db: Session, user_id: str, topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns an interactive concept details panel payload with working learning resources,
    connected concepts, plain-English explanations, and real deep links.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
    if not topic:
        return None

    # 1. Associated Documents
    doc_assocs = db.query(DocumentTopic).filter(DocumentTopic.topic_id == topic.id).all()
    doc_ids = [da.document_id for da in doc_assocs]
    docs = db.query(Document).filter(Document.id.in_(doc_ids), Document.user_id == user_id).all() if doc_ids else []
    
    docs_payload = [{"id": d.id, "title": d.title, "filename": d.filename} for d in docs]

    # 2. Outgoing & Incoming Connections
    relationships = db.query(TopicRelationship).filter(
        TopicRelationship.user_id == user_id,
        (TopicRelationship.source_topic_id == topic.id) | (TopicRelationship.target_topic_id == topic.id)
    ).all()

    all_nbr_ids = set()
    for r in relationships:
        all_nbr_ids.add(r.source_topic_id)
        all_nbr_ids.add(r.target_topic_id)
    all_nbr_ids.discard(topic.id)

    nbr_topics = {t.id: t for t in db.query(Topic).filter(Topic.id.in_(all_nbr_ids), Topic.user_id == user_id).all()} if all_nbr_ids else {}

    connections = []
    for r in relationships:
        is_source = r.source_topic_id == topic.id
        nbr_id = r.target_topic_id if is_source else r.source_topic_id
        nbr = nbr_topics.get(nbr_id)
        if not nbr:
            continue

        rel_type = r.relationship_type.replace("_", " ").title()
        explanation = (
            f"Studying {topic.canonical_name} prepares you for {nbr.canonical_name}." if "prerequisite" in r.relationship_type
            else f"Closely connected to {nbr.canonical_name} in your learning vault."
        )

        connections.append({
            "topic_id": nbr.id,
            "topic_name": nbr.canonical_name,
            "direction": "outgoing" if is_source else "incoming",
            "relationship_type": rel_type,
            "confidence": r.confidence,
            "simple_explanation": explanation,
            "evidence": r.evidence_text
        })

    # 3. Available Learning Resources
    # Existing Quizzes
    quizzes = db.query(Quiz).filter(Quiz.topic_id == topic.id, Quiz.user_id == user_id).order_by(Quiz.created_at.desc()).limit(1).all()
    quiz_id = quizzes[0].id if quizzes else None

    # Existing Flashcard Decks
    decks = db.query(FlashcardDeck).filter(FlashcardDeck.topic_id == topic.id, FlashcardDeck.user_id == user_id).order_by(FlashcardDeck.created_at.desc()).limit(1).all()
    deck_id = decks[0].id if decks else None

    # Existing Mind Maps
    mindmaps = db.query(MindMap).filter(MindMap.topic_id == topic.id, MindMap.user_id == user_id).order_by(MindMap.created_at.desc()).limit(1).all()
    mindmap_id = mindmaps[0].id if mindmaps else None

    # Memory retention state
    mem = db.query(TopicMemoryState).filter(TopicMemoryState.topic_id == topic.id, TopicMemoryState.user_id == user_id).first()
    retention_pct = int(round((mem.estimated_retention if mem else 1.0) * 100))
    stability_days = round(mem.stability if mem else 1.0, 1)

    return {
        "id": topic.id,
        "name": topic.canonical_name,
        "description": topic.description or f"Essential academic concept in {topic.canonical_name}.",
        "topic_type": topic.topic_type or "concept",
        "retention_percentage": retention_pct,
        "stability_days": stability_days,
        "status": mem.status if mem else "unlearned",
        "source_documents": docs_payload,
        "connections": connections,
        "resources": {
            "learn_url": f"/learn?topic={topic.canonical_name}",
            "quiz_id": quiz_id,
            "quiz_url": f"/recall?topic_id={topic.id}" if quiz_id else None,
            "deck_id": deck_id,
            "flashcards_url": f"/flashcards?deck_id={deck_id}" if deck_id else None,
            "mindmap_id": mindmap_id,
            "mindmap_url": f"/mindmaps?map_id={mindmap_id}" if mindmap_id else None
        }
    }

def connect_new_topics_heuristic(db: Session, user_id: str, new_topics: List[Topic]):
    """
    Automatically links new topics together and with existing user topics based on
    semantic similarity, co-occurrence, and keyword inclusion.
    Tags cross-document connections when source documents differ.
    """
    all_topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    if len(all_topics) < 2:
        return

    # Check for relations among new topics
    for i in range(len(new_topics)):
        for j in range(i + 1, len(new_topics)):
            t1 = new_topics[i]
            t2 = new_topics[j]
            # Link them as related concepts
            rel = TopicRelationship(
                user_id=user_id,
                source_topic_id=t1.id,
                target_topic_id=t2.id,
                relationship_type="relates_to",
                confidence=0.85,
                evidence_text=f"Co-occurred in study material: '{t1.name}' and '{t2.name}'."
            )
            db.add(rel)

    # If existing topics exist, connect with relevant keyword overlap
    for new_t in new_topics:
        for exist_t in all_topics:
            if new_t.id == exist_t.id:
                continue
            words1 = set(new_t.name.lower().split())
            words2 = set(exist_t.name.lower().split())
            if words1.intersection(words2):
                rel = TopicRelationship(
                    user_id=user_id,
                    source_topic_id=exist_t.id,
                    target_topic_id=new_t.id,
                    relationship_type="builds_on",
                    confidence=0.75,
                    evidence_text=f"Shared conceptual domain between '{exist_t.name}' and '{new_t.name}'."
                )
                db.add(rel)
    db.commit()
