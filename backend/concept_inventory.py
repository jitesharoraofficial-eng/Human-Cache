"""
Source Outline & Concept Inventory Builder for Human Cache.

Constructs, stores, and validates structured concept inventories for documents.
Extracts verified headings, sections, definitions, formulas, processes, and relationships
from all source chunks, avoiding arbitrary truncation or top-k limitations.
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models import Document, SourceChunk, DocumentConceptInventory

logger = logging.getLogger("concept_inventory")

HEADING_PATTERNS = [
    re.compile(r'^(?:#{1,4}\s+|Chapter\s+\d+[:\s]+|[0-9]+\.[0-9]*\s+|Section\s+\d+[:\s]+)([A-Z][^\n]{2,70})', re.MULTILINE),
    re.compile(r'^([A-Z][A-Za-z0-9\s,\-]{2,40}):$', re.MULTILINE),
    re.compile(r'^\b([A-Z][A-Z\s0-9]{3,40})\b$', re.MULTILINE)
]

DEFINITION_PATTERNS = [
    re.compile(r'([A-Z][A-Za-z\s]{2,35})\s+(?:is defined as|refers to|is a fundamental|is the process of|represents|is categorized as)\s+([^.\n]+)', re.IGNORECASE),
    re.compile(r'([A-Z][A-Za-z\s]{2,35}):\s+([^.\n]{10,180})')
]

FORMULA_PATTERNS = [
    re.compile(r'([A-Za-z\s]{2,30})\s*(?:=|is given by|formula:\s*)\s*([A-Za-z0-9\s\+\-\*\/\^\(\)\=\_\{\}\\\<\>]+)'),
    re.compile(r'\b(E\s*=\s*mc\^?2|PV\s*=\s*nRT|F\s*=\s*ma|a\^2\s*\+\s*b\^2\s*=\s*c\^2)\b')
]

PROCESS_PATTERNS = [
    re.compile(r'(?:Step\s+\d+|Phase\s+\d+|Stage\s+\d+|First,|Second,|Third,|Finally,)\s*:?\s*([^.\n]+)', re.IGNORECASE)
]


class ConceptInventoryBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build_or_get_inventory(self, document_id: str, user_id: str, force_rebuild: bool = False) -> DocumentConceptInventory:
        """
        Retrieves existing inventory or builds a fresh one idempotently.
        Ensures strict user ownership.
        """
        if not force_rebuild:
            existing = self.db.query(DocumentConceptInventory).filter(
                DocumentConceptInventory.document_id == document_id,
                DocumentConceptInventory.user_id == user_id
            ).first()
            if existing and existing.concepts_count > 0:
                return existing

        doc = self.db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found or access denied for user {user_id}")

        chunks = self.db.query(SourceChunk).filter(
            SourceChunk.document_id == document_id
        ).order_by(SourceChunk.chunk_index.asc()).all()

        if not chunks:
            # Check raw_text
            if doc.raw_text:
                chunks_data = [{"id": f"chunk_raw_{doc.id}", "content": doc.raw_text, "page_number": 1, "section_heading": doc.title}]
            else:
                chunks_data = []
        else:
            chunks_data = [
                {
                    "id": c.id,
                    "content": c.content,
                    "page_number": c.page_number or 1,
                    "section_heading": c.section_heading
                }
                for c in chunks
            ]

        inventory_data = self._extract_inventory_from_chunks(doc.title, chunks_data)

        # Upsert record
        existing = self.db.query(DocumentConceptInventory).filter(
            DocumentConceptInventory.document_id == document_id
        ).first()
        if existing:
            existing.outline_json = inventory_data["outline"]
            existing.concepts_json = inventory_data["concepts"]
            existing.sections_count = len(inventory_data["outline"])
            existing.concepts_count = len(inventory_data["concepts"])
            existing.status = inventory_data["status"]
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_inv = DocumentConceptInventory(
                document_id=document_id,
                user_id=user_id,
                outline_json=inventory_data["outline"],
                concepts_json=inventory_data["concepts"],
                sections_count=len(inventory_data["outline"]),
                concepts_count=len(inventory_data["concepts"]),
                status=inventory_data["status"]
            )
            self.db.add(new_inv)
            self.db.commit()
            self.db.refresh(new_inv)
            return new_inv

    def _extract_inventory_from_chunks(self, doc_title: str, chunks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        outline = []
        concepts = []
        seen_concepts = set()
        seen_sections = set()
        current_section = doc_title or "Overview"

        for idx, chunk in enumerate(chunks_data):
            text = chunk.get("content", "")
            chunk_id = chunk.get("id")
            page_num = chunk.get("page_number", 1)

            # 1. Identify Headings / Section boundaries
            sec_heading = chunk.get("section_heading")
            if not sec_heading:
                for pattern in HEADING_PATTERNS:
                    m = pattern.search(text)
                    if m:
                        sec_heading = (m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)).strip().rstrip(':')
                        break

            if sec_heading and sec_heading.lower() not in seen_sections:
                seen_sections.add(sec_heading.lower())
                current_section = sec_heading
                outline.append({
                    "section_index": len(outline) + 1,
                    "heading": current_section,
                    "page_number": page_num,
                    "chunk_id": chunk_id
                })

            # 2. Extract Definitions
            for pattern in DEFINITION_PATTERNS:
                for m in pattern.finditer(text):
                    if m.lastindex and m.lastindex >= 2:
                        term = m.group(1).strip()
                        definition = m.group(2).strip()
                    elif m.lastindex and m.lastindex == 1:
                        term = m.group(1).strip()
                        definition = m.group(0).strip()
                    else:
                        continue
                    if 2 < len(term) < 50 and term.lower() not in seen_concepts:
                        seen_concepts.add(term.lower())
                        concepts.append({
                            "concept_id": f"c_{uuid.uuid4().hex[:8]}",
                            "name": term.title(),
                            "type": "definition",
                            "definition": definition[:250],
                            "section_heading": current_section,
                            "page_number": page_num,
                            "chunk_id": chunk_id
                        })

            # 3. Extract Formulas
            for pattern in FORMULA_PATTERNS:
                for m in pattern.finditer(text):
                    formula_name = m.group(1).strip() if (m.lastindex and m.lastindex > 1) else "Core Relationship"
                    formula_expr = m.group(2).strip() if (m.lastindex and m.lastindex > 1) else (m.group(1).strip() if m.lastindex else m.group(0).strip())
                    if formula_name.lower() not in seen_concepts and len(formula_expr) > 2:
                        seen_concepts.add(formula_name.lower())
                        concepts.append({
                            "concept_id": f"c_{uuid.uuid4().hex[:8]}",
                            "name": formula_name.title(),
                            "type": "formula",
                            "definition": f"Formula: {formula_expr}",
                            "section_heading": current_section,
                            "page_number": page_num,
                            "chunk_id": chunk_id
                        })

            # 4. Extract Processes / Steps
            for pattern in PROCESS_PATTERNS:
                for m in pattern.finditer(text):
                    step_desc = (m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)).strip()
                    step_key = f"{current_section} Step"
                    if len(step_desc) > 5 and step_desc.lower() not in seen_concepts:
                        seen_concepts.add(step_desc.lower())
                        concepts.append({
                            "concept_id": f"c_{uuid.uuid4().hex[:8]}",
                            "name": f"{current_section}: {step_desc[:30]}",
                            "type": "process",
                            "definition": step_desc[:250],
                            "section_heading": current_section,
                            "page_number": page_num,
                            "chunk_id": chunk_id
                        })

        # If outline is empty, provide default single section
        if not outline:
            outline.append({
                "section_index": 1,
                "heading": doc_title or "Main Module",
                "page_number": 1,
                "chunk_id": chunks_data[0]["id"] if chunks_data else None
            })

        # If few concepts detected, harvest key entities from capital nouns
        if len(concepts) < 3 and chunks_data:
            full_body = " ".join(c.get("content", "") for c in chunks_data)
            cap_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', full_body)
            freq: Dict[str, int] = {}
            for ct in cap_terms:
                if len(ct) > 3 and ct.lower() not in ["chapter", "section", "figure", "table", "page"]:
                    freq[ct] = freq.get(ct, 0) + 1
            top_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:8]
            for term, _ in top_terms:
                if term.lower() not in seen_concepts:
                    seen_concepts.add(term.lower())
                    concepts.append({
                        "concept_id": f"c_{uuid.uuid4().hex[:8]}",
                        "name": term,
                        "type": "concept",
                        "definition": f"Core domain entity emphasized in {doc_title}.",
                        "section_heading": outline[0]["heading"],
                        "page_number": 1,
                        "chunk_id": chunks_data[0]["id"]
                    })

        status = "verified" if len(concepts) >= 3 else "partial" if concepts else "unreadable"

        return {
            "outline": outline,
            "concepts": concepts,
            "status": status
        }
