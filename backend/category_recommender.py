"""
AI Category Recommendation Service for Captures.

Analyzes captured content against the user's real database categories using Gemini
(with deterministic fallback) and returns:
- recommended_category_id: ID of existing category if strong match
- recommended_category_name: Name of category (existing or suggested new)
- confidence: heuristic confidence score (0.0 to 1.0)
- explanation: grounded pedagogical reason
- is_new_category: bool indicating whether a new category was suggested
- alternative_categories: other potential matching categories
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.models import Category
from backend.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class CategoryRecommendationSchema(BaseModel):
    recommended_category_name: str = Field(description="Name of the best-fitting category, either from existing categories or a sensible new one.")
    matches_existing: bool = Field(description="True if recommended category matches one of the user's existing categories.")
    confidence: float = Field(default=0.85, description="Heuristic confidence from 0.0 to 1.0.")
    explanation: str = Field(description="Brief explanation of why this category fits the content.")
    alternative_names: List[str] = Field(default_factory=list, description="Up to 2 alternative category names.")


def recommend_category_for_content(
    db: Session,
    user_id: str,
    title: str,
    content_text: str,
    gemini_provider: Optional[GeminiProvider] = None
) -> Dict[str, Any]:
    """
    Evaluates captured material and provides an intelligent category recommendation.
    Prioritizes matching the user's existing categories.
    """
    user_categories = db.query(Category).filter(
        Category.user_id == user_id,
        Category.is_archived == False
    ).all()

    existing_cat_map = {c.name.strip().lower(): c for c in user_categories}
    existing_cat_names = [c.name for c in user_categories]

    snippet = content_text[:2000].strip()
    if not snippet:
        snippet = title

    provider = gemini_provider or GeminiProvider()

    # If Gemini is available, attempt structured categorization
    if provider.is_available():
        cat_list_str = ", ".join([f'"{name}"' for name in existing_cat_names]) if existing_cat_names else "None yet"
        prompt = (
            f"You are an educational AI assistant organizing study materials for a learner.\n"
            f"The user has the following EXISTING categories in their library:\n[{cat_list_str}]\n\n"
            f"TITLE OF CAPTURED RESOURCE: {title}\n\n"
            f"CONTENT SNIPPET:\n{snippet}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. If this content clearly belongs to one of the user's EXISTING categories, recommend that category name and set matches_existing = true.\n"
            f"2. If none of the existing categories fit well, suggest a concise, professional NEW academic category name (1-3 words, e.g. 'Computer Science', 'Organic Chemistry', 'Constitutional Law', 'Economics') and set matches_existing = false.\n"
            f"3. Provide a clear 1-sentence explanation of why this category fits."
        )

        try:
            res = provider.generate_structured(prompt, CategoryRecommendationSchema)
            rec_name = res.get("recommended_category_name", "").strip()
            matches_existing = res.get("matches_existing", False)
            confidence = float(res.get("confidence", 0.85))
            explanation = res.get("explanation", f"Content aligns with {rec_name}.")
            alt_names = res.get("alternative_names", [])

            # Check if recommended name actually matches an existing category
            matching_cat = existing_cat_map.get(rec_name.lower())
            if not matching_cat:
                for ex_name_lower, ex_obj in existing_cat_map.items():
                    if ex_name_lower in rec_name.lower() or rec_name.lower() in ex_name_lower:
                        matching_cat = ex_obj
                        rec_name = ex_obj.name
                        matches_existing = True
                        break

            matched_id = matching_cat.id if matching_cat else None
            is_new = matched_id is None

            # Prepare alternatives
            alternatives = []
            for alt in alt_names:
                alt_cat = existing_cat_map.get(alt.strip().lower())
                alternatives.append({
                    "id": alt_cat.id if alt_cat else None,
                    "name": alt.strip(),
                    "is_existing": alt_cat is not None
                })

            return {
                "recommended_category_id": matched_id,
                "recommended_category_name": rec_name,
                "confidence": round(min(1.0, max(0.2, confidence)), 2),
                "explanation": explanation,
                "is_new_category": is_new,
                "alternative_categories": alternatives[:3]
            }
        except Exception as e:
            logger.warning(f"Gemini category recommendation failed, falling back to heuristic: {e}")

    # Deterministic Academic Fallback
    lower_text = f"{title} {snippet}".lower()

    # Common domain keyword matching
    domain_keywords = {
        "physics": ["physics", "quantum", "mechanics", "thermodynamics", "kinematics", "electromagnetism", "gravity", "optics"],
        "chemistry": ["chemistry", "molecule", "reaction", "organic", "benzene", "acid", "base", "solution", "catalyst"],
        "mathematics": ["calculus", "algebra", "matrix", "derivative", "integral", "theorem", "geometry", "probability"],
        "biology": ["biology", "cell", "organism", "genetics", "dna", "evolution", "physiology", "ecosystem"],
        "computer science": ["algorithm", "programming", "software", "database", "python", "javascript", "network", "api", "code"],
        "law": ["constitution", "statute", "jurisdiction", "court", "legal", "clause", "justice", "legislation"],
        "business & finance": ["finance", "accounting", "management", "market", "revenue", "investment", "strategy", "capital"],
        "history": ["civilization", "empire", "revolution", "dynasty", "war", "century", "historical", "treaty"]
    }

    best_match_name = None
    best_match_cat = None
    max_hits = 0

    # 1. Try to match user's existing categories by name or domain keywords
    for cat in user_categories:
        c_name_lower = cat.name.lower()
        hits = 0
        if c_name_lower in lower_text:
            hits += 5
        # Check domain keywords for existing categories
        for domain, kws in domain_keywords.items():
            if domain in c_name_lower:
                for kw in kws:
                    if kw in lower_text:
                        hits += 1
        if hits > max_hits:
            max_hits = hits
            best_match_cat = cat
            best_match_name = cat.name

    if best_match_cat and max_hits > 0:
        return {
            "recommended_category_id": best_match_cat.id,
            "recommended_category_name": best_match_name,
            "confidence": 0.85 if max_hits >= 3 else 0.70,
            "explanation": f"Grounded in keyword matches aligning with your existing '{best_match_name}' study collection.",
            "is_new_category": False,
            "alternative_categories": [
                {"id": c.id, "name": c.name, "is_existing": True}
                for c in user_categories if c.id != best_match_cat.id
            ][:2]
        }

    # 2. If no existing category matches, find top keyword domain
    for domain, kws in domain_keywords.items():
        hits = sum(1 for kw in kws if kw in lower_text)
        if hits > max_hits:
            max_hits = hits
            best_match_name = domain.title()

    if best_match_name:
        return {
            "recommended_category_id": None,
            "recommended_category_name": best_match_name,
            "confidence": 0.75,
            "explanation": f"Detected recurring academic concepts typical of {best_match_name}.",
            "is_new_category": True,
            "alternative_categories": [
                {"id": c.id, "name": c.name, "is_existing": True}
                for c in user_categories
            ][:2]
        }

    # 3. Fallback: User's first category if available, or 'General Studies'
    if user_categories:
        return {
            "recommended_category_id": user_categories[0].id,
            "recommended_category_name": user_categories[0].name,
            "confidence": 0.50,
            "explanation": f"Defaulted to your primary study collection '{user_categories[0].name}'.",
            "is_new_category": False,
            "alternative_categories": []
        }

    return {
        "recommended_category_id": None,
        "recommended_category_name": "General Studies",
        "confidence": 0.50,
        "explanation": "No prior category found. Suggested starting with 'General Studies'.",
        "is_new_category": True,
        "alternative_categories": []
    }
