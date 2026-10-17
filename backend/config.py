from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Human Cache"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./human_cache.db"
    
    # Upload storage
    STORAGE_DIR: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 25
    
    # AI Config
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    LLM_PROVIDER: str = "auto" # "gemini", "mock", or "auto"
    
    # Security & Auth
    SECRET_KEY: str = "human-cache-dev-secret-key-super-secure-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    SESSION_COOKIE_NAME: str = "humancache_session"
    COOKIE_SECURE: bool = False # Set True in production with HTTPS
    COOKIE_SAMESITE: str = "lax"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "chrome-extension://*",
        "edge-extension://*"
    ]

    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
