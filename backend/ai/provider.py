"""
Abstract base interface for AI providers.
Ensures provider agnosticism (Gemini, Anthropic, Local, etc.).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseAIProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        """Generates raw text response."""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema_class: Any, system_prompt: Optional[str] = None, temperature: float = 0.1) -> Dict[str, Any]:
        """Generates and validates structured JSON response matching schema_class."""
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generates a dense vector embedding for the input text."""
        pass

    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a batch of texts."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and reachable."""
        pass
