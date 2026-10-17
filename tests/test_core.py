import os
from datetime import datetime, timedelta
from backend.extractor import extract_text_from_file, extract_topics_and_concepts
from backend.memory_engine import calculate_current_retention, update_memory_on_recall
from backend.exam_planner import parse_date_sheet_text
from backend.models import TopicMemoryState

def test_topic_extractor_headings():
    sample_text = """
    # Raft Consensus Protocol
    Raft decomposes consensus into leader election, log replication, and safety.
    
    ## Leader Election
    Leader Election is defined as the process where candidate nodes collect majority votes.
    
    ## Majority Quorum
    Majority Quorum refers to having strictly greater than half of the cluster members agree.
    """
    topics = extract_topics_and_concepts(sample_text, "raft.txt")
    names = [t["canonical_name"].lower() for t in topics]
    assert any("raft" in n for n in names)
    assert any("leader election" in n or "election" in n for n in names)

def test_ebbinghaus_retention_calculation():
    # 0 days elapsed -> retention should be ~ 1.0
    mem = TopicMemoryState(
        stability=2.0,
        difficulty=0.3,
        last_learned_at=datetime.utcnow()
    )
    r0 = calculate_current_retention(mem)
    assert 0.95 <= r0 <= 1.0

    # 4 days elapsed with 2 day stability -> retention should drop to exp(-4/2) = exp(-2) = ~0.135
    mem_old = TopicMemoryState(
        stability=2.0,
        difficulty=0.3,
        last_learned_at=datetime.utcnow() - timedelta(days=4)
    )
    r_decay = calculate_current_retention(mem_old)
    assert r_decay < 0.25

def test_date_sheet_parser():
    date_sheet = """
    EXAMINATION TIMETABLE - FALL 2026
    15/10/2026 - Distributed Systems - 10:00 AM
    18/10/2026 - Cognitive Neural Architectures - 02:00 PM
    22/10/2026 - Database Internals - 09:30 AM
    """
    exams = parse_date_sheet_text(date_sheet)
    assert len(exams) >= 3
    subjects = [e["subject"].lower() for e in exams]
    assert any("distributed" in s for s in subjects)
    assert any("cognitive" in s for s in subjects)
    assert any("database" in s for s in subjects)

if __name__ == "__main__":
    test_topic_extractor_headings()
    test_ebbinghaus_retention_calculation()
    test_date_sheet_parser()
    print("ALL CORE UNIT TESTS PASSED!")
