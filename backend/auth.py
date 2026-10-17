import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status, Depends
from backend.models import User, UserSession
from backend.database import get_db
from backend.config import settings

# Initialize Argon2id password hasher with secure defaults
ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return ph.hash(password)

def verify_password(password: str, hashed_password: Optional[str]) -> bool:
    """Verifies a password against an Argon2id hash."""
    if not hashed_password:
        return False
    try:
        return ph.verify(hashed_password, password)
    except (VerifyMismatchError, InvalidHashError):
        return False

def hash_session_token(token: str) -> str:
    """Hashes a raw session token for secure database storage using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_session(
    db: Session,
    user_id: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Tuple[str, UserSession]:
    """
    Generates a cryptographically strong session token and persists the session hash in DB.
    Returns (raw_session_token, user_session_record).
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_session_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    session_record = UserSession(
        session_token_hash=token_hash,
        user_id=user_id,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        is_revoked=False,
        user_agent=user_agent[:500] if user_agent else None,
        ip_address=ip_address[:100] if ip_address else None
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return raw_token, session_record

def invalidate_session(db: Session, raw_token: str) -> bool:
    """Revokes a session by hashing the token and marking the DB row as is_revoked."""
    token_hash = hash_session_token(raw_token)
    session_record = db.query(UserSession).filter(UserSession.session_token_hash == token_hash).first()
    if session_record:
        session_record.is_revoked = True
        db.commit()
        return True
    return False

def get_session_token_from_request(request: Request) -> Optional[str]:
    """
    Extracts session token from HttpOnly cookie first,
    or fallback to Bearer token in Authorization header.
    """
    # 1. Check Authorization header first (allows explicit Bearer token in tests/APIs/extensions)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 2. Check HttpOnly cookie
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that enforces real authentication.
    Resolves session, validates expiry and revocation, and returns the User object.
    """
    raw_token = get_session_token_from_request(request)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token_hash = hash_session_token(raw_token)
    session_record = db.query(UserSession).filter(
        UserSession.session_token_hash == token_hash,
        UserSession.is_revoked == False
    ).first()

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if session_record.expires_at < datetime.utcnow():
        session_record.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user
