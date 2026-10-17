from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import (
    User, UserPreference, Category, Document, SourceChunk,
    Topic, DocumentTopic, TopicRelationship, TopicMemoryState,
    Quiz, FlashcardDeck, Flashcard, MindMap, Note, Exam, StudyTask, Notification
)
from backend.auth import hash_password

DEMO_USER_ID = "demo-user-master-id"
DEMO_USER_EMAIL = "alex.learner@humancache.ai"

def seed_demo_data(db: Session):
    """
    Seeds a rich, approachable, realistic academic and personal learning dataset
    featuring Chemistry (Chemical Bonding), Physics (Newton's Laws),
    Cognitive Science (Active Recall), and Applied Computing.
    """
    # 1. User & Preferences
    user = db.query(User).filter(User.id == DEMO_USER_ID).first()
    if not user:
        user = User(
            id=DEMO_USER_ID,
            email=DEMO_USER_EMAIL,
            name="Alex Sharma",
            hashed_password=hash_password("demouser123"),
            is_active=True,
            is_demo_user=True
        )
        db.add(user)

        pref = UserPreference(
            user_id=DEMO_USER_ID,
            user_roles=["competitive_aspirant", "school_student"],
            learning_goals="Master Core Science & Competitive Concepts with Spaced Active Recall",
            learning_goals_list=["jee_prep", "cbse_prep"],
            target_exam="JEE & CBSE 12th Board",
            curriculum="CBSE / NCERT Standard",
            learning_context={"grade": "Class 12", "target_year": "2027", "stage": "Advanced Revision"},
            subjects_of_interest=["Chemistry", "Physics", "Mathematics", "Cognitive Science"],
            explanation_depth="balanced",
            teaching_styles=["examples_first", "step_by_step", "analogies", "exam_focused"],
            preferred_formats=["summaries", "quizzes", "flashcards", "mind_maps"],
            graph_detail_level="semi-detailed",
            mindmap_detail_level="semi-detailed",
            custom_other_responses={
                "role_other": "Self-directed Olympiad Aspirant",
                "goal_other": "Retain 95%+ of formulas through spaced repetition"
            },
            daily_study_time_minutes=45,
            notifications_enabled=True,
            onboarding_completed=True
        )
        db.add(pref)
        db.commit()

    # If user already has categories and topics, avoid duplicate seeding
    if db.query(Category).filter(Category.user_id == DEMO_USER_ID).count() > 0:
        return

    # 2. Predefined Approachable Categories
    cat_chem = Category(
        user_id=DEMO_USER_ID,
        name="Chemistry — Chemical Bonding & Structure",
        description="Molecular geometry, hybridization, ionic & covalent mechanisms, VSEPR.",
        color="#0284c7"
    )
    cat_phys = Category(
        user_id=DEMO_USER_ID,
        name="Physics — Mechanics & Newton's Laws",
        description="Inertia, momentum conservation, constraint relations, free body dynamics.",
        color="#4f46e5"
    )
    cat_memory = Category(
        user_id=DEMO_USER_ID,
        name="Cognitive Science — Active Recall & Memory",
        description="Ebbinghaus forgetting curve, spaced practice, synaptic stabilization.",
        color="#059669"
    )
    db.add_all([cat_chem, cat_phys, cat_memory])
    db.commit()

    # 3. Documents
    doc_chem = Document(
        user_id=DEMO_USER_ID,
        category_id=cat_chem.id,
        title="NCERT & JEE Notes: Chemical Bonding and Molecular Structure",
        filename="chemical_bonding_master_notes.pdf",
        file_type="pdf",
        file_size_bytes=340000,
        processing_status="completed",
        is_demo=True,
        raw_text="Chemical bonding is the attractive force that holds constituent atoms and ions together in chemical species..."
    )
    doc_phys = Document(
        user_id=DEMO_USER_ID,
        category_id=cat_phys.id,
        title="Physics Core: Newton's Laws of Motion & Momentum Dynamics",
        filename="newtons_laws_mechanics.docx",
        file_type="docx",
        file_size_bytes=280000,
        processing_status="completed",
        is_demo=True,
        raw_text="Newton's laws of motion describe the relationship between a body and the forces acting upon it..."
    )
    doc_memory = Document(
        user_id=DEMO_USER_ID,
        category_id=cat_memory.id,
        title="Learning Science: Active Recall & The Ebbinghaus Forgetting Curve",
        filename="active_recall_ebbinghaus_dynamics.txt",
        file_type="txt",
        file_size_bytes=145000,
        processing_status="completed",
        is_demo=True,
        raw_text="Memory decay follows an exponential curve unless active retrieval practice intervenes to compound stability..."
    )
    db.add_all([doc_chem, doc_phys, doc_memory])
    db.commit()

    # Source chunks
    c1 = SourceChunk(
        document_id=doc_chem.id,
        chunk_index=0,
        page_number=1,
        content="Chemical Bonding encompasses Ionic bonds (transfer of electrons) and Covalent bonds (sharing of electron pairs). VSEPR theory dictates molecular geometry by minimizing valence shell electron pair repulsions.",
        char_count=215
    )
    c2 = SourceChunk(
        document_id=doc_phys.id,
        chunk_index=0,
        page_number=1,
        content="Newton's First Law defines inertia. The Second Law establishes that force equals the time rate of change of momentum (F = dp/dt = ma). The Third Law mandates equal and opposite action-reaction pairs across distinct bodies.",
        char_count=227
    )
    c3 = SourceChunk(
        document_id=doc_memory.id,
        chunk_index=0,
        page_number=1,
        content="The Ebbinghaus Forgetting Curve shows that up to 70% of new learning decays within 48 hours without retrieval. Spaced repetition expands memory stability exponentially over each successful recall milestone.",
        char_count=212
    )
    db.add_all([c1, c2, c3])
    db.commit()

    # 4. Canonical Approachable Topics
    t_chem_bond = Topic(
        user_id=DEMO_USER_ID,
        name="Chemical Bonding",
        canonical_name="Chemical Bonding",
        description="Attractive force binding atoms or ions to attain stable noble gas electronic configurations.",
        topic_type="concept",
        is_demo=True
    )
    t_vsepr = Topic(
        user_id=DEMO_USER_ID,
        name="VSEPR Theory & Molecular Geometry",
        canonical_name="VSEPR Theory",
        description="Predicts 3D molecular shapes by minimizing electrostatic repulsions between valence electron pairs.",
        topic_type="theory",
        is_demo=True
    )
    t_newton = Topic(
        user_id=DEMO_USER_ID,
        name="Newton's Laws of Motion",
        canonical_name="Newton's Laws of Motion",
        description="Three fundamental physical laws governing classical particle dynamics, force, and inertia.",
        topic_type="principle",
        is_demo=True
    )
    t_momentum = Topic(
        user_id=DEMO_USER_ID,
        name="Conservation of Momentum",
        canonical_name="Conservation of Momentum",
        description="Total momentum of an isolated system remains constant in the absence of net external forces.",
        topic_type="law",
        is_demo=True
    )
    t_active_recall = Topic(
        user_id=DEMO_USER_ID,
        name="Active Recall Mechanism",
        canonical_name="Active Recall",
        description="Deliberate cognitive retrieval practice forcing neural pathway reconstruction.",
        topic_type="concept",
        is_demo=True
    )
    t_spaced_rep = Topic(
        user_id=DEMO_USER_ID,
        name="Spaced Repetition Algorithm",
        canonical_name="Spaced Repetition",
        description="Scheduling reviews at calculated exponential intervals to maximize long-term memory stability.",
        topic_type="algorithm",
        is_demo=True
    )
    db.add_all([t_chem_bond, t_vsepr, t_newton, t_momentum, t_active_recall, t_spaced_rep])
    db.commit()

    # Document-Topic Associations
    db.add_all([
        DocumentTopic(document_id=doc_chem.id, topic_id=t_chem_bond.id, relevance_score=1.0),
        DocumentTopic(document_id=doc_chem.id, topic_id=t_vsepr.id, relevance_score=0.95),
        DocumentTopic(document_id=doc_phys.id, topic_id=t_newton.id, relevance_score=1.0),
        DocumentTopic(document_id=doc_phys.id, topic_id=t_momentum.id, relevance_score=0.9),
        DocumentTopic(document_id=doc_memory.id, topic_id=t_active_recall.id, relevance_score=1.0),
        DocumentTopic(document_id=doc_memory.id, topic_id=t_spaced_rep.id, relevance_score=0.95),
    ])

    # Meaningful Cross-Concept Relationships
    db.add_all([
        TopicRelationship(
            user_id=DEMO_USER_ID,
            source_topic_id=t_chem_bond.id,
            target_topic_id=t_vsepr.id,
            relationship_type="prerequisite_of",
            confidence=0.96,
            evidence_text="Understanding covalent electron sharing is prerequisite to calculating VSEPR lone pair and bond pair shapes."
        ),
        TopicRelationship(
            user_id=DEMO_USER_ID,
            source_topic_id=t_newton.id,
            target_topic_id=t_momentum.id,
            relationship_type="builds_on",
            confidence=0.94,
            evidence_text="Newton's Third Law (action-reaction) and Second Law directly derive the law of conservation of linear momentum."
        ),
        TopicRelationship(
            user_id=DEMO_USER_ID,
            source_topic_id=t_active_recall.id,
            target_topic_id=t_spaced_rep.id,
            relationship_type="builds_on",
            confidence=0.95,
            evidence_text="Spaced repetition systems rely on active retrieval drills rather than passive reading to calculate stability."
        ),
        TopicRelationship(
            user_id=DEMO_USER_ID,
            source_topic_id=t_chem_bond.id,
            target_topic_id=t_active_recall.id,
            relationship_type="relates_to",
            confidence=0.82,
            evidence_text="Formulas in chemical bonding (bond orders, hybridization formulas) require spaced recall to prevent retention decay."
        ),
    ])

    # 5. Memory States (realistic distribution)
    now = datetime.utcnow()
    m1 = TopicMemoryState(
        user_id=DEMO_USER_ID,
        topic_id=t_chem_bond.id,
        status="learned",
        stability=3.8,
        difficulty=0.3,
        recall_accuracy=0.88,
        total_reviews=3,
        successful_reviews=3,
        last_learned_at=now - timedelta(days=2),
        last_recalled_at=now - timedelta(days=1),
        next_review_at=now + timedelta(days=2, hours=14),
        estimated_retention=0.89
    )
    m2 = TopicMemoryState(
        user_id=DEMO_USER_ID,
        topic_id=t_vsepr.id,
        status="review_due",
        stability=1.7,
        difficulty=0.35,
        recall_accuracy=0.72,
        total_reviews=2,
        successful_reviews=1,
        last_learned_at=now - timedelta(days=3),
        last_recalled_at=now - timedelta(days=2),
        next_review_at=now - timedelta(hours=3), # Review Due!
        estimated_retention=0.69
    )
    m3 = TopicMemoryState(
        user_id=DEMO_USER_ID,
        topic_id=t_newton.id,
        status="learned",
        stability=5.5,
        difficulty=0.2,
        recall_accuracy=0.94,
        total_reviews=4,
        successful_reviews=4,
        last_learned_at=now - timedelta(days=4),
        last_recalled_at=now - timedelta(days=1),
        next_review_at=now + timedelta(days=4),
        estimated_retention=0.93
    )
    m4 = TopicMemoryState(
        user_id=DEMO_USER_ID,
        topic_id=t_momentum.id,
        status="unlearned",
        stability=1.0,
        difficulty=0.3,
        estimated_retention=1.0
    )
    m5 = TopicMemoryState(
        user_id=DEMO_USER_ID,
        topic_id=t_active_recall.id,
        status="learned",
        stability=6.0,
        difficulty=0.15,
        recall_accuracy=0.96,
        total_reviews=4,
        successful_reviews=4,
        last_learned_at=now - timedelta(days=5),
        last_recalled_at=now - timedelta(days=1),
        next_review_at=now + timedelta(days=5),
        estimated_retention=0.95
    )
    m6 = TopicMemoryState(
        user_id=DEMO_USER_ID,
        topic_id=t_spaced_rep.id,
        status="unlearned",
        stability=1.0,
        difficulty=0.3,
        estimated_retention=1.0
    )
    db.add_all([m1, m2, m3, m4, m5, m6])

    # 6. Flashcard Decks
    deck = FlashcardDeck(
        user_id=DEMO_USER_ID,
        title="Chemical Bonding & Molecular Shapes Drill",
        description="High-yield flashcards for molecular geometries, bond angles, and hybridization.",
        topic_id=t_vsepr.id,
        document_id=doc_chem.id
    )
    db.add(deck)
    db.commit()

    db.add_all([
        Flashcard(
            deck_id=deck.id,
            front="What is the molecular geometry and bond angle of Water (H₂O) according to VSEPR?",
            back="Bent (V-shaped) with an angle of ~104.5° due to strong lone pair-lone pair repulsion on the central Oxygen atom.",
            hint="2 bond pairs, 2 lone pairs",
            topic_id=t_vsepr.id
        ),
        Flashcard(
            deck_id=deck.id,
            front="How do you calculate Bond Order from Molecular Orbital Theory (MOT)?",
            back="Bond Order = (Nb - Na) / 2, where Nb is bonding electrons and Na is antibonding electrons.",
            hint="Bonding minus antibonding divided by 2",
            topic_id=t_chem_bond.id
        ),
        Flashcard(
            deck_id=deck.id,
            front="Why is Newton's Third Law action-reaction pair unable to cancel each other out?",
            back="Because the action and reaction forces act on two completely different objects, never on the same body.",
            hint="Consider the bodies receiving the forces",
            topic_id=t_newton.id
        )
    ])

    # 7. Study Note
    note = Note(
        user_id=DEMO_USER_ID,
        category_id=cat_chem.id,
        topic_id=t_vsepr.id,
        document_id=doc_chem.id,
        title="High-Yield Summary: VSEPR Rules & Molecular Geometries",
        content="""Key takeaways for Chemical Bonding & VSEPR:
1. Repulsion order: Lone Pair - Lone Pair > Lone Pair - Bond Pair > Bond Pair - Bond Pair.
2. NH3 (Ammonia): 3 bond pairs + 1 lone pair = Trigonal Pyramidal (~107°).
3. H2O (Water): 2 bond pairs + 2 lone pairs = Bent / Angular (~104.5°).
4. SF6 (Sulfur Hexafluoride): 6 bond pairs + 0 lone pairs = Octahedral (90°).
5. Always determine steric number (SN) first: SN = (Valence e- of central atom + Monovalent atoms - Charge) / 2.""",
        source_type="ai_tutor",
        tags=["chemistry", "cbse", "jee", "vsepr"]
    )
    db.add(note)

    # 8. Approachable Exam & Tasks
    exam = Exam(
        user_id=DEMO_USER_ID,
        subject="Chemistry & Physics Board & Pre-Competitive Midterms",
        exam_date=now + timedelta(days=5, hours=10),
        exam_time_str="09:30 AM",
        location="Examination Hall A",
        syllabus_summary="Chemical Bonding, VSEPR Theory, Newton's Laws of Motion, and Linear Momentum.",
        total_preparation_days=7
    )
    db.add(exam)
    db.commit()

    task1 = StudyTask(
        user_id=DEMO_USER_ID,
        exam_id=exam.id,
        topic_id=t_vsepr.id,
        title="⚡ Urgent Revision: VSEPR Molecular Shapes & Lone Pair Traps",
        description="Review bond angles of NH₃, H₂O, and PCl₅; complete 4-minute active recall drill.",
        scheduled_for=now + timedelta(hours=2),
        allocated_minutes=30,
        priority="high"
    )
    task2 = StudyTask(
        user_id=DEMO_USER_ID,
        exam_id=exam.id,
        topic_id=t_momentum.id,
        title="Deep Dive: Momentum Conservation & Collision Problems",
        description="Work through elastic vs inelastic collision problems and vector momentum conservation.",
        scheduled_for=now + timedelta(days=1, hours=3),
        allocated_minutes=45,
        priority="medium"
    )
    db.add_all([task1, task2])

    # 9. Proactive Notification
    notif = Notification(
        user_id=DEMO_USER_ID,
        topic_id=t_vsepr.id,
        title="⚡ Memory Review Due: VSEPR Theory & Shapes",
        message="Your estimated retention for VSEPR Theory has declined to 69%. A 3-minute quiz now will reset your forgetting curve before the exam in 5 days.",
        notification_type="review_due",
        action_url=f"/recall?topicId={t_vsepr.id}",
        dedup_key=f"demo_init_due_{t_vsepr.id}"
    )
    db.add(notif)
    db.commit()
