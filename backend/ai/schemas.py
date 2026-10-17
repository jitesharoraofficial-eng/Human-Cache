"""
Pydantic contracts for structured LLM generation, validation, and repair.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QuizQuestionSchema(BaseModel):
    id: str = Field(..., description="Unique question identifier, e.g. q1, q2")
    question: str = Field(..., description="The quiz question text")
    type: str = Field(default="mcq", description="mcq, tf, or short")
    options: List[str] = Field(default_factory=list, description="Answer options for MCQ or TF")
    correct_answer: str = Field(..., description="The correct answer text")
    explanation: str = Field(..., description="Detailed pedagogical explanation grounded in source")
    source_citation: Optional[str] = Field(None, description="Optional page/slide/section citation")

class QuizOutputSchema(BaseModel):
    title: str = Field(..., description="Quiz title")
    topic_name: str = Field(..., description="Topic name")
    difficulty: str = Field(default="medium", description="easy, medium, or hard")
    questions: List[QuizQuestionSchema] = Field(..., min_length=1)

class FlashcardItemSchema(BaseModel):
    front: str = Field(..., description="Front of the card (question/prompt)")
    back: str = Field(..., description="Back of the card (answer/explanation)")
    hint: Optional[str] = Field(None, description="Optional recall hint")
    source_citation: Optional[str] = Field(None, description="Optional page/slide reference")
    concept_id: Optional[str] = Field(None, description="Identifier of the concept tested")
    section_name: Optional[str] = Field(None, description="Source section or heading")
    detail_level: Optional[str] = Field(default="semi-detailed", description="brief, semi-detailed, or detailed")

class FlashcardDeckSchema(BaseModel):
    topic_name: str = Field(..., description="Topic name")
    cards: List[FlashcardItemSchema] = Field(..., min_length=1)
    detail_level: Optional[str] = Field(default="semi-detailed", description="brief, semi-detailed, or detailed")
    coverage_status: Optional[str] = Field(default="verified", description="verified, partial, or source_incomplete")
    covered_concepts_count: Optional[int] = Field(default=0)

class MindMapLeafSchema(BaseModel):
    label: str = Field(..., description="Leaf concept label")
    description: Optional[str] = Field(None, description="Short concept detail")

class MindMapBranchSchema(BaseModel):
    title: str = Field(..., description="Branch title")
    description: Optional[str] = Field("", description="Branch overview")
    leaves: List[str] = Field(default_factory=list, description="Sub-concepts or key points")

class MindMapOutputSchema(BaseModel):
    central_topic: str = Field(..., description="Central topic name")
    branches: List[MindMapBranchSchema] = Field(..., min_length=1)

class GraphNodeSchema(BaseModel):
    name: str = Field(..., description="Canonical concept name")
    topic_type: str = Field(default="concept", description="concept, principle, algorithm, theory, fact")
    description: str = Field(..., description="Concise definition from source")
    aliases: List[str] = Field(default_factory=list, description="Synonyms or alternative names")

class GraphEdgeSchema(BaseModel):
    source: str = Field(..., description="Canonical source concept name")
    target: str = Field(..., description="Canonical target concept name")
    relationship_type: str = Field(default="relates_to", description="part_of, prerequisite_of, causes, contrasts_with, example_of, relates_to")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence: str = Field(..., description="Direct citation or sentence from the source demonstrating the link")

class KnowledgeGraphExtractionSchema(BaseModel):
    nodes: List[GraphNodeSchema] = Field(default_factory=list)
    edges: List[GraphEdgeSchema] = Field(default_factory=list)

class ExplanationOutputSchema(BaseModel):
    topic_name: Optional[str] = Field(default="")
    explanation: Optional[str] = Field(default="")
    prerequisites: List[str] = Field(default_factory=list)
    analogies: List[str] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    source_citations: List[str] = Field(default_factory=list)
    exam_traps: Optional[List[str]] = Field(default_factory=list, description="Common traps and edge cases")
    coverage_status: Optional[str] = Field(default="verified", description="verified, partial, or source_incomplete")
    covered_concepts: Optional[List[str]] = Field(default_factory=list)
    missing_concepts: Optional[List[str]] = Field(default_factory=list)
    detail_level: Optional[str] = Field(default="semi-detailed")
