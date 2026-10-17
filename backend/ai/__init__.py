"""
AI Package initialization.
Exposes GeminiProvider, RetrievalService, and RAGIntelligenceEngine.
"""
from backend.ai.provider import BaseAIProvider
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.retrieval import RetrievalService
from backend.ai.generation import RAGIntelligenceEngine

__all__ = [
    "BaseAIProvider",
    "GeminiProvider",
    "RetrievalService",
    "RAGIntelligenceEngine"
]
