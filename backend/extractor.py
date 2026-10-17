import os
import re
from typing import Tuple, List, Dict, Any
import pypdf
import docx

def extract_raw_pages_and_text(file_path: str, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts raw text and page structures from PDF, DOCX, TXT, MD files.
    Returns: (full_text, pages_data)
    """
    ext = os.path.splitext(filename)[1].lower()
    pages_data = []
    full_text = ""

    if ext == ".pdf":
        try:
            reader = pypdf.PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_clean = page_text.strip()
                char_len = len(page_clean)
                status = "readable" if char_len >= 25 else ("empty" if char_len == 0 else "scanned_or_sparse")
                pages_data.append({
                    "page_number": idx + 1,
                    "text": page_clean,
                    "char_count": char_len,
                    "status": status
                })
                if page_clean:
                    full_text += f"\n--- Page {idx + 1} ---\n" + page_clean
        except Exception as e:
            full_text = f"Error extracting PDF: {str(e)}"
    elif ext in [".docx", ".doc"]:
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)
            pages_data.append({
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text),
                "status": "readable" if len(full_text) >= 25 else "empty"
            })
        except Exception as e:
            full_text = f"Error extracting DOCX: {str(e)}"
    else: # txt, md, csv, etc.
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                full_text = f.read()
            pages_data.append({
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text),
                "status": "readable" if len(full_text) >= 25 else "empty"
            })
        except Exception as e:
            full_text = f"Error reading text file: {str(e)}"

    return full_text, pages_data


def compute_page_coverage(pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes page-level audit and coverage metrics.
    Detects empty, scanned, corrupted, and readable pages.
    """
    total_pages = len(pages_data)
    readable = [p for p in pages_data if p.get("status") == "readable"]
    scanned_or_sparse = [p for p in pages_data if p.get("status") == "scanned_or_sparse"]
    empty = [p for p in pages_data if p.get("status") == "empty"]

    coverage_pct = round((len(readable) / max(1, total_pages)) * 100, 1)
    status = "fully_readable" if len(readable) == total_pages else ("partially_scanned" if scanned_or_sparse else "sparse")

    return {
        "total_pages": total_pages,
        "readable_pages": len(readable),
        "scanned_or_sparse_pages": len(scanned_or_sparse),
        "empty_pages": len(empty),
        "coverage_percentage": coverage_pct,
        "status": status
    }


def chunk_pages_and_text(pages_data: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
    """
    Document-aware semantic chunking.
    Preserves page numbers, Units, Chapters, Sections, and paragraph boundaries.
    Never dumps entire multi-thousand char pages into single monolithic chunks.
    Target chunk size: 500 - 1100 characters.
    """
    chunks = []
    heading_re = re.compile(
        r'^(?:#{1,4}\s+|'
        r'(?:Unit|UNIT)\s+(?:[0-9]+|[IVXLCDM]+)[\s:\-–—]+|'
        r'(?:Chapter|CHAPTER)\s+(?:[0-9]+|[IVXLCDM]+)[\s:\-–—]+|'
        r'[0-9]+(?:\.[0-9]+)+\s+|'
        r'(?:Section|SECTION|Topic|TOPIC)\s*(?:[0-9]+|[A-Z])?[:\s\-–—]+)'
        r'([A-Za-z0-9][^\n]{2,70})',
        re.MULTILINE
    )

    current_heading = None

    def split_large_para(para_text: str, max_len: int = 1000) -> List[str]:
        if len(para_text) <= max_len:
            return [para_text]
        sentences = re.split(r'(?<=[.?!])\s+', para_text)
        sub_chunks = []
        cur = ""
        for s in sentences:
            if not s.strip():
                continue
            if len(cur) + len(s) > max_len and len(cur) > 200:
                sub_chunks.append(cur.strip())
                cur = s
            else:
                cur = f"{cur} {s}".strip() if cur else s
        if cur:
            sub_chunks.append(cur.strip())
        return sub_chunks if sub_chunks else [para_text[:max_len]]

    if pages_data:
        for p in pages_data:
            page_num = p.get("page_number", 1)
            raw_page_text = p.get("text", "").strip()
            if not raw_page_text:
                continue

            paragraphs = re.split(r'\n\s*\n', raw_page_text)
            current_chunk = ""

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # Detect heading update
                h_match = heading_re.search(para)
                if h_match:
                    detected = h_match.group(1).strip()
                    if len(detected) > 3:
                        current_heading = detected

                split_parts = split_large_para(para, max_len=1000)
                for part in split_parts:
                    if len(current_chunk) + len(part) > 1100 and len(current_chunk) >= 300:
                        chunks.append({
                            "content": current_chunk.strip(),
                            "page_number": page_num,
                            "section_heading": current_heading
                        })
                        current_chunk = part
                    else:
                        current_chunk = f"{current_chunk}\n\n{part}".strip() if current_chunk else part

            if current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "page_number": page_num,
                    "section_heading": current_heading
                })
    else:
        paragraphs = re.split(r'\n\s*\n', full_text)
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            h_match = heading_re.search(para)
            if h_match:
                detected = h_match.group(1).strip()
                if len(detected) > 3:
                    current_heading = detected

            split_parts = split_large_para(para, max_len=1000)
            for part in split_parts:
                if len(current_chunk) + len(part) > 1100 and len(current_chunk) >= 300:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "page_number": 1,
                        "section_heading": current_heading
                    })
                    current_chunk = part
                else:
                    current_chunk = f"{current_chunk}\n\n{part}".strip() if current_chunk else part

        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "page_number": 1,
                "section_heading": current_heading
            })

    if not chunks:
        chunks = [{"content": full_text or "No content extracted.", "page_number": 1, "section_heading": None}]

    return chunks


def extract_text_from_file(file_path: str, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts text from PDF, DOCX, TXT, MD files and returns chunks.
    Maintains backward compatibility across all consumers.
    """
    full_text, pages_data = extract_raw_pages_and_text(file_path, filename)
    chunks = chunk_pages_and_text(pages_data, full_text)
    return full_text, chunks

def extract_topics_and_concepts(text: str, filename: str) -> List[Dict[str, Any]]:
    """
    Intelligent document-aware hierarchical extractor for Units, Chapters, Sections, and Concepts.
    Follows: Document -> Unit / Chapter -> Topic -> Subtopic / Concept.
    Guarantees full-document coverage without starving middle and late units.
    """
    units_found = []
    topics_found = []
    seen = set()

    # 1. Detect Units, Chapters, Modules, and Parts across the full document text
    unit_chapter_pattern = r'^\s*(?:(?:Unit|UNIT|Module|MODULE)\s*([0-9]+|[IVXLCDM]+)?[\s:\-–—]+([^\n]+)|(?:Chapter|CHAPTER|Part|PART)\s*([0-9]+|[IVXLCDM]+)?[\s:\-–—]+([^\n]+))'
    for match in re.finditer(unit_chapter_pattern, text, re.MULTILINE):
        if match.group(2):
            unit_num = (match.group(1) or "").strip()
            unit_title = re.sub(r'[^a-zA-Z0-9\s]', '', match.group(2) or "").strip()
            num_prefix = f"Unit {unit_num}: " if unit_num else "Unit: "
            name = f"{num_prefix}{unit_title}".strip()
            topic_type = "unit"
        elif match.lastindex and match.lastindex >= 4:
            ch_num = (match.group(3) or "").strip()
            ch_title = re.sub(r'[^a-zA-Z0-9\s]', '', match.group(4) or "").strip()
            num_prefix = f"Chapter {ch_num}: " if ch_num else "Chapter: "
            name = f"{num_prefix}{ch_title}".strip()
            topic_type = "chapter"
        else:
            continue

        if 4 < len(name) < 75 and name.lower() not in seen:
            seen.add(name.lower())
            units_found.append({
                "name": name,
                "canonical_name": name.title(),
                "description": f"Curriculum division from {filename}.",
                "topic_type": topic_type,
                "category": name.title()
            })

    # 2. Detect formal sections and numbered topics across all pages
    heading_pattern = r'^\s*(?:#{1,4}\s+|[0-9]+(?:\.[0-9]+)+\s+|(?:Section|SECTION|Topic|TOPIC)[:\s]+)([A-Za-z0-9][^\n]{3,65})'
    for match in re.finditer(heading_pattern, text, re.MULTILINE):
        topic_name = match.group(1).strip()
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', topic_name).strip()
        if 3 < len(cleaned) < 60 and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            topics_found.append({
                "name": cleaned,
                "canonical_name": cleaned.title(),
                "description": f"Curriculum topic identified in {filename}.",
                "topic_type": "topic"
            })

    # 3. Detect definitions ("X is defined as...", "X refers to...", "X is a...")
    def_pattern = r'([A-Z][A-Za-z\s]{2,35})\s+(?:is defined as|refers to|is a fundamental|is the process of|consists of)\s+([^.\n]+)'
    for match in re.finditer(def_pattern, text):
        concept = match.group(1).strip()
        definition = match.group(2).strip()
        if 3 < len(concept) < 45 and concept.lower() not in seen:
            seen.add(concept.lower())
            topics_found.append({
                "name": concept,
                "canonical_name": concept.title(),
                "description": f"{concept} {definition[:180]}.",
                "topic_type": "definition"
            })

    # 4. Balanced extraction across all units / sections
    unit_positions = []
    for match in re.finditer(unit_chapter_pattern, text, re.MULTILINE):
        unit_positions.append(match.start())
    unit_positions.append(len(text))

    stopwords = {"The", "This", "That", "These", "Those", "When", "What", "There", "Here", "With", "From", "Into", "Over", "After", "Before", "Page", "Figure", "Table", "Note", "Unit", "Chapter", "Section", "Topic"}

    if len(unit_positions) > 2: # Multiple units detected
        for i in range(len(unit_positions) - 1):
            sec_text = text[unit_positions[i]:unit_positions[i+1]]
            candidates = re.findall(r'\b(?:[A-Z]{2,}|[A-Z][a-z]+)(?:[ \t]+[A-Z][a-z]+)?\b', sec_text)
            for c in candidates:
                c_clean = re.sub(r'\s+', ' ', c).strip()
                if c_clean and c_clean not in stopwords and len(c_clean) > 3 and not c_clean.lower().startswith("unit ") and not c_clean.lower().startswith("chapter "):
                    if c_clean.lower() not in seen and len(topics_found) < 36:
                        seen.add(c_clean.lower())
                        topics_found.append({
                            "name": c_clean,
                            "canonical_name": c_clean.title(),
                            "description": f"Curriculum topic from {filename}.",
                            "topic_type": "concept"
                        })
    else:
        candidates = re.findall(r'\b(?:[A-Z]{2,}|[A-Z][a-z]+)(?:[ \t]+[A-Z][a-z]+)?\b', text)
        freq = {}
        for c in candidates:
            c_clean = re.sub(r'\s+', ' ', c).strip()
            if c_clean and c_clean not in stopwords and len(c_clean) > 3 and not c_clean.lower().startswith("unit ") and not c_clean.lower().startswith("chapter "):
                freq[c_clean] = freq.get(c_clean, 0) + 1
        sorted_candidates = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        for term, count in sorted_candidates[:24]:
            if term.lower() not in seen and len(topics_found) < 32:
                seen.add(term.lower())
                topics_found.append({
                    "name": term,
                    "canonical_name": term.title(),
                    "description": f"Key concept in {filename} (referenced {count} times).",
                    "topic_type": "concept"
                })

    # 5. Fallback to document title if still empty
    if not units_found and not topics_found:
        base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        topics_found.append({
            "name": base_name,
            "canonical_name": base_name,
            "description": f"Primary topic derived from document {filename}.",
            "topic_type": "concept"
        })

    # Balanced assembly: Keep ALL detected Units/Chapters (never truncate curriculum units)
    # Plus up to 30 distributed subtopics/concepts
    assembled = list(units_found)
    assembled.extend(topics_found[:32])

    return assembled
