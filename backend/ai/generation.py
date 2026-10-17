"""
Centralized RAG Intelligence Engine.
Connects RetrievalService, Gemini Provider, Prompts, and Grounded Fallbacks.
Powers Learn, Recall/Quiz, Flashcards, Mind Maps, Knowledge Graph, and AI Tutor.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Topic, Document, SourceChunk, TopicRelationship, DocumentTopic
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.retrieval import RetrievalService
from backend.ai.fallback_engine import DeterministicAIEngine
from backend.ai.prompts import (
    UNIVERSAL_GROUNDING_INSTRUCTIONS,
    LEARN_EXPLAIN_PROMPT,
    QUIZ_GENERATE_PROMPT,
    FLASHCARD_GENERATE_PROMPT,
    MINDMAP_GENERATE_PROMPT,
    GRAPH_EXTRACTION_PROMPT,
    TUTOR_CHAT_PROMPT,
)
from backend.ai.schemas import (
    QuizOutputSchema,
    FlashcardDeckSchema,
    MindMapOutputSchema,
    KnowledgeGraphExtractionSchema,
    ExplanationOutputSchema
)

logger = logging.getLogger(__name__)

class RAGIntelligenceEngine:
    def __init__(self, db: Session):
        self.db = db
        self.provider = GeminiProvider()
        self.retrieval = RetrievalService(db, self.provider)

    def _format_retrieved_context(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No specific source chunks available."
        lines = []
        for idx, c in enumerate(chunks, 1):
            source_tag = f"Source: {c['filename']}"
            if c.get("page_number"):
                source_tag += f" (Page {c['page_number']})"
            if c.get("section_heading"):
                source_tag += f" [Section: {c['section_heading']}]"
            lines.append(f"--- Chunk {idx} | {source_tag} ---\n{c['content']}\n")
        return "\n".join(lines)

    # 1. LEARN ENGINE
    def explain_topic(
        self,
        user_id: str,
        topic_name: str,
        depth: str = "semi-detailed",
        user_query: Optional[str] = None,
        personalization_context: Optional[Dict[str, Any]] = None,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        from backend.concept_inventory import ConceptInventoryBuilder
        inventory_builder = ConceptInventoryBuilder(self.db)

        # 1. Topic-scoped document resolution to prevent cross-document contamination
        resolved_docs = list(document_ids or [])
        if not resolved_docs and topic_name:
            topic_obj = self.db.query(Topic).filter(
                Topic.user_id == user_id,
                (Topic.canonical_name.ilike(topic_name.strip()) | Topic.name.ilike(topic_name.strip()))
            ).first()
            if topic_obj:
                linked_doc_ids = [
                    dt.document_id for dt in self.db.query(DocumentTopic.document_id).filter(
                        DocumentTopic.topic_id == topic_obj.id
                    ).all()
                ]
                if linked_doc_ids:
                    resolved_docs = linked_doc_ids

        # Build / fetch concept inventory for user's relevant documents
        concept_inventory = []
        for doc_id in resolved_docs:
            try:
                inv = inventory_builder.build_or_get_inventory(doc_id, user_id)
                if inv and inv.concepts_json:
                    concept_inventory.extend(inv.concepts_json)
            except Exception as e:
                logger.warning(f"Could not load inventory for doc {doc_id}: {e}")

        # Choose retrieval mode based on request scope
        is_comprehensive = (depth == "detailed") or (user_query and any(w in user_query.lower() for w in ["entire", "chapter", "all", "complete", "everything", "syllabus"]))
        if is_comprehensive:
            retrieved_chunks = self.retrieval.retrieve_comprehensive(
                user_id=user_id,
                query=f"{topic_name} {user_query or ''}",
                document_ids=resolved_docs or None,
                max_chunks=12
            )
        else:
            retrieved_chunks = self.retrieval.retrieve(
                user_id=user_id,
                query=f"{topic_name} {user_query or ''}",
                document_ids=resolved_docs or None,
                top_k=5
            )

        has_grounded_chunks = len(retrieved_chunks) > 0
        retrieved_context = self._format_retrieved_context(retrieved_chunks)
        ctx = personalization_context or {}

        # 2. If Gemini provider is available, use real LLM generation
        if self.provider.is_available():
            inventory_summary = ", ".join(c.get("name", "") for c in concept_inventory[:15]) if concept_inventory else "Standard topic scope"
            prompt = LEARN_EXPLAIN_PROMPT.format(
                universal_grounding=UNIVERSAL_GROUNDING_INSTRUCTIONS,
                topic_name=topic_name,
                depth=depth,
                learner_context=str(ctx.get("learning_context") or ctx.get("user_roles") or "General Learner"),
                learning_goals=str(ctx.get("learning_goals_list") or "Comprehensive mastery"),
                concept_inventory=inventory_summary,
                retrieved_context=retrieved_context if has_grounded_chunks else "NO_DOCUMENT_CHUNKS: Provide a foundational explanation from general educational knowledge. Do NOT fabricate document citations or page numbers.",
                user_query=user_query or f"Explain {topic_name} at {depth} depth."
            )
            try:
                structured = self.provider.generate_structured(prompt, ExplanationOutputSchema)
                if isinstance(structured, dict):
                    structured["detail_level"] = depth
                    if not structured.get("topic_name"):
                        structured["topic_name"] = topic_name
                    if not structured.get("explanation") and retrieved_chunks:
                        fallback_exp = DeterministicAIEngine.generate_grounded_explanation(
                            topic_name=topic_name,
                            sources=[c["content"] for c in retrieved_chunks],
                            depth=depth,
                            user_query=user_query,
                            personalization_context=personalization_context,
                            concept_inventory=concept_inventory
                        )
                        structured["explanation"] = fallback_exp.get("explanation", f"Core concepts and foundational principles of {topic_name}.")
                    if not structured.get("covered_concepts") and concept_inventory:
                        structured["covered_concepts"] = [c.get("name") for c in concept_inventory[:6]]
                    if not structured.get("exam_traps"):
                        structured["exam_traps"] = [
                            f"Overlooking boundary conditions or edge cases in {topic_name}.",
                            f"Confusing {topic_name} with adjacent principles without verifying underlying conditions."
                        ]
                    # Format grounded sources honestly
                    if has_grounded_chunks:
                        structured["grounded_sources"] = [
                            {
                                "document_id": c.get("document_id"),
                                "filename": c.get("filename"),
                                "chunk_id": c.get("chunk_id", c.get("id", "")),
                                "page_number": c.get("page_number", 1),
                                "section_heading": c.get("section_heading"),
                                "snippet": c.get("content", "")[:200]
                            }
                            for c in retrieved_chunks
                        ]
                        structured["coverage_status"] = "verified"
                    else:
                        structured["grounded_sources"] = []
                        structured["coverage_status"] = "general_ai_knowledge"
                        structured["source_citations"] = ["General AI Knowledge"]
                return structured
            except Exception as e:
                logger.warning(f"Gemini explain generation failed ({e}), using grounded academic fallback")
                source_texts = [c["content"] for c in retrieved_chunks]
                res = DeterministicAIEngine.generate_grounded_explanation(
                    topic_name=topic_name,
                    sources=source_texts,
                    depth=depth,
                    user_query=user_query,
                    personalization_context=personalization_context,
                    concept_inventory=concept_inventory
                )
                if retrieved_chunks:
                    res["grounded_sources"] = [
                        {
                            "document_id": c.get("document_id"),
                            "filename": c.get("filename"),
                            "chunk_id": c.get("chunk_id", c.get("id", "")),
                            "snippet": c.get("content", "")[:200],
                            "page_number": c.get("page_number", 1)
                        }
                        for c in retrieved_chunks
                    ]
                return res

        # 3. Deterministic Grounded Fallback (used only when no AI provider is configured)
        source_texts = [c["content"] for c in retrieved_chunks]
        return DeterministicAIEngine.generate_grounded_explanation(
            topic_name=topic_name,
            sources=source_texts,
            depth=depth,
            user_query=user_query,
            personalization_context=personalization_context,
            concept_inventory=concept_inventory
        )

    # 2. RECALL / QUIZ ENGINE
    def generate_quiz(
        self,
        user_id: str,
        topic_name: str,
        question_count: int = 4,
        difficulty: str = "medium",
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        resolved_docs = list(document_ids or [])
        if not resolved_docs and topic_name:
            topic_obj = self.db.query(Topic).filter(
                Topic.user_id == user_id,
                (Topic.canonical_name.ilike(topic_name.strip()) | Topic.name.ilike(topic_name.strip()))
            ).first()
            if topic_obj:
                linked_doc_ids = [
                    dt.document_id for dt in self.db.query(DocumentTopic.document_id).filter(
                        DocumentTopic.topic_id == topic_obj.id
                    ).all()
                ]
                if linked_doc_ids:
                    resolved_docs = linked_doc_ids

        retrieved_chunks = self.retrieval.retrieve(
            user_id=user_id,
            query=f"{topic_name} core principles mechanisms evaluation",
            document_ids=resolved_docs or None,
            top_k=6
        )
        retrieved_context = self._format_retrieved_context(retrieved_chunks)

        if self.provider.is_available():
            prompt = QUIZ_GENERATE_PROMPT.format(
                universal_grounding=UNIVERSAL_GROUNDING_INSTRUCTIONS,
                topic_name=topic_name,
                question_count=question_count,
                difficulty=difficulty,
                retrieved_context=retrieved_context
            )
            try:
                res = self.provider.generate_structured(prompt, QuizOutputSchema)
                return res
            except Exception as e:
                logger.warning(f"Gemini quiz generation failed ({e}), falling back to grounded deterministic quiz engine")
                source_texts = [c["content"] for c in retrieved_chunks]
                return DeterministicAIEngine.generate_grounded_quiz(
                    topic_name=topic_name,
                    sources=source_texts,
                    question_count=question_count,
                    difficulty=difficulty
                )

        source_texts = [c["content"] for c in retrieved_chunks]
        return DeterministicAIEngine.generate_grounded_quiz(
            topic_name=topic_name,
            sources=source_texts,
            question_count=question_count,
            difficulty=difficulty
        )

    # 3. FLASHCARD ENGINE
    def generate_flashcards(
        self,
        user_id: str,
        topic_name: str,
        card_count: Optional[int] = None,
        detail_level: str = "semi-detailed",
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Adaptive flashcard deck generator.
        Dynamically adapts card count to concept inventory breadth and source size.
        Supports 3 distinct detail modes: brief, semi-detailed, detailed.
        """
        from backend.concept_inventory import ConceptInventoryBuilder
        inventory_builder = ConceptInventoryBuilder(self.db)

        # 1. Resolve document IDs for this topic if not passed
        resolved_docs = list(document_ids or [])
        if not resolved_docs and topic_name:
            topic_obj = self.db.query(Topic).filter(
                Topic.user_id == user_id,
                (Topic.canonical_name.ilike(topic_name.strip()) | Topic.name.ilike(topic_name.strip()))
            ).first()
            if topic_obj:
                linked_doc_ids = [
                    dt.document_id for dt in self.db.query(DocumentTopic.document_id).filter(
                        DocumentTopic.topic_id == topic_obj.id
                    ).all()
                ]
                if linked_doc_ids:
                    resolved_docs = linked_doc_ids

        concept_inventory = []
        for doc_id in resolved_docs:
            try:
                inv = inventory_builder.build_or_get_inventory(doc_id, user_id)
                if inv and inv.concepts_json:
                    concept_inventory.extend(inv.concepts_json)
            except Exception as e:
                logger.warning(f"Could not load inventory for doc {doc_id}: {e}")

        # 2. Adaptive card count determination
        if card_count is None:
            concept_count = len(concept_inventory)
            if concept_count <= 4:
                effective_count = max(3, concept_count)
            elif concept_count <= 10:
                effective_count = min(8, concept_count)
            else:
                effective_count = min(15, concept_count)

            if detail_level == "brief":
                effective_count = max(3, int(effective_count * 0.8))
            elif detail_level == "detailed":
                effective_count = min(15, effective_count + 2)
        else:
            effective_count = card_count

        # 3. Comprehensive retrieval across full topic scope
        retrieved_chunks = self.retrieval.retrieve_comprehensive(
            user_id=user_id,
            query=f"{topic_name} definitions key facts relationships mechanisms",
            document_ids=resolved_docs or None,
            max_chunks=10
        )
        retrieved_context = self._format_retrieved_context(retrieved_chunks)

        if self.provider.is_available():
            inventory_summary = ", ".join(c.get("name", "") for c in concept_inventory[:15]) if concept_inventory else "Standard topic scope"
            prompt = FLASHCARD_GENERATE_PROMPT.format(
                universal_grounding=UNIVERSAL_GROUNDING_INSTRUCTIONS,
                topic_name=topic_name,
                card_count=effective_count,
                detail_level=detail_level,
                concept_inventory=inventory_summary,
                retrieved_context=retrieved_context
            )
            try:
                res = self.provider.generate_structured(prompt, FlashcardDeckSchema)
                if isinstance(res, dict):
                    res["detail_level"] = detail_level
                    cards = res.get("cards", [])
                    # If LLM under-generated cards relative to effective_count, augment with grounded fallback cards
                    if len(cards) < effective_count and retrieved_chunks:
                        source_texts = [c["content"] for c in retrieved_chunks]
                        fallback_deck = DeterministicAIEngine.generate_grounded_flashcards(
                            topic_name=topic_name,
                            sources=source_texts,
                            card_count=effective_count,
                            detail_level=detail_level,
                            concept_inventory=concept_inventory
                        )
                        existing_prompts = {c["front"].lower().strip() for c in cards}
                        for fc in fallback_deck.get("cards", []):
                            if fc["front"].lower().strip() not in existing_prompts:
                                cards.append(fc)
                                existing_prompts.add(fc["front"].lower().strip())
                            if len(cards) >= effective_count:
                                break
                        res["cards"] = cards
                    for idx, c in enumerate(res.get("cards", [])):
                        if not c.get("detail_level") or c.get("detail_level") != detail_level:
                            c["detail_level"] = detail_level
                        if not c.get("section_name"):
                            if concept_inventory and idx < len(concept_inventory):
                                c["section_name"] = concept_inventory[idx].get("section_heading", "Core Principles")
                                c["concept_id"] = concept_inventory[idx].get("concept_id", f"c_{idx}")
                            elif retrieved_chunks and idx < len(retrieved_chunks):
                                c["section_name"] = retrieved_chunks[idx].get("section_heading", "Core Concepts")
                                c["concept_id"] = f"chunk_{idx}"
                            else:
                                c["section_name"] = "Core Principles"
                                c["concept_id"] = f"c_{idx}"
                    res["covered_concepts_count"] = len(res.get("cards", []))
                    return res
            except Exception as e:
                logger.warning(f"Gemini flashcard generation failed ({e}), falling back to grounded deterministic engine")
                source_texts = [c["content"] for c in retrieved_chunks]
                return DeterministicAIEngine.generate_grounded_flashcards(
                    topic_name=topic_name,
                    sources=source_texts,
                    card_count=effective_count,
                    detail_level=detail_level,
                    concept_inventory=concept_inventory
                )

        source_texts = [c["content"] for c in retrieved_chunks]
        return DeterministicAIEngine.generate_grounded_flashcards(
            topic_name=topic_name,
            sources=source_texts,
            card_count=effective_count,
            detail_level=detail_level,
            concept_inventory=concept_inventory
        )

    # 4. MIND MAP ENGINE
    def generate_mind_map(
        self,
        user_id: str,
        central_topic: str,
        detail_level: str = "semi-detailed",
        document_ids: Optional[List[str]] = None,
        source_text: Optional[str] = None,
        subtopics: Optional[List[Dict[str, Any]]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        retrieved_chunks = self.retrieval.retrieve(
            user_id=user_id,
            query=f"{central_topic} structure categories components",
            document_ids=document_ids,
            top_k=4
        )
        retrieved_context = self._format_retrieved_context(retrieved_chunks)
        combined_source = (source_text or "") + "\n\n" + retrieved_context
        branches_data = list(subtopics or [])
        if self.provider.is_available():
            prompt = MINDMAP_GENERATE_PROMPT.format(
                universal_grounding=UNIVERSAL_GROUNDING_INSTRUCTIONS,
                central_topic=central_topic,
                detail_level=detail_level,
                retrieved_context=retrieved_context
            )
            try:
                res = self.provider.generate_structured(prompt, MindMapOutputSchema)
                branches_data = res.get("branches", [])
            except Exception as e:
                logger.warning(f"Gemini mindmap generation failed: {e}")

        # Build React Flow nodes and edges using deterministic formatter
        from backend.ai_engine import AITutorEngine
        source_texts = [c["content"] for c in retrieved_chunks]
        if source_text:
            source_texts.insert(0, source_text)

        formatted_subtopics = []
        if subtopics:
            for s in subtopics:
                formatted_subtopics.append({
                    "name": s.get("name") or s.get("title") or s.get("canonical_name") or "",
                    "description": s.get("description", "")
                })
        for b in branches_data:
            if isinstance(b, dict):
                b_name = b.get("name") or b.get("title") or b.get("canonical_name") or ""
                if b_name and not any(s["name"] == b_name for s in formatted_subtopics):
                    formatted_subtopics.append({
                        "name": b_name,
                        "description": b.get("description", "")
                    })

        return AITutorEngine.generate_mind_map(
            central_topic=central_topic,
            detail_level=detail_level,
            source_text="\n\n".join(source_texts),
            subtopics=formatted_subtopics if formatted_subtopics else None,
            relationships=relationships if relationships else None
        )

    # 5. KNOWLEDGE GRAPH EXTRACTION & CROSS-DOCUMENT CONNECTIVITY
    def extract_graph_elements_from_document(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        title: str,
        raw_text: str
    ) -> Dict[str, Any]:
        """
        Extracts genuine concepts and relationships from an uploaded document.
        When multiple documents exist, discovers evidence-based cross-document edges.
        """
        # 1. Run full-document hierarchical extractor to discover all Units, Chapters & Sections
        from backend.extractor import extract_topics_and_concepts
        raw_topics = extract_topics_and_concepts(raw_text, filename)

        # 2. If Gemini is available, use structured LLM extraction with multi-window full-document text
        if self.provider.is_available():
            if len(raw_text) <= 24000:
                document_snippet = raw_text
            else:
                # Multi-window sampling across early, middle, and late document sections
                outline_lines = [f"- [{t.get('topic_type', 'topic').upper()}] {t['canonical_name']}" for t in raw_topics[:20]]
                outline_text = "DISCOVERED OUTLINE & SYLLABUS UNITS ACROSS ALL PAGES:\n" + "\n".join(outline_lines)
                
                mid_point = len(raw_text) // 2
                early_chunk = raw_text[:8000]
                mid_chunk = raw_text[mid_point - 4000:mid_point + 4000]
                late_chunk = raw_text[-8000:]
                
                document_snippet = (
                    f"{outline_text}\n\n"
                    f"--- DOCUMENT START (Early Units) ---\n{early_chunk}\n\n"
                    f"--- DOCUMENT MIDDLE (Intermediate Units) ---\n{mid_chunk}\n\n"
                    f"--- DOCUMENT CONCLUSION (Late Units & Topics) ---\n{late_chunk}"
                )

            prompt = GRAPH_EXTRACTION_PROMPT.format(
                universal_grounding=UNIVERSAL_GROUNDING_INSTRUCTIONS,
                filename=filename,
                title=title,
                document_text=document_snippet
            )
            try:
                extracted = self.provider.generate_structured(prompt, KnowledgeGraphExtractionSchema)
                nodes = extracted.get("nodes", [])
                edges = extracted.get("edges", [])
                
                if nodes:
                    # Merge any critical Units / Chapters discovered by full scan that were missed
                    existing_names = {n["name"].strip().lower() for n in nodes}
                    for t in raw_topics:
                        if t.get("topic_type") in ["unit", "chapter"] and t["canonical_name"].lower() not in existing_names:
                            nodes.append({
                                "name": t["canonical_name"],
                                "topic_type": t.get("topic_type", "unit"),
                                "description": t.get("description", f"Curriculum division from {filename}"),
                                "aliases": []
                            })
                            existing_names.add(t["canonical_name"].lower())

                    # Ensure sequence edges between consecutive units
                    unit_nodes = [n for n in nodes if n.get("topic_type") in ["unit", "chapter"]]
                    for i in range(len(unit_nodes) - 1):
                        u_src = unit_nodes[i]["name"]
                        u_tgt = unit_nodes[i + 1]["name"]
                        if not any(e.get("source") == u_src and e.get("target") == u_tgt for e in edges):
                            edges.append({
                                "source": u_src,
                                "target": u_tgt,
                                "relationship_type": "prerequisite_of",
                                "confidence": 0.95,
                                "evidence": f"Sequential syllabus unit progression in {filename}."
                            })

                    return {"nodes": nodes, "edges": edges}
            except Exception as e:
                logger.warning(f"Gemini full-document graph extraction failed: {e}")

        # Fallback to deterministic extractor
        nodes = []
        edges = []
        for t in raw_topics:
            nodes.append({
                "name": t["canonical_name"],
                "topic_type": t.get("topic_type", "concept"),
                "description": t.get("description", f"Extracted from {filename}: {t['canonical_name']}"),
                "aliases": []
            })
        
        # Link adjacent pairs with explicit relationship
        for i in range(len(nodes) - 1):
            rel_type = "prerequisite_of" if nodes[i].get("topic_type") in ["unit", "chapter"] else "relates_to"
            edges.append({
                "source": nodes[i]["name"],
                "target": nodes[i + 1]["name"],
                "relationship_type": rel_type,
                "confidence": 0.85,
                "evidence": f"Curriculum association from {filename}."
            })

        return {"nodes": nodes, "edges": edges}

    # 6. AI TUTOR CHAT (Conversational RAG)
    def chat_with_tutor(
        self,
        user_id: str,
        user_name: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        personalization_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # 1. Retrieve top source chunks
        retrieved_chunks = self.retrieval.retrieve(
            user_id=user_id,
            query=user_message,
            top_k=3
        )
        retrieved_context = self._format_retrieved_context(retrieved_chunks)
        ctx = personalization_context or {}

        # 2. Format recent history (bounded to last 4 turns)
        history_str = "None"
        if conversation_history:
            h_lines = []
            for h in conversation_history[-4:]:
                role = "User" if h.get("role") == "user" else "Assistant"
                h_lines.append(f"{role}: {h.get('content', '')}")
            history_str = "\n".join(h_lines)

        # 3. Call Gemini if available
        if self.provider.is_available():
            prompt = TUTOR_CHAT_PROMPT.format(
                universal_grounding=UNIVERSAL_GROUNDING_INSTRUCTIONS,
                user_name=user_name,
                learner_context=str(ctx.get("learning_context") or ctx.get("user_roles") or "Learner"),
                conversation_history=history_str,
                retrieved_context=retrieved_context,
                user_query=user_message
            )
            try:
                reply = self.provider.generate_text(prompt, temperature=0.3)
                citations = [f"{c['filename']} (Page {c['page_number']})" if c.get("page_number") else c['filename'] for c in retrieved_chunks]
                return {
                    "reply": reply,
                    "citations": citations,
                    "is_grounded": bool(retrieved_chunks)
                }
            except Exception as e:
                logger.warning(f"Gemini tutor chat failed: {e}")
                return {
                    "reply": f"⚠️ The AI Tutor is temporarily unable to generate responses due to upstream service demand or rate limits ({e}). Please try again in a few moments.",
                    "citations": [f"{c['filename']} (Page {c.get('page_number', 1)})" for c in retrieved_chunks] if retrieved_chunks else [],
                    "is_grounded": bool(retrieved_chunks),
                    "provider_unavailable": True
                }

        # 4. Fallback tutor response (only when no AI provider is configured)
        if retrieved_chunks:
            top_c = retrieved_chunks[0]
            cite = f"{top_c['filename']} (Page {top_c.get('page_number', 1)})"
            reply = (
                f"Based on your notes in **{top_c['document_title']}**:\n\n"
                f"> \"{top_c['content'][:250]}...\"\n\n"
                f"This concept is directly cataloged in your knowledge graph. "
                f"You can reinforce this retention via a targeted Recall drill or inspect related nodes in your Knowledge Graph!"
            )
            return {
                "reply": reply,
                "citations": [cite],
                "is_grounded": True
            }
        else:
            return {
                "reply": (
                    f"Regarding '{user_message}': While this topic was not found in your currently indexed notes, "
                    f"uploading your study materials or slides will automatically map its concepts into your knowledge graph!"
                ),
                "citations": [],
                "is_grounded": False
            }
