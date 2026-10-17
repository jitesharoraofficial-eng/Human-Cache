import os
import re
from typing import List, Tuple, Optional
from fastapi import HTTPException, UploadFile
import pypdf

from backend.config import settings

# Dangerous binary signatures that should never be uploaded
DANGEROUS_SIGNATURES = [
    (b"MZ", "Windows PE executable / DLL"),
    (b"\x7fELF", "Linux ELF executable"),
    (b"\xca\xfe\xba\xbe", "Java class bytecode / Mach-O universal binary"),
    (b"\xfe\xed\xfa\xce", "Mach-O binary"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit binary"),
    (b"\xce\xfa\xed\xfe", "Mach-O reverse binary"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit reverse binary"),
]


def sanitize_filename(filename: Optional[str], default_name: str = "document") -> str:
    """
    Strips directory traversal sequences and special characters from upload filename.
    """
    raw_name = os.path.basename(filename or default_name)
    safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', raw_name)
    # Ensure there is a base name
    if not safe or safe.startswith("."):
        safe = f"{default_name}{safe}"
    return safe


def validate_file_header(header: bytes, ext: str):
    """
    Inspects leading bytes to verify actual content type matches extension
    and prevents disguised executable or malformed files.
    """
    # 1. Reject known executable headers regardless of extension
    for sig, desc in DANGEROUS_SIGNATURES:
        if header.startswith(sig):
            raise HTTPException(
                status_code=400,
                detail=f"Security violation: File header matches forbidden binary type ({desc})."
            )

    # 2. Format-specific magic byte checks
    if ext == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file: Missing '%PDF-' header signature."
            )
    elif ext == ".docx":
        if not header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=400,
                detail="Invalid DOCX file: Missing ZIP archive signature."
            )
    elif ext == ".png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PNG file: Missing PNG signature."
            )
    elif ext in [".jpg", ".jpeg"]:
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=400,
                detail="Invalid JPEG file: Missing JPEG signature."
            )
    elif ext == ".webp":
        if not (header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP"):
            raise HTTPException(
                status_code=400,
                detail="Invalid WEBP file: Missing WEBP signature."
            )
    elif ext in [".txt", ".md"]:
        if b"\x00" in header:
            raise HTTPException(
                status_code=400,
                detail="Invalid text file: File contains binary null bytes."
            )
        try:
            header.decode("utf-8")
        except UnicodeDecodeError:
            try:
                header.decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid text file: File encoding is not valid UTF-8 or Latin-1."
                )


def stream_save_and_validate(
    upload_file: UploadFile,
    dest_path: str,
    allowed_extensions: List[str],
    max_size_mb: Optional[int] = None,
    chunk_size: int = 64 * 1024
) -> Tuple[int, str, str]:
    """
    Streams an uploaded file chunk-by-chunk directly to disk, validating:
    1. Extension whitelist.
    2. Size limit enforcement without buffering entire payload into memory.
    3. Magic byte content integrity on the initial chunk.
    4. Corrupted PDF structural validation.

    Returns: (total_bytes, safe_filename, extension)
    Raises: HTTPException on invalid type, oversized payload, or corrupt content.
    """
    effective_max_mb = max_size_mb if max_size_mb is not None else settings.MAX_UPLOAD_SIZE_MB
    max_bytes = effective_max_mb * 1024 * 1024

    safe_filename = sanitize_filename(upload_file.filename)
    ext = os.path.splitext(safe_filename)[1].lower()

    if ext not in [e.lower() for e in allowed_extensions]:
        allowed_str = ", ".join(allowed_extensions)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed formats: {allowed_str}."
        )

    # Ensure parent directory exists
    parent_dir = os.path.dirname(dest_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    total_bytes = 0
    first_chunk = True

    try:
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = upload_file.file.read(chunk_size)
                if not chunk:
                    break

                if first_chunk:
                    validate_file_header(chunk[:512], ext)
                    first_chunk = False

                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File exceeds maximum allowed upload size of {effective_max_mb}MB."
                    )

                buffer.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        # Additional structural validation for PDF files
        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(dest_path)
                # Ensure it has pages and reader can access them
                _ = len(reader.pages)
            except Exception as pdf_err:
                raise HTTPException(
                    status_code=400,
                    detail=f"Malformed or unreadable PDF: {str(pdf_err)[:100]}"
                )

        return total_bytes, safe_filename, ext

    except Exception:
        # Guarantee immediate cleanup of partial/invalid file on disk
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise
