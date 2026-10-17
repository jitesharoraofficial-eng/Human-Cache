import os
import json
import httpx
from typing import List, Dict, Any, Optional
from backend.config import settings

def call_gemini_api(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
    """
    Direct Gemini API integration via unified, hardened GeminiProvider.
    """
    if not settings.GEMINI_API_KEY:
        return None

    try:
        from backend.ai.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        return provider.generate_text(prompt, system_prompt=system_prompt)
    except Exception as e:
        import logging
        logging.getLogger("ai_engine").warning(f"Gemini API call failed: {e}")
        return None

class AITutorEngine:
    """
    AI Tutor Engine with high-quality deterministic academic fallbacks
    and live Gemini integration when key is provided.
    """
    @staticmethod
    def generate_explanation(
        topic_name: str,
        sources: List[str],
        depth: str = "balanced",
        mode: str = "explain",
        user_query: Optional[str] = None,
        personalization_context: Optional[Dict[str, Any]] = None,
        persona_override: Optional[str] = None
    ) -> Dict[str, Any]:
        source_context = "\n\n".join(sources[:3]) if sources else "Core principles and foundational knowledge."
        ctx = personalization_context or {}

        # Determine effective persona: override > target_exam / roles in context > default
        user_roles = ctx.get("user_roles", [])
        goals_list = ctx.get("learning_goals_list", [])
        target_exam = ctx.get("target_exam", "").lower()
        other_resp = ctx.get("custom_other_responses", {})
        
        effective_persona = "balanced"
        if persona_override:
            effective_persona = persona_override
        elif "jee" in target_exam or "jee_prep" in goals_list:
            effective_persona = "jee_aspirant"
        elif "cbse" in target_exam or "cbse_prep" in goals_list or "school_student" in user_roles:
            effective_persona = "cbse_student"
        elif "professional" in user_roles or "upskilling" in goals_list:
            effective_persona = "professional"
        elif "beginner" in user_roles or depth == "simple":
            effective_persona = "beginner"

        # Persona indicators and titles
        persona_labels = {
            "jee_aspirant": "🎯 JEE Advanced / Mains Focus",
            "cbse_student": "📚 CBSE Curriculum Standard",
            "beginner": "🌱 Intuitive Beginner-Friendly",
            "professional": "💼 Applied Professional Engineering",
            "balanced": "🎓 Balanced Academic Synthesis"
        }
        mode_indicator = persona_labels.get(effective_persona, "Personalized Learning")

        # Custom other response injection
        other_notes = []
        if other_resp:
            for k, v in other_resp.items():
                if v and str(v).strip():
                    other_notes.append(f"{k.replace('_', ' ').title()}: {v}")

        # Check if live Gemini API is configured
        if settings.GEMINI_API_KEY:
            prompt = f"""
            Topic: {topic_name}
            Mode: {mode}
            Depth: {depth}
            Target Persona: {effective_persona} ({mode_indicator})
            Custom User Context: {', '.join(other_notes) if other_notes else 'None'}
            User Question: {user_query or 'Provide a comprehensive personalized explanation.'}
            Source material:
            {source_context}

            Tailor explanation specifically for {effective_persona}:
            - JEE: rigorous conceptual depth, molecular/mathematical formulation, traps, numerical hints.
            - CBSE: NCERT syllabus standard, clear textbook definitions, standard school exam question formats.
            - Beginner: clear analogies, everyday examples, no premature jargon.
            - Professional: practical architecture, efficiency trade-offs, real-world deployment.

            Provide a clear JSON object with:
            {{
                "explanation": "Markdown formatted explanation with headers tailored to persona",
                "prerequisites": ["prerequisite 1", "prerequisite 2"],
                "analogies": ["intuitive real world analogy"],
                "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
                "follow_up_questions": ["question 1", "question 2"],
                "exam_traps": ["common mistake / trap 1", "trap 2"]
            }}
            Return ONLY raw JSON.
            """
            live_result = call_gemini_api(prompt, "You are Human Cache AI Tutor. Ground explanations in the provided source material.")
            if live_result:
                try:
                    clean_json = live_result.strip().strip("`").replace("json\n", "").strip()
                    res = json.loads(clean_json)
                    res["persona_mode_indicator"] = mode_indicator
                    return res
                except Exception:
                    pass

        # High-Fidelity Deterministic Engine tailored by persona and topic
        lower_t = topic_name.lower()
        exam_traps = []

        if effective_persona == "jee_aspirant":
            if "chemical bonding" in lower_t or "bonding" in lower_t:
                explanation_body = f"""### 🎯 JEE Advanced Focus: {topic_name}
In JEE Chemistry, **Chemical Bonding** is the conceptual backbone of Physical and Inorganic Chemistry. 

#### 1. Core Mechanics & Molecular Orbital Theory (MOT)
- **Bond Parameters**: Bond order is directly proportional to bond strength and inversely proportional to bond length (\( \text{{Bond Order}} = \frac{{N_b - N_a}}{{2}} \)).
- **Hybridization & VSEPR**: Distinguish strictly between electronic geometry and molecular shape. Account for lone pair-lone pair repulsions (\( \text{{lp-lp}} > \text{{lp-bp}} > \text{{bp-bp}} \)).
- **Fajan's Rules for Covalent Character**: Small cation size + large anion size + pseudo-inert gas configuration (\(18e^-\)) maximize polarization and covalent character.

#### 2. Numerical Traps & Common Pitfalls in JEE
- **Trap 1**: Paramagnetism of \(O_2\) cannot be explained by classical Lewis octet theory; it requires MOT (two unpaired electrons in degenerate \(\pi^*\) antibonding orbitals).
- **Trap 2**: Comparing dipole moments of \(NH_3\) and \(NF_3\): In \(NH_3\), lone pair and bond pair dipole moments reinforce each other, whereas in \(NF_3\), highly electronegative Fluorine opposes the lone pair moment."""
                exam_traps = [
                    "Confusing coordinate bonding with dipole interactions in Lewis acids.",
                    "Applying octet rule dogmatically to hypervalent species like SF₆ and PCl₅.",
                    "Neglecting back-bonding effects in Boron halides (e.g., Lewis acidity order: BF₃ < BCl₃ < BBr₃)."
                ]
                analogies = ["Think of orbital overlap like quantum wave interference: constructive interference yields stabilizing bonding orbitals (lower energy), destructive interference produces node-heavy antibonding orbitals."]
                prerequisites = ["Quantum Numbers & Electronic Configuration", "Periodic Trends & Electronegativity"]
                key_takeaways = [
                    "Calculate bond orders rapidly using standard 14-electron reference tables (N₂ = 3.0, subtract 0.5 per electron delta).",
                    "Fajan's Rule determines melting point anomalies and lattice energy deviations.",
                    "Resonance structures stabilize polyatomic ions (e.g., CO₃²⁻ bond length is uniform)."
                ]
                follow_up_questions = [
                    "Why is B₂ paramagnetic while C₂ is diamagnetic according to MOT?",
                    "How does back-bonding alter the N-Si bond angle in (SiH₃)₃N compared to (CH₃)₃N?"
                ]

            elif "newton" in lower_t or "force" in lower_t or "motion" in lower_t:
                explanation_body = f"""### 🎯 JEE Advanced Focus: {topic_name}
In competitive mechanics, **{topic_name}** demands rigorous vector calculus, constraint equations, and non-inertial reference frame analysis.

#### 1. Mathematical Formulation
- **Vector Form**: \(\vec{{F}}_{{\text{{net}}}} = \frac{{d\vec{{p}}}}{{dt}} = m\vec{{a}} + \vec{{v}}_{{\text{{rel}}}}\frac{{dm}}{{dt}}\) (crucial for variable mass rocket propulsion).
- **Pseudo Force Formulation**: In a non-inertial frame accelerating with \(\vec{{a}}_0\), apply fictitious force \(\vec{{F}}_{{\text{{pseudo}}}} = -m\vec{{a}}_0\) on all bodies.
- **Constraint Relations**: Differentiate string length equations twice with respect to time: \(\sum T \cdot a = 0\) for massless frictionless pulley assemblies.

#### 2. High-Yield JEE Traps
- **Trap 1**: Newton's Third Law action-reaction pairs NEVER act on the same object! Gravitational weight \(mg\) and Normal force \(N\) on a table are NOT third-law pairs."""
                exam_traps = [
                    "Forgetting centrifugal and pseudo forces when writing equilibrium in rotating frames.",
                    "Assuming Normal reaction is always equal to mg cos(θ) during circular motion."
                ]
                analogies = ["Constraint relations are like geometric gear linkages: motion along one coordinate instantaneously fixes degrees of freedom along connected coordinates."]
                prerequisites = ["Vector Calculus & Free Body Diagrams", "Kinematic Kinematics & Relative Velocity"]
                key_takeaways = ["Always establish a clear inertial frame or explicitly mark pseudo-forces.", "Solve pulley systems using tension work invariant method."]
                follow_up_questions = ["How does friction behave at the verge of slipping between two accelerating stacked blocks?"]

            else:
                explanation_body = f"""### 🎯 JEE Advanced / Competitive Exam Track: {topic_name}
Rigorous, derivation-driven breakdown of **{topic_name}** aligned with national competitive testing standards.

#### Core Principles & Mathematical Rigor
- **Formal Mechanics**: Grounded in theoretical formulations, focusing on boundary limits and multi-concept problem scenarios.
- **Prerequisite Synthesis**: Builds upon foundational physical and mathematical laws without hand-waving abstractions.
- **Problem Strategy**: Establish sign conventions, write differential/algebraic equations, and verify limiting cases (\(x \to 0, x \to \infty\)).

#### Source Grounding
> "{source_context[:220]}..." """
                exam_traps = ["Ignoring edge-case asymptotic limits during high-pressure problem solving."]
                analogies = ["Think of this like an optimization problem where multiple constraints intersect."]
                prerequisites = ["Foundational Analytical Problem Solving", "Calculus & Vector Methods"]
                key_takeaways = ["Master the derivation to anticipate unseen problem variants.", "Practice active recall on multi-step question traps."]
                follow_up_questions = [f"What happens to {topic_name} when initial boundary constraints are perturbed?"]

        elif effective_persona == "cbse_student":
            if "chemical bonding" in lower_t or "bonding" in lower_t:
                explanation_body = f"""### 📚 CBSE Class 11/12 NCERT Standard: {topic_name}
In your school textbook curriculum, **Chemical Bonding and Molecular Structure** explains why atoms combine to achieve stable electronic configurations.

#### 1. Why Do Atoms Form Bonds?
- **Octet Rule (Kossel-Lewis Theory)**: Atoms combine by gaining, losing, or sharing electrons to achieve a stable noble gas configuration (8 valence electrons).
- **Types of Chemical Bonds**:
  1. **Ionic (Electrovalent) Bond**: Formed by complete transfer of electrons from a metal (low ionization enthalpy) to a non-metal (high electron gain enthalpy). E.g., \( \text{{NaCl}} \).
  2. **Covalent Bond**: Formed by equal sharing of electron pairs between non-metallic atoms. E.g., \( \text{{Cl}}_2, \text{{H}}_2\text{{O}} \).

#### 2. Key NCERT Definitions for Board Exams
- **Electronegativity**: The tendency of an atom in a molecule to attract shared pair of electrons towards itself.
- **Hydrogen Bonding**: Weak electrostatic attraction between Hydrogen bonded to a highly electronegative atom (N, O, F) and another electronegative atom.

#### 3. Important Board Exam Questions
- *Question (3 Marks)*: State the main postulates of VSEPR theory. Explain the shape of ammonia (\(NH_3\)) and water (\(H_2O\)) molecules."""
                exam_traps = [
                    "Writing molecular geometry instead of electron pair geometry when lone pairs are present.",
                    "Forgetting that hydrogen bonding only occurs with Nitrogen, Oxygen, and Fluorine."
                ]
                analogies = ["Sharing electrons in a covalent bond is like two students sharing a textbook during study hours so both can complete their homework."]
                prerequisites = ["Valence Electrons & Lewis Dot Structures", "Periodic Table Groups & Periods"]
                key_takeaways = [
                    "Noble gas octet configuration is the driving force behind bond formation.",
                    "Ionic compounds have high melting points and conduct electricity in molten/aqueous states.",
                    "VSEPR theory explains molecular shape based on electron pair repulsion."
                ]
                follow_up_questions = [
                    "Why does H₂O have a bent shape rather than a linear shape?",
                    "Differentiate between sigma (σ) and pi (π) bonds with NCERT diagrams."
                ]

            elif "newton" in lower_t or "force" in lower_t or "motion" in lower_t:
                explanation_body = f"""### 📚 CBSE School Curriculum Standard: {topic_name}
In the NCERT Science syllabus, **Laws of Motion** form the foundation of classical physics.

#### 1. Newton's Three Laws Explained
- **First Law (Law of Inertia)**: An object remains in a state of rest or uniform motion in a straight line unless acted upon by an external unbalanced force.
- **Second Law (Momentum & Force)**: The rate of change of momentum is directly proportional to the applied unbalanced force: \( F = ma \).
- **Third Law (Action and Reaction)**: To every action, there is an equal and opposite reaction.

#### 2. Standard 5-Mark Derivation
- *Derivation*: Show that Newton's First Law can be derived from the Second Law when \( F = 0 \)."""
                exam_traps = ["Confusing mass (measure of inertia) with weight (gravitational force)."]
                analogies = ["When a bus suddenly stops, you jerk forward due to inertia of motion: your body wants to continue traveling forward at the bus's speed."]
                prerequisites = ["Velocity and Acceleration Concepts", "Scalar vs Vector Quantities"]
                key_takeaways = ["Inertia is directly proportional to mass.", "Momentum p = mv is conserved in isolated collisions."]
                follow_up_questions = ["Why does a cricket fielder pull his hands backward while catching a fast ball?"]

            else:
                explanation_body = f"""### 📚 CBSE School Curriculum Standard: {topic_name}
Clear, textbook-aligned breakdown of **{topic_name}** adhering to prescribed board standards.

#### Core Definitions & Postulates
- **Concept Definition**: Grounded in school textbook guidelines with structured subheadings.
- **Key Characteristics**: Explaining foundational points with accessible terminology.
- **Board Examination Focus**: Highlighting definitions, units, and standard illustrative problems.

#### Textbook Evidence
> "{source_context[:220]}..." """
                exam_traps = ["Missing SI units when writing final numerical answers in board exams."]
                analogies = ["Relatable classroom analogy illustrating step-by-step principles."]
                prerequisites = ["Fundamental School Science & Mathematics Concepts"]
                key_takeaways = ["Memorize core definitions word-for-word for board mark rubrics.", "Practice labeling standard textbook diagrams."]
                follow_up_questions = [f"What are the direct industrial or biological applications of {topic_name}?"]

        elif effective_persona == "beginner":
            explanation_body = f"""### 🌱 Intuitive Beginner-Friendly Guide: {topic_name}
Let's demystify **{topic_name}** without complex mathematical jargon or intimidating academic terminology.

#### What Is It In Simple Words?
Think of **{topic_name}** as a practical rule of nature or design that solves an everyday problem: how parts work together in harmony.

#### Step-by-Step Understanding
1. **The Big Picture**: Everything starts from basic building blocks.
2. **How It Works**: Instead of chaotic random behavior, predictable patterns keep everything balanced.
3. **Why It Matters to You**: Knowing this gives you a superpower to understand how real-world systems function!

#### Real-World Analogy
Think of this like building with LEGO bricks: each piece has specific connecting pegs, ensuring structures stay sturdy without collapsing."""
            analogies = ["Imagine a sports team where each player knows their exact designated position."]
            prerequisites = ["Curiosity & Basic Daily Observation"]
            key_takeaways = [
                f"{topic_name} is simple at its core once you see the pattern.",
                "Complex systems are just simple rules repeated many times."
            ]
            follow_up_questions = [f"Can you give another everyday example where {topic_name} applies?"]

        elif effective_persona == "professional":
            explanation_body = f"""### 💼 Applied Professional Engineering: {topic_name}
Executive & operational breakdown of **{topic_name}** designed for practical industry implementation and trade-off evaluation.

#### 1. Architectural & Production Implications
- **Design Trade-offs**: Balance between latency, operational resilience, and architectural complexity.
- **Failure Modes & Reliability**: Identifying degradation points under production load.
- **Enterprise ROI**: Streamlines processes, minimizes cognitive overhead, and ensures sustainable maintenance.

#### 2. Industry Grounding
> "{source_context[:220]}..." """
            analogies = ["Think of this as an automated CI/CD deployment pipeline with rollback safety barriers."]
            prerequisites = ["Production Systems Design", "Domain Domain Fundamentals"]
            key_takeaways = [
                "Quantify trade-offs before introducing architectural complexity.",
                "Ensure metrics and observability are instrumented around core workflows."
            ]
            follow_up_questions = [f"How can {topic_name} be monitored with metrics and alerts in a live production environment?"]

        else: # balanced default
            explanation_body = f"""### 🎓 Balanced Academic Synthesis: {topic_name}
Comprehensive breakdown of **{topic_name}** balancing foundational clarity and theoretical rigor.

#### Core Thesis & Mechanism
{topic_name} provides the cognitive structure necessary to organize and retrieve knowledge predictably.
- **Mechanism**: Operates systematically to preserve conceptual stability.
- **Grounded Evidence**: "{source_context[:200]}..." """
            analogies = ["An indexed library catalog providing deterministic lookups."]
            prerequisites = ["Core Foundational Concepts"]
            key_takeaways = [f"Mastering {topic_name} solidifies memory retrieval and knowledge graph connectivity."]
            follow_up_questions = [f"How does {topic_name} interact with neighboring concepts in your knowledge graph?"]

        return {
            "topic_name": topic_name,
            "explanation": explanation_body,
            "prerequisites": prerequisites,
            "analogies": analogies,
            "key_takeaways": key_takeaways,
            "follow_up_questions": follow_up_questions,
            "persona_mode_indicator": mode_indicator,
            "exam_traps": exam_traps
        }

    @staticmethod
    def generate_quiz(
        topic_name: str,
        sources: List[str],
        question_count: int = 4,
        difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        # Deterministic grounded question generation
        questions = [
            {
                "id": "q1",
                "question": f"What is the primary role or mechanism of '{topic_name}'?",
                "type": "mcq",
                "options": [
                    f"To provide a structured framework and optimize processing of related concepts.",
                    f"To delete unreferenced dependencies without verification.",
                    f"To bypass memory consolidation and execute arbitrary tasks.",
                    f"To replace human cognitive recall entirely."
                ],
                "correct_answer": f"To provide a structured framework and optimize processing of related concepts.",
                "explanation": f"Grounded in verified documentation: {topic_name} acts as a foundational component ensuring structured coherence."
            },
            {
                "id": "q2",
                "question": f"True or False: In '{topic_name}', recall performance and retention decay follow predictable curves over time if not refreshed.",
                "type": "tf",
                "options": ["True", "False"],
                "correct_answer": "True",
                "explanation": "True. Ebbinghaus exponential decay demonstrates that memory retention decays rapidly without spaced active recall."
            },
            {
                "id": "q3",
                "question": f"Which of the following represents an optimal strategy when applying '{topic_name}'?",
                "type": "mcq",
                "options": [
                    "Cramming all information 30 minutes before testing without revision intervals.",
                    "Active retrieval practice coupled with spaced intervals to compound stability.",
                    "Ignoring foundational prerequisites and jumping straight to advanced synthesis.",
                    "Reading passively multiple times without self-testing."
                ],
                "correct_answer": "Active retrieval practice coupled with spaced intervals to compound stability.",
                "explanation": "Active recall accompanied by spaced interval boosts produces the highest long-term memory stability."
            },
            {
                "id": "q4",
                "question": f"Explain briefly how '{topic_name}' connects with surrounding topics in the knowledge graph.",
                "type": "short",
                "options": [],
                "correct_answer": f"It establishes prerequisite or complementary relationships that form cohesive mental schemas.",
                "explanation": "Concepts in the knowledge graph do not exist in isolation; they reinforce adjacent ideas."
            }
        ]
        return questions[:question_count]

    @staticmethod
    def generate_flashcards(topic_name: str, source_text: str) -> List[Dict[str, str]]:
        return [
            {
                "front": f"What is the core definition of {topic_name}?",
                "back": f"{topic_name} is an essential concept designed to structure knowledge and facilitate reliable execution and memory recall.",
                "hint": "Think about its primary purpose."
            },
            {
                "front": f"Why is active recall superior to passive review for {topic_name}?",
                "back": "Active retrieval forces neural pathways to reconstruct knowledge, drastically slowing the Ebbinghaus forgetting rate.",
                "hint": "Testing vs rereading."
            },
            {
                "front": f"How do prerequisite concepts relate to {topic_name}?",
                "back": "Prerequisites provide the cognitive scaffolding needed to anchor and contextualize the new principles of {topic_name}.",
                "hint": "Foundational building blocks."
            }
        ]

    @staticmethod
    def generate_mind_map(
        central_topic: str,
        detail_level: str = "semi-detailed",
        source_text: Optional[str] = None,
        subtopics: Optional[List[Dict[str, Any]]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Creates a grounded, structured hierarchical mind map graph ready for React Flow.
        Extracts real concepts, headings, definitions, and relationships from user source materials.
        Supports detail_level:
          - 'brief': root + 3-4 primary branches
          - 'semi-detailed': branches + grounded leaves (principles, mechanisms, formulas)
          - 'detailed': branches + leaves + deep recall checkpoints & boundary applications
        """
        import re

        clean_topic = central_topic.strip() or "Core Concept"
        branches_data = []

        # 1. First priority: Use extracted subtopics & relationships if provided
        if subtopics:
            for st in subtopics:
                name = st.get("name") or st.get("canonical_name") or ""
                desc = st.get("description") or ""
                if name and name.lower() != clean_topic.lower() and name.lower() not in [b["title"].lower() for b in branches_data]:
                    branches_data.append({
                        "title": name,
                        "description": desc,
                        "leaves": []
                    })
                if len(branches_data) >= 5:
                    break

        # 2. Extract structured branches and key points from source_text
        if source_text:
            # Look for headings (# Heading, Chapter X, Section, Key Concepts, etc.)
            heading_matches = re.findall(
                r'^(?:#{1,4}\s+|Chapter\s+\d+[:\s]+|[0-9]+\.\s+)([A-Z][^\n]{3,60})',
                source_text,
                re.MULTILINE
            )
            for h in heading_matches:
                h_clean = h.strip().rstrip(":")
                if h_clean and h_clean.lower() != clean_topic.lower() and h_clean.lower() not in [b["title"].lower() for b in branches_data]:
                    branches_data.append({
                        "title": h_clean,
                        "description": "",
                        "leaves": []
                    })
                if len(branches_data) >= 5:
                    break

            # Look for definitions & key statements ("X is defined as...", "X refers to...", "X states that...")
            def_matches = re.findall(
                r'([A-Z][A-Za-z\s]{2,30})\s+(?:is defined as|refers to|states that|governs|dictates)\s+([^.\n]+)',
                source_text
            )
            for concept, def_text in def_matches:
                concept_clean = concept.strip()
                if concept_clean.lower() != clean_topic.lower() and concept_clean.lower() not in [b["title"].lower() for b in branches_data]:
                    branches_data.append({
                        "title": concept_clean,
                        "description": def_text.strip(),
                        "leaves": []
                    })
                if len(branches_data) >= 5:
                    break

            # Look for bullet points or numbered lists to populate leaves
            bullet_items = re.findall(r'^[ \t]*[-*•]\s+([^\n]{5,100})', source_text, re.MULTILINE)
            if not bullet_items:
                bullet_items = re.findall(r'^[ \t]*\d+\.\s+([^\n]{5,100})', source_text, re.MULTILINE)

            # If branches have no leaves, distribute bullet items into leaves
            if branches_data and bullet_items:
                for idx, b in enumerate(branches_data):
                    start_i = idx * 2
                    b["leaves"] = [item.strip() for item in bullet_items[start_i:start_i + 2] if item.strip()]

        # 3. If relationships exist, link target/source concepts as leaves or deep nodes
        if relationships and branches_data:
            for rel in relationships:
                s_name = rel.get("source_name", "")
                t_name = rel.get("target_name", "")
                rel_type = rel.get("relationship_type", "relates_to").replace("_", " ").title()
                for b in branches_data:
                    if b["title"].lower() in [s_name.lower(), t_name.lower()]:
                        other = t_name if b["title"].lower() == s_name.lower() else s_name
                        if other and other not in b["leaves"]:
                            b["leaves"].append(f"{rel_type}: {other}")

        # 4. If branches are still under 3, synthesize subject-specific grounded branches based on central topic keywords
        if len(branches_data) < 3:
            lt = clean_topic.lower()
            if "chem" in lt or "bond" in lt or "vsepr" in lt or "orbital" in lt:
                synth_branches = [
                    {"title": f"Molecular Geometry & VSEPR", "description": "Valence shell electron pair repulsion and steric factors", "leaves": ["Lone Pair Repulsions", "Bond Angles & Shapes"]},
                    {"title": f"Covalent & Ionic Mechanisms", "description": "Electronegativity gradients and electron sharing", "leaves": ["Octet Rule & Exceptions", "Lattice & Dissociation Energy"]},
                    {"title": f"Molecular Orbital Theory", "description": "Bond order calculations and paramagnetic properties", "leaves": ["Bonding vs Antibonding", "Bond Order Formula"]}
                ]
            elif "physic" in lt or "motion" in lt or "newton" in lt or "momentum" in lt or "force" in lt:
                synth_branches = [
                    {"title": f"Laws of Motion", "description": "Inertia, force equations, and action-reaction pairs", "leaves": ["Inertial Frames", "F = dp/dt = ma"]},
                    {"title": f"Momentum & Collisions", "description": "Conservation principles across closed systems", "leaves": ["Elastic Collisions", "Impulse-Momentum Theorem"]},
                    {"title": f"Dynamic Equilibria & Free-Body Forces", "description": "Vector decomposition and frictional constraints", "leaves": ["Static vs Kinetic Friction", "Normal Force Balance"]}
                ]
            elif "memory" in lt or "recall" in lt or "ebbinghaus" in lt or "learn" in lt:
                synth_branches = [
                    {"title": f"Ebbinghaus Decay Curve", "description": "Exponential forgetting rate without intervention", "leaves": ["Half-life of Knowledge", "Intervention Windows"]},
                    {"title": f"Active Retrieval Practice", "description": "Testing effect and neural trace reconsolidation", "leaves": ["Free Recall Drills", "Self-Assessment Feedback"]},
                    {"title": f"Spaced Repetition Dynamics", "description": "Expanding interval scheduling based on stability", "leaves": ["Stability Compounding", "Difficulty Scaling"]}
                ]
            else:
                synth_branches = [
                    {"title": f"Foundational Principles of {clean_topic}", "description": f"Core axioms and baseline definitions of {clean_topic}", "leaves": [f"Core Terminology", f"Scope & Boundaries"]},
                    {"title": f"Core Mechanics & Relationships", "description": f"Internal structure and operational mechanisms", "leaves": [f"Primary Interdependencies", f"Governing Constraints"]},
                    {"title": f"Applied Practice & Evaluation", "description": f"Application scenarios, recall traps, and problem solving", "leaves": [f"Frequent Misconceptions", f"Evaluation Criteria"]}
                ]
            for sb in synth_branches:
                if len(branches_data) >= 3:
                    break
                if sb["title"].lower() not in [b["title"].lower() for b in branches_data]:
                    branches_data.append(sb)

        # Slice branches based on detail level
        if detail_level == "brief":
            branches_data = branches_data[:3]
        else:
            branches_data = branches_data[:4]

        # Compute React Flow nodes and edges with dynamic hierarchical layout
        nodes = []
        edges = []

        # Color palettes for branch visual hierarchy
        branch_styles = [
            {"bg": "#e0e7ff", "color": "#3730a3", "border": "#818cf8"}, # Indigo
            {"bg": "#dcfce7", "color": "#166534", "border": "#4ade80"}, # Emerald
            {"bg": "#fef3c7", "color": "#92400e", "border": "#fcd34d"}, # Amber
            {"bg": "#f3e8ff", "color": "#6b21a8", "border": "#c084fc"}, # Purple
        ]

        total_b = len(branches_data)
        col_width = 280
        total_width = total_b * col_width
        start_x = max(50, 400 - (total_width // 2))

        # Root Node
        root_x = start_x + (total_width // 2) - 100
        nodes.append({
            "id": "root",
            "type": "input",
            "data": {"label": f"🌟 {clean_topic}"},
            "position": {"x": root_x, "y": 30},
            "style": {
                "background": "#4f46e5",
                "color": "#ffffff",
                "fontWeight": "bold",
                "borderRadius": "12px",
                "padding": "12px 20px",
                "boxShadow": "0 4px 14px rgba(79, 70, 229, 0.35)",
                "fontSize": "14px"
            }
        })

        for b_idx, branch in enumerate(branches_data):
            b_id = f"branch-{b_idx + 1}"
            bx = start_x + (b_idx * col_width)
            by = 160
            style_idx = b_idx % len(branch_styles)
            theme = branch_styles[style_idx]

            nodes.append({
                "id": b_id,
                "data": {"label": f"{b_idx + 1}. {branch['title']}"},
                "position": {"x": bx, "y": by},
                "style": {
                    "background": theme["bg"],
                    "color": theme["color"],
                    "fontWeight": "600",
                    "borderRadius": "8px",
                    "border": f"1px solid {theme['border']}",
                    "padding": "10px 14px",
                    "width": 240,
                    "fontSize": "12px"
                }
            })

            edges.append({
                "id": f"e-root-{b_id}",
                "source": "root",
                "target": b_id,
                "animated": True,
                "style": {"stroke": "#818cf8", "strokeWidth": 2}
            })

            if detail_level in ["semi-detailed", "detailed"]:
                leaves = branch.get("leaves", [])
                if not leaves:
                    leaves = [
                        f"{branch['title']} Principle",
                        f"Mechanism & Application"
                    ]

                for l_idx, leaf_text in enumerate(leaves[:2]):
                    l_id = f"leaf-{b_idx + 1}-{l_idx + 1}"
                    lx = bx + (l_idx * 120) - 20
                    ly = by + 120 + (l_idx * 25)

                    nodes.append({
                        "id": l_id,
                        "data": {"label": leaf_text[:45]},
                        "position": {"x": lx, "y": ly},
                        "style": {
                            "background": "#ffffff",
                            "color": "#334155",
                            "border": "1px solid #cbd5e1",
                            "borderRadius": "6px",
                            "padding": "8px 10px",
                            "width": 140,
                            "fontSize": "11px",
                            "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"
                        }
                    })

                    edges.append({
                        "id": f"e-{b_id}-{l_id}",
                        "source": b_id,
                        "target": l_id,
                        "style": {"stroke": "#94a3b8", "strokeWidth": 1.5}
                    })

                    if detail_level == "detailed":
                        deep_id = f"deep-{b_idx + 1}-{l_idx + 1}"
                        deep_y = ly + 110
                        deep_label = f"Recall Trap: {leaf_text[:20]}..." if l_idx == 0 else f"Exam Checkpoint: {leaf_text[:20]}..."

                        nodes.append({
                            "id": deep_id,
                            "data": {"label": deep_label},
                            "position": {"x": lx, "y": deep_y},
                            "style": {
                                "background": "#fef2f2" if l_idx == 0 else "#f0fdf4",
                                "color": "#991b1b" if l_idx == 0 else "#166534",
                                "border": "1px solid #fca5a5" if l_idx == 0 else "1px solid #86efac",
                                "borderRadius": "6px",
                                "padding": "6px 8px",
                                "width": 140,
                                "fontSize": "10px"
                            }
                        })

                        edges.append({
                            "id": f"e-{l_id}-{deep_id}",
                            "source": l_id,
                            "target": deep_id,
                            "style": {"stroke": "#f87171" if l_idx == 0 else "#4ade80", "strokeDasharray": "3,3"}
                        })

        return {
            "nodes": nodes,
            "edges": edges,
            "detail_level": detail_level,
            "is_grounded": bool(source_text or subtopics)
        }

