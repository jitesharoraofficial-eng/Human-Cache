"""
Deterministic local fallback embedding generator.
Used when GEMINI_API_KEY is not configured or in offline/test environments.
Produces consistent, normalized 64-dimensional pseudo-semantic vectors based on character n-grams and hashing.
"""
import math
import re
import hashlib
from typing import List

def generate_local_embedding(text: str, dim: int = 64) -> List[float]:
    clean = text.lower().strip()
    words = re.findall(r'\b\w+\b', clean)
    if not words:
        words = ["empty"]

    vector = [0.0] * dim
    for word in words:
        # Hash full word
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vector[idx] += 1.0

        # Also add bigrams for sub-word semantic overlap
        for i in range(len(word) - 1):
            bg = word[i:i+2]
            bh = int(hashlib.sha256(bg.encode("utf-8")).hexdigest(), 16)
            b_idx = bh % dim
            vector[b_idx] += 0.3

    # Normalize vector to unit length
    magnitude = math.sqrt(sum(v * v for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    return vector

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    return max(0.0, min(1.0, dot))
