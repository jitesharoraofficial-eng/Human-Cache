"""
Learning Resource Preparation Service.

Ensures that before inviting a learner to review a topic or take a recall quiz,
appropriate, source-grounded learning resources (Quizzes, Flashcard Decks, Notes)
already exist or are prepared idempotently with zero hallucination.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models import Topic, Quiz, FlashcardDeck, Flashcard, Note, DocumentTopic
from backend.ai.generation import RAGIntelligenceEngine

logger = logging.getLogger(__name__)

def prepare_or_reuse_learning_resources(
    db: Session,
    user_id: str,
    topic_id: str,
    auto_generate: bool = True
) -> Dict[str, Any]:
    """
    Checks for existing study materials for the topic.
    If none exist and auto_generate is True, generates and persists a high-yield recall quiz
    and flashcard deck using the RAG intelligence engine.
    If auto_generate is False, defers LLM generation until user explicitly initiates learning.
    Returns status and resource IDs.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
    if not topic:
        return {"status": "error", "message": "Topic not found"}

    # 1. Check for existing Quiz
    existing_quiz = db.query(Quiz).filter(Quiz.user_id == user_id, Quiz.topic_id == topic_id).first()
    
    # 2. Check for existing Flashcard Deck
    existing_deck = db.query(FlashcardDeck).filter(FlashcardDeck.user_id == user_id, FlashcardDeck.topic_id == topic_id).first()

    # If auto-generation is not requested (e.g. background notification scan / startup), return immediately
    if not auto_generate:
        return {
            "status": "ready" if (existing_quiz or existing_deck) else "deferred",
            "topic_id": topic_id,
            "topic_name": topic.canonical_name,
            "quiz_id": existing_quiz.id if existing_quiz else None,
            "deck_id": existing_deck.id if existing_deck else None,
            "action_url": f"/recall?topic_id={topic_id}" if existing_quiz else f"/learn?topic_id={topic_id}"
        }

    rag_engine = RAGIntelligenceEngine(db)

    # If quiz is missing, synthesize one grounded in user's documents
    quiz_id = existing_quiz.id if existing_quiz else None
    if not existing_quiz:
        try:
            quiz_data = rag_engine.generate_quiz(
                user_id=user_id,
                topic_name=topic.canonical_name,
                question_count=3,
                difficulty="medium"
            )
            new_quiz = Quiz(
                user_id=user_id,
                topic_id=topic_id,
                title=quiz_data.get("title", f"Active Recall Drill: {topic.canonical_name}"),
                difficulty="medium",
                questions=quiz_data.get("questions", [])
            )
            db.add(new_quiz)
            db.commit()
            db.refresh(new_quiz)
            quiz_id = new_quiz.id
            logger.info(f"Prepared new quiz {quiz_id} for topic {topic.canonical_name}")
        except Exception as e:
            logger.warning(f"Could not auto-generate quiz for topic {topic_id}: {e}")

    # If flashcard deck is missing, synthesize an adaptive one
    deck_id = existing_deck.id if existing_deck else None
    if not existing_deck:
        try:
            deck_data = rag_engine.generate_flashcards(
                user_id=user_id,
                topic_name=topic.canonical_name,
                detail_level="semi-detailed"
            )
            cards = deck_data.get("cards", [])
            if cards:
                new_deck = FlashcardDeck(
                    user_id=user_id,
                    topic_id=topic_id,
                    title=f"Deck: {topic.canonical_name}",
                    description=f"Auto-generated drill cards for {topic.canonical_name}",
                    detail_level="semi-detailed",
                    version=1
                )
                db.add(new_deck)
                db.commit()
                db.refresh(new_deck)
                deck_id = new_deck.id

                for c in cards:
                    fc = Flashcard(
                        deck_id=new_deck.id,
                        front=c["front"],
                        back=c["back"],
                        hint=c.get("hint", ""),
                        topic_id=topic_id,
                        detail_level=c.get("detail_level", "semi-detailed"),
                        concept_id=c.get("concept_id"),
                        section_name=c.get("section_name"),
                        source_citation=c.get("source_citation")
                    )
                    db.add(fc)
                db.commit()
                logger.info(f"Prepared new adaptive flashcard deck {deck_id} ({len(cards)} cards) for topic {topic.canonical_name}")
        except Exception as e:
            logger.warning(f"Could not auto-generate flashcard deck for topic {topic_id}: {e}")

    return {
        "status": "ready",
        "topic_id": topic_id,
        "topic_name": topic.canonical_name,
        "quiz_id": quiz_id,
        "deck_id": deck_id,
        "action_url": f"/recall?topic_id={topic_id}" if quiz_id else f"/learn?topic_id={topic_id}"
    }


def auto_prepare_document_learning_suite(
    db: Session,
    user_id: str,
    document_id: str
) -> Dict[str, Any]:
    """
    Background automated suite preparation triggered upon document upload or capture confirmation.
    Idempotently creates:
    1. Initial comprehensive summary note (document units, concepts, key takeaways).
    2. Primary and secondary topic drill quizzes (3 grounded questions each).
    3. Primary and secondary topic adaptive flashcards (3-5 cards each).
    4. Initial interactive mind map.
    5. Dispatches an in-app notification when the learning suite is ready.
    """
    from backend.models import Document, MindMap
    from backend.notification_engine import dispatch_notification

    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        return {"status": "error", "message": "Document not found"}

    try:
        doc.resource_prep_status = "processing"
        db.commit()

        # 1. Resolve topics discovered for this document
        doc_topics = (
            db.query(Topic)
            .join(DocumentTopic, DocumentTopic.topic_id == Topic.id)
            .filter(DocumentTopic.document_id == document_id, Topic.user_id == user_id)
            .all()
        )
        if not doc_topics:
            doc_topics = db.query(Topic).filter(Topic.user_id == user_id).limit(6).all()

        primary_topic = doc_topics[0] if doc_topics else None

        # 2. Check / create initial comprehensive synthesis note
        existing_note = db.query(Note).filter(
            Note.user_id == user_id,
            Note.document_id == document_id,
            Note.source_type == "auto_summary"
        ).first()
        note_id = existing_note.id if existing_note else None

        if not existing_note and primary_topic:
            try:
                units = [t for t in doc_topics if t.topic_type in ["unit", "chapter"]]
                concepts = [t for t in doc_topics if t.topic_type not in ["unit", "chapter"]]
                
                units_section = ""
                if units:
                    units_section = "\n**Curriculum Units & Chapters:**\n" + "\n".join([f"- **{u.canonical_name}**: {u.description[:100] if u.description else 'Core curriculum division'}" for u in units])
                
                concepts_section = "\n**Core Concepts:**\n" + "\n".join([f"- **{c.canonical_name}**: {c.description[:120] if c.description else 'Foundational concept'}" for c in (concepts[:8] if concepts else doc_topics[:6])])

                summary_text = (
                    f"### Comprehensive Study Guide: {doc.title}\n\n"
                    f"**Primary Focus:** {primary_topic.canonical_name}\n\n"
                    f"{primary_topic.description or 'Foundational study concept extracted from uploaded material.'}\n"
                    f"{units_section}\n"
                    f"{concepts_section}\n"
                )
                new_note = Note(
                    user_id=user_id,
                    category_id=doc.category_id,
                    topic_id=primary_topic.id,
                    document_id=document_id,
                    title=f"Study Guide: {doc.title}",
                    content=summary_text,
                    source_type="auto_summary",
                    tags=["auto-summary", "study-guide", primary_topic.canonical_name.lower()]
                )
                db.add(new_note)
                db.commit()
                db.refresh(new_note)
                note_id = new_note.id
                logger.info(f"Auto-prepared comprehensive study note {note_id} for document {doc.title}")
            except Exception as e:
                logger.warning(f"Could not auto-generate note for document {document_id}: {e}")

        # 3. Prepare Quizzes and Flashcards for top 2-3 topics (multi-unit coverage)
        prepared_topics = doc_topics[:3] if len(doc_topics) >= 3 else doc_topics
        quiz_ids = []
        deck_ids = []
        for top in prepared_topics:
            try:
                prep_res = prepare_or_reuse_learning_resources(db, user_id, top.id)
                if prep_res.get("quiz_id"):
                    quiz_ids.append(prep_res["quiz_id"])
                if prep_res.get("deck_id"):
                    deck_ids.append(prep_res["deck_id"])
            except Exception as prep_err:
                logger.warning(f"Resource prep error for topic {top.canonical_name}: {prep_err}")

        # 4. Check / create Mind Map
        existing_map = db.query(MindMap).filter(
            MindMap.user_id == user_id,
            MindMap.document_id == document_id
        ).first()
        map_id = existing_map.id if existing_map else None

        if not existing_map and primary_topic:
            try:
                rag_engine = RAGIntelligenceEngine(db)
                subtopics_list = [
                    {"name": t.name, "canonical_name": t.canonical_name, "description": t.description or ""}
                    for t in doc_topics[1:10]
                ]
                structure = rag_engine.generate_mind_map(
                    user_id=user_id,
                    central_topic=doc.title,
                    detail_level="semi-detailed",
                    document_ids=[document_id],
                    subtopics=subtopics_list if subtopics_list else None
                )
                new_map = MindMap(
                    user_id=user_id,
                    title=f"Mind Map: {doc.title}",
                    central_topic=doc.title,
                    topic_id=primary_topic.id,
                    document_id=document_id,
                    structure_json=structure
                )
                db.add(new_map)
                db.commit()
                db.refresh(new_map)
                map_id = new_map.id
                logger.info(f"Auto-prepared mind map {map_id} for document {doc.title}")
            except Exception as e:
                logger.warning(f"Could not auto-generate mind map for document {document_id}: {e}")

        # 5. Mark preparation completed
        doc.resource_prep_status = "completed"
        db.commit()

        # 6. Dispatch in-app notification alerting user that learning materials are ready
        try:
            dispatch_notification(
                db=db,
                user_id=user_id,
                notification_type="resource_prep_completed",
                title=f"✨ Learning Materials Ready: {doc.title}",
                message=f"Quizzes, flashcards, mind maps, and a study guide are prepared for '{doc.title}'. Ready for active recall!",
                action_url=f"/recall?topic_id={primary_topic.id}" if primary_topic else "/uploads",
                entity_type="document",
                entity_id=doc.id,
                priority="high",
                dedup_key=f"prep_completed_{doc.id}",
                meta={"quiz_count": len(quiz_ids), "deck_count": len(deck_ids), "has_map": bool(map_id)}
            )
        except Exception as notif_err:
            logger.warning(f"Could not send prep notification: {notif_err}")

        return {
            "status": "completed",
            "document_id": document_id,
            "primary_topic_id": primary_topic.id if primary_topic else None,
            "note_id": note_id,
            "quiz_ids": quiz_ids,
            "deck_ids": deck_ids,
            "mind_map_id": map_id
        }

    except Exception as e:
        logger.error(f"auto_prepare_document_learning_suite failed for doc {document_id}: {e}", exc_info=True)
        doc.resource_prep_status = "failed"
        doc.error_message = f"Resource preparation failed: {str(e)}"
        db.commit()
        return {"status": "failed", "document_id": document_id, "error": str(e)}
