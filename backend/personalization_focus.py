"""
Dynamic Dashboard Cognitive Focus & Personalization Engine for Human Cache.

Generates the authenticated user's dashboard greeting and cognitive focus
strictly from their persisted preferences and genuine learning activity.

Guarantees:
1. No fabricated claims (no 'High-Yield Revision' without source/exam context).
2. Dynamic synthesis across academic streams, degrees, exams, professional education,
   personal development, multiple interests, custom subjects, and empty states.
3. Strict user isolation — never leaks demo preferences or hardcoded strings.
"""

from typing import Optional, List, Dict, Any


GOAL_TITLES = {
    "commerce_business": "Business Management & Commerce",
    "technical_craft": "Software & Engineering Tech",
    "creative_arts": "Humanities & Creative Arts",
    "personal_growth": "Personal Development & Skills",
    "college_university": "College & University Degree",
    "competitive_exam": "Competitive Exam Preparation",
    "school_studies": "School & Board Academics",
    "academic_research": "Academic Research & Synthesis",
    "lifelong_curiosity": "Curiosity & Lifelong Learning",
}

STREAM_KEYWORDS = [
    # Law & Governance
    (["law", "legal", "ll.b", "llb", "clat", "judiciary", "jurisprudence"],
     "Legal Studies",
     "Upload your materials to organize legal concepts and build recall practice."),
    
    # Commerce / Business / Finance
    (["b.com", "bcom", "commerce", "business", "bba", "mba", "finance", "accountancy", "taxation"],
     "Business Management & Commerce",
     "Upload your notes to start building your personal knowledge graph."),
    
    # Engineering & Technology
    (["b.tech", "btech", "engineering", "computer science", "software", "programming", "algorithms", "data science"],
     "Engineering & Technology",
     "Upload your technical documents, notes, and problem sets to start building your personal knowledge graph."),
     
    # Medical & Healthcare
    (["mbbs", "medicine", "medical", "neet", "anatomy", "clinical", "nursing", "pharmacy"],
     "Medical & Healthcare Studies",
     "Upload your clinical notes and slides to organize concepts and build recall practice."),
     
    # Humanities & History
    (["history", "humanities", "political science", "philosophy", "sociology", "literature"],
     "History & Humanities",
     "Upload your materials to organize historical concepts and build recall practice."),
     
    # Personal Skills
    (["public speaking", "productivity", "personal growth", "financial literacy", "creative writing"],
     "Personal Development & Practical Skills",
     "Upload your guides or notes to build your personal knowledge base."),
     
    # Natural Sciences
    (["physics", "chemistry", "biology", "mathematics", "science"],
     "Scientific Fundamentals",
     "Upload your study materials to organize concepts and prepare for active recall.")
]


def derive_preference_learning_focus(prefs: Optional[Any]) -> Dict[str, str]:
    """
    Derives cognitive learning focus strictly from the user's saved preferences
    when no prior learning activity exists (clean onboarding state).
    """
    if not prefs:
        return {
            "focus_title": "Your learning journey starts here",
            "focus_prompt": "Upload your first resource to build your personal knowledge graph.",
            "full_message": "Your learning journey starts here. Upload your first resource to build your personal knowledge graph."
        }

    context = prefs.learning_context or {}
    if not isinstance(context, dict):
        context = {}

    degree = (context.get("college_degree") or "").strip()
    field = (context.get("college_field") or "").strip()
    p_role = (context.get("profession_role") or "").strip()
    p_industry = (context.get("profession_industry") or "").strip()
    p_skills = (context.get("profession_skills") or "").strip()
    r_field = (context.get("research_field") or "").strip()
    r_topics = (context.get("research_topics") or "").strip()

    target_exam = (prefs.target_exam or "").strip()
    curriculum = (prefs.curriculum or "").strip()
    roles = prefs.user_roles or []
    goals_list = prefs.learning_goals_list or []
    subjects = prefs.subjects_of_interest or []
    custom_subjs = prefs.custom_subjects or []
    others = prefs.custom_other_responses or {}
    if not isinstance(others, dict):
        others = {}
    goal_other = others.get("goal_other", "").strip()
    exam_other = others.get("exam_other", "").strip()
    role_other = others.get("role_other", "").strip()

    if target_exam.lower() == "other" and exam_other:
        target_exam = exam_other

    # Check if user has explicit target exam and is in an exam preparation context
    has_exam_intent = bool(
        target_exam
        and target_exam.lower() not in ["", "none", "n/a"]
        and ("competitive_aspirant" in roles or "competitive_exam" in goals_list or not roles)
    )

    # 1. Competitive Exam Intent
    if has_exam_intent:
        tx_lower = target_exam.lower()
        if "jee" in tx_lower:
            focus_title = "JEE Main & Advanced"
            focus_prompt = "Upload your study materials to organize concepts and prepare for active recall."
        elif "neet" in tx_lower:
            focus_title = "NEET Medical Preparation"
            focus_prompt = "Upload your biology and chemistry notes to prepare for active recall."
        elif "clat" in tx_lower or "law" in tx_lower:
            focus_title = "Legal Studies"
            focus_prompt = "Upload your materials to organize legal concepts and build recall practice."
        elif "upsc" in tx_lower or "civil services" in tx_lower:
            focus_title = "UPSC Civil Services"
            focus_prompt = "Upload your syllabus notes to organize key concepts and prepare for active recall."
        elif "ca" in tx_lower or "cfa" in tx_lower:
            focus_title = target_exam
            focus_prompt = "Upload your study materials to organize accounting and financial concepts."
        else:
            focus_title = target_exam
            focus_prompt = "Upload your study materials to organize concepts and prepare for active recall."
        
        return {
            "focus_title": focus_title,
            "focus_prompt": focus_prompt,
            "full_message": f"Your learning focus: {focus_title}. {focus_prompt}"
        }

    # 2. College Degree & Specialization Context (e.g. B.Com, LL.B, B.Tech, History)
    if degree or field:
        combo_text = f"{degree} {field}".lower()
        if any(k in combo_text for k in ["b.com", "bcom", "commerce", "business management", "bba", "finance", "accounting"]):
            focus_title = "Business Management & Commerce"
            focus_prompt = "Upload your notes to start building your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif any(k in combo_text for k in ["law", "ll.b", "llb", "legal", "jurisprudence"]):
            focus_title = "Legal Studies"
            focus_prompt = "Upload your materials to organize legal concepts and build recall practice."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Your learning focus: {focus_title}. {focus_prompt}"
            }
        # Engineering & Technology degrees
        elif any(k in combo_text for k in ["b.tech", "btech", "b.e", "be", "engineering"]):
            if any(k in combo_text for k in ["computer science", "cs", "cse", "software", "it", "information technology"]):
                focus_title = "Computer Science & Engineering"
            elif any(k in combo_text for k in ["mechanical", "mech"]):
                focus_title = "Mechanical Engineering"
            elif any(k in combo_text for k in ["electrical", "electronics", "ece", "eee"]):
                focus_title = "Electrical & Electronics Engineering"
            elif any(k in combo_text for k in ["civil"]):
                focus_title = "Civil Engineering"
            elif field:
                focus_title = f"Engineering ({field.title()})"
            else:
                focus_title = "Engineering & Technology Foundations"

            focus_prompt = "Upload your technical documents, coursework, and problem sets to build your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif any(k in combo_text for k in ["history", "arts", "humanities", "literature"]):
            focus_title = "History & Humanities"
            focus_prompt = "Upload your materials to organize historical concepts and build recall practice."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Your learning focus: {focus_title}. {focus_prompt}"
            }
        else:
            if degree and field:
                focus_title = f"{degree}: {field}"
            elif degree:
                focus_title = f"{degree} Studies"
            else:
                focus_title = f"{field} Studies"
            focus_prompt = "Upload your notes to start building your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }

    # 3. Custom Subjects entered by user
    if custom_subjs:
        if len(custom_subjs) == 1:
            focus_title = custom_subjs[0]
        else:
            focus_title = f"{custom_subjs[0]} & {custom_subjs[1]}"
        focus_prompt = "Upload your resources to start building your personal knowledge graph."
        return {
            "focus_title": focus_title,
            "focus_prompt": focus_prompt,
            "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
        }

    # 4. Multi-interest / Multi-goal Synthesis
    if len(goals_list) > 1:
        labels = []
        for g in goals_list:
            if g in GOAL_TITLES and g not in ["college_university", "lifelong_curiosity"]:
                if g == "commerce_business":
                    labels.append("Business Management")
                elif g == "technical_craft":
                    labels.append("Technology")
                elif g == "creative_arts":
                    labels.append("Humanities")
                elif g == "personal_growth":
                    labels.append("Personal Skills")
                elif g == "school_studies":
                    labels.append("School Academics")
                elif g == "academic_research":
                    labels.append("Research")
                elif g == "competitive_exam":
                    labels.append("Exam Preparation")
        
        if len(labels) == 2:
            focus_title = f"{labels[0]} & {labels[1]}"
        elif len(labels) > 2:
            focus_title = f"{labels[0]}, {labels[1]} & {labels[2]}"
        else:
            focus_title = "Multi-Disciplinary Studies"

        focus_prompt = "Upload your materials to start building your multi-disciplinary knowledge graph."
        return {
            "focus_title": focus_title,
            "focus_prompt": focus_prompt,
            "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
        }

    # 5. Single Goal Selection
    if len(goals_list) == 1:
        g = goals_list[0]
        if g == "commerce_business":
            focus_title = "Business Management & Commerce"
            focus_prompt = "Upload your notes to start building your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "creative_arts":
            focus_title = "Humanities & Creative Arts"
            focus_prompt = "Upload your materials to organize creative concepts and build recall practice."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "personal_growth":
            focus_title = "Personal Development & Skills"
            focus_prompt = "Upload your notes or guides to build your personal knowledge base."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "technical_craft":
            focus_title = "Software & Engineering Tech"
            focus_prompt = "Upload your technical documents and code notes to start building your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "school_studies":
            curriculum_str = f" ({curriculum})" if curriculum else ""
            focus_title = f"School & Board Academics{curriculum_str}"
            focus_prompt = "Upload your textbook chapters and class notes to organize your study graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "academic_research":
            focus_title = "Academic Research & Synthesis"
            focus_prompt = "Upload your papers and research notes to map citations and concepts."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "lifelong_curiosity":
            focus_title = "Curiosity & Lifelong Learning"
            focus_prompt = "Upload your reading notes to build your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }
        elif g == "other" and goal_other:
            focus_title = goal_other
            focus_prompt = "Upload your materials to start building your personal knowledge graph."
            return {
                "focus_title": focus_title,
                "focus_prompt": focus_prompt,
                "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
            }

    # 6. Selected Subjects of Interest
    if subjects:
        subj_text = " ".join(subjects).lower()
        for keywords, title, prompt in STREAM_KEYWORDS:
            if any(k in subj_text for k in keywords):
                return {
                    "focus_title": title,
                    "focus_prompt": prompt,
                    "full_message": f"Today's learning focus: {title}. {prompt}"
                }
        
        focus_title = subjects[0] if len(subjects) == 1 else f"{subjects[0]} & {subjects[1]}"
        focus_prompt = "Upload your study notes to start building your personal knowledge graph."
        return {
            "focus_title": focus_title,
            "focus_prompt": focus_prompt,
            "full_message": f"Today's learning focus: {focus_title}. {focus_prompt}"
        }

    # 7. Fallback when user has no preferences
    return {
        "focus_title": "Your learning journey starts here",
        "focus_prompt": "Upload your first resource to build your personal knowledge graph.",
        "full_message": "Your learning journey starts here. Upload your first resource to build your personal knowledge graph."
    }


def generate_dashboard_focus(
    prefs: Optional[Any],
    topics: list,
    mem_states: list,
    upcoming_exams: list,
    total_docs: int
) -> Dict[str, str]:
    """
    Synthesizes the dashboard focus, distinguishing between:
    A. User preference-based learning focus (when empty account / 0 docs).
    B. Actual activity-based revision recommendation (when user has genuine documents, topics, or quizzes).
    """
    # STAGE 4: Prevent fabricated personalization.
    # If the user has NOT uploaded any content, show preference-based focus, never fabricated revision.
    if total_docs == 0 or not topics:
        return derive_preference_learning_focus(prefs)

    # User has real uploaded content and topics!
    # Check for genuine review-due or overdue topics
    review_due = [m for m in mem_states if m.status in ["review_due", "overdue"]]
    if review_due:
        review_due.sort(key=lambda m: getattr(m, "estimated_retention", 0.0))
        target = review_due[0]
        topic_name = target.topic.canonical_name if getattr(target, "topic", None) else "Concept"
        return {
            "focus_title": f"Active Recall: {topic_name}",
            "focus_prompt": f"Reinforce your memory trace for {topic_name} to stabilize long-term retention.",
            "full_message": f"Today's cognitive focus is Active Recall: {topic_name}. Reinforce your memory trace to stabilize long-term retention."
        }

    # Check for relearning or low-retention topics
    relearn = [m for m in mem_states if m.status == "relearning" or getattr(m, "estimated_retention", 1.0) < 0.65]
    if relearn:
        relearn.sort(key=lambda m: getattr(m, "estimated_retention", 0.0))
        target = relearn[0]
        topic_name = target.topic.canonical_name if getattr(target, "topic", None) else "Concept"
        return {
            "focus_title": f"Concept Reinforcement: {topic_name}",
            "focus_prompt": f"Retention has declined for {topic_name}. An active recall drill will restore stability.",
            "full_message": f"Today's cognitive focus is Concept Reinforcement: {topic_name}. An active recall drill will restore stability."
        }

    # Check for unlearned topics
    unlearned = [m for m in mem_states if m.status == "unlearned"]
    if unlearned:
        target = unlearned[0]
        topic_name = target.topic.canonical_name if getattr(target, "topic", None) else "Concept"
        return {
            "focus_title": f"Explore {topic_name}",
            "focus_prompt": f"Build conceptual foundations for {topic_name} with flashcards and notes.",
            "full_message": f"Today's cognitive focus is {topic_name}. Build conceptual foundations with flashcards and notes."
        }

    # Check for upcoming exam with saved date
    if upcoming_exams:
        exam = upcoming_exams[0]
        return {
            "focus_title": f"{exam.subject} Preparation",
            "focus_prompt": f"Exam on {exam.exam_date.strftime('%b %d')}. Complete your scheduled study tasks.",
            "full_message": f"Today's cognitive focus is {exam.subject} Preparation. Complete your scheduled study tasks."
        }

    # Stable learned topics
    topic_name = topics[0].canonical_name if getattr(topics[0], "canonical_name", None) else "Concept"
    return {
        "focus_title": f"Mastery Review: {topic_name}",
        "focus_prompt": f"Concepts are stable. Test your recall on {topic_name} to maintain retention.",
        "full_message": f"Today's cognitive focus is Mastery Review: {topic_name}. Test your recall to maintain retention."
    }
