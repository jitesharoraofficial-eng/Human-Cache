import io
import os
import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from tests.test_auth_and_isolation import client, TestingSessionLocal


def register_and_login(client: TestClient, email: str, name: str = "Upload Tester"):
    res = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!"}
    )
    assert res.status_code == 200, res.text
    return res.json()["user"]


def test_oversized_file_rejected_without_crashing():
    """
    Ensure files exceeding MAX_UPLOAD_SIZE_MB (25MB) are streaming-rejected
    with HTTP 400 and removed immediately from disk.
    """
    user = register_and_login(client, "oversized_tester@humancache.ai", "Oversized Tester")

    # Generate a virtual file just over 25 MB (26 MB)
    oversized_size = (settings.MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024
    
    # We create a generator or BytesIO starting with valid PDF header
    header = b"%PDF-1.4\n"
    padding = b"0" * (oversized_size - len(header))
    oversized_bytes = header + padding

    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("huge_document.pdf", io.BytesIO(oversized_bytes), "application/pdf")}
    )

    assert res.status_code == 400
    assert "exceeds maximum allowed upload size" in res.json()["detail"]

    # Verify no leaked files in storage
    user_storage = os.path.abspath(os.path.join(settings.STORAGE_DIR, user["id"]))
    if os.path.exists(user_storage):
        leaked_files = [f for f in os.listdir(user_storage) if "huge_document" in f]
        assert len(leaked_files) == 0, f"Leaked file found: {leaked_files}"


def test_disguised_executable_rejected():
    """
    Reject executable binaries disguised as .pdf (PE / MZ header).
    """
    user = register_and_login(client, "malware_tester@humancache.ai", "Malware Tester")

    # Windows PE executable header
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This is a binary executable"

    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("trojan_report.pdf", io.BytesIO(fake_exe), "application/pdf")}
    )

    assert res.status_code == 400
    assert "forbidden binary type" in res.json()["detail"] or "Invalid PDF file" in res.json()["detail"]


def test_malformed_pdf_rejected():
    """
    Reject invalid/corrupted PDF that starts with %PDF- but contains unparseable corrupted structure.
    """
    register_and_login(client, "malformed_tester@humancache.ai", "Malformed Tester")

    corrupted_pdf = b"%PDF-1.5 corrupt garbage payload that cannot be parsed by pypdf"

    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf), "application/pdf")}
    )

    assert res.status_code == 400
    assert "Malformed" in res.json()["detail"] or "unreadable" in res.json()["detail"]


def test_valid_pdf_upload_and_performance_metrics():
    """
    Verify valid document upload succeeds and returns structured performance metrics
    without leaking private document contents.
    """
    user = register_and_login(client, "perf_tester@humancache.ai", "Perf Tester")

    # Build a minimal valid 1-page PDF
    # Minimal PDF syntax
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] /Contents 4 0 R>> endobj\n"
        b"4 0 obj <</Length 44>> stream\n"
        b"BT /F1 12 Tf 100 700 Td (Thermodynamics) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000218 00000 n \n"
        b"trailer <</Size 5 /Root 1 0 R>>\n"
        b"startxref\n"
        b"312\n"
        b"%%EOF\n"
    )

    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("thermodynamics_intro.pdf", io.BytesIO(pdf_content), "application/pdf")}
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert "performance_metrics" in data
    metrics = data["performance_metrics"]
    assert "timings_ms" in metrics
    timings = metrics["timings_ms"]
    assert "upload_save_ms" in timings
    assert "text_extraction_ms" in timings
    assert "chunking_ms" in timings
    assert "vector_embedding_ms" in timings
    assert "graph_extraction_ms" in timings
    assert "total_duration_ms" in timings
    assert "Thermodynamics" not in str(timings)  # Confidentiality verification
