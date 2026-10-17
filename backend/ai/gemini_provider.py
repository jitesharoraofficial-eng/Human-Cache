"""
Gemini Provider implementation using the official Google Gemini API.
Uses modern models via standard HTTP requests with strict secret redaction,
bounded retries respecting Retry-After headers, quota/demand awareness,
and robust exception handling.
"""
import json
import logging
import re
import time
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, ValidationError

from backend.config import settings
from backend.ai.provider import BaseAIProvider
from backend.logging_config import sanitize_text

logger = logging.getLogger(__name__)


class GeminiProviderError(Exception):
    """Base exception for Gemini provider operations."""
    pass


class GeminiAuthError(GeminiProviderError):
    """Raised when authentication fails (HTTP 401/403)."""
    pass


class GeminiQuotaExceededError(GeminiProviderError):
    """Raised when API quota is exhausted (HTTP 429 quota)."""
    pass


class GeminiRateLimitError(GeminiProviderError):
    """Raised when request rate limit is exceeded (HTTP 429 RPM/RPD)."""
    pass


class GeminiServiceUnavailableError(GeminiProviderError):
    """Raised when upstream Gemini service is unavailable or high demand (HTTP 503)."""
    pass


class GeminiModelNotFoundError(GeminiProviderError):
    """Raised when requested model ID is invalid or deprecated (HTTP 404)."""
    pass


class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, embedding_model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        
        # Resolve active model, substituting deprecated/non-existent model names
        configured_model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
        obsolete_names = {"gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"}
        if configured_model in obsolete_names:
            configured_model = "gemini-3.8-flash"
        self.model = configured_model
        
        self.embedding_model = embedding_model or getattr(settings, "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_auth_headers(self) -> Dict[str, str]:
        """Provides secure header-based authentication, keeping secrets out of the request URL."""
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key or ""
        }

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 4096, temperature: float = 0.2) -> str:
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured. Provider unavailable.")

        # Candidate models prioritized by verified endpoint availability
        candidate_models = [self.model, "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]
        obsolete = {"gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"}
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m and m not in obsolete]))

        headers = self._get_auth_headers()
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        last_error = None
        for cur_model in candidate_models:
            url = f"{self.base_url}/models/{cur_model}:generateContent"

            for attempt in range(2):
                try:
                    with httpx.Client(timeout=30.0) as client:
                        response = client.post(url, headers=headers, json=payload)
                        
                        if response.status_code == 200:
                            data = response.json()
                            candidates = data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    self.model = cur_model
                                    return parts[0]["text"]

                        # 401/403 Authentication Failure — Fail fast, do NOT retry or cascade
                        if response.status_code in [401, 403]:
                            logger.error(f"Gemini authentication failed (HTTP {response.status_code}). Invalid API key.")
                            raise GeminiAuthError(f"Gemini authentication failed (HTTP {response.status_code}). Please verify your GEMINI_API_KEY.")

                        # 404 Model Not Found — Advance to next candidate immediately
                        if response.status_code == 404:
                            logger.warning(f"Model '{cur_model}' returned 404 (not found). Skipping to next candidate.")
                            last_error = f"Model {cur_model} not found (HTTP 404)"
                            break

                        # 429 Rate Limit / Quota Exhaustion
                        if response.status_code == 429:
                            err_body = response.text.lower()
                            if "quota" in err_body or "exhausted" in err_body:
                                logger.error(f"Gemini API quota exhausted (HTTP 429) on model '{cur_model}'. Halting fallback cascade.")
                                raise GeminiQuotaExceededError("Gemini API quota exhausted (HTTP 429). Please check your plan/quota or wait before retrying.")

                            retry_after = response.headers.get("retry-after")
                            wait_time = min(float(retry_after), 3.0) if retry_after and retry_after.replace('.', '', 1).isdigit() else 1.5
                            if attempt == 0:
                                logger.warning(f"Model '{cur_model}' rate limited (HTTP 429). Backing off {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.warning(f"Model '{cur_model}' rate limit persisted. Advancing candidate...")
                                last_error = f"HTTP 429 Rate Limit on {cur_model}"
                                break

                        # 500, 502, 503, 504 Temporary Server Error / Spikes in demand
                        if response.status_code in [500, 502, 503, 504]:
                            retry_after = response.headers.get("retry-after")
                            wait_time = min(float(retry_after), 2.0) if retry_after and retry_after.replace('.', '', 1).isdigit() else 1.0
                            if attempt == 0:
                                logger.warning(f"Model '{cur_model}' returned HTTP {response.status_code} (high demand/server error). Waiting {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.warning(f"Model '{cur_model}' returned HTTP {response.status_code} twice. Advancing candidate...")
                                last_error = f"HTTP {response.status_code} on {cur_model}"
                                break

                        clean_err = sanitize_text(response.text[:150])
                        logger.warning(f"Model '{cur_model}' returned unexpected HTTP {response.status_code}: {clean_err}")
                        last_error = f"HTTP {response.status_code}: {clean_err}"
                        break

                except (GeminiAuthError, GeminiQuotaExceededError):
                    raise
                except Exception as e:
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                    clean_e = sanitize_text(str(e))
                    logger.warning(f"Model '{cur_model}' request failed ({clean_e}). Advancing candidate...")
                    last_error = clean_e
                    break

        raise GeminiServiceUnavailableError(f"All Gemini model candidates failed. Last error: {last_error}")

    def generate_structured(self, prompt: str, schema_class: Any, system_prompt: Optional[str] = None, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Enforces structured JSON generation, strips Markdown code fences, validates via Pydantic,
        and provides 1 bounded repair retry if parsing fails.
        """
        schema_hint = ""
        if hasattr(schema_class, "model_json_schema"):
            schema_hint = f"\nExpected JSON Schema:\n{json.dumps(schema_class.model_json_schema())}\n"

        augmented_prompt = (
            f"{prompt}\n{schema_hint}\n"
            f"IMPORTANT: Respond ONLY with a single valid JSON object strictly complying with the requested schema. "
            f"Do not include explanations before or after the JSON."
        )

        for attempt in range(2):
            raw_text = self.generate_text(augmented_prompt, system_prompt=system_prompt, temperature=temperature)
            
            # Robust JSON extraction: look for json code block or raw outer braces
            clean_json = raw_text.strip()
            code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', clean_json)
            if code_block_match:
                clean_json = code_block_match.group(1).strip()
            else:
                brace_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', clean_json)
                if brace_match:
                    clean_json = brace_match.group(1).strip()

            try:
                parsed = json.loads(clean_json, strict=False)
            except json.JSONDecodeError:
                # Repair unescaped LaTeX backslashes (e.g. \Delta, \eta, \alpha, \c, \e)
                repaired = re.sub(r'\\([a-zA-Z])', r'\\\\\1', clean_json)
                try:
                    parsed = json.loads(repaired, strict=False)
                except Exception:
                    parsed = None

            try:
                if parsed is not None:
                    if issubclass(schema_class, BaseModel):
                        validated = schema_class.model_validate(parsed)
                        return validated.model_dump()
                    return parsed
                raise ValueError("JSON parse resulted in None")
            except (json.JSONDecodeError, ValidationError, ValueError) as err:
                logger.warning(f"Structured output parse error on attempt {attempt + 1}: {err}")
                if attempt == 0:
                    augmented_prompt = (
                        f"Your previous output failed to validate with error: {str(err)}.\n"
                        f"Previous output snippet: {clean_json[:300]}\n"
                        f"Fix the JSON structure and return ONLY the corrected, valid JSON object strictly adhering to the schema."
                    )
                else:
                    raise ValueError(f"Failed to generate valid structured response after repair attempt: {err}")

    def generate_embedding(self, text: str) -> List[float]:
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured. Embedding unavailable.")

        clean_text = text.strip()[:2048]
        if not clean_text:
            clean_text = "empty"

        url = f"{self.base_url}/models/{self.embedding_model}:embedContent"
        headers = self._get_auth_headers()
        payload = {
            "model": f"models/{self.embedding_model}",
            "content": {"parts": [{"text": clean_text}]}
        }

        for attempt in range(2):
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["embedding"]["values"]
                    if resp.status_code in [401, 403]:
                        raise GeminiAuthError(f"Gemini embedding authentication failed (HTTP {resp.status_code}).")
                    if resp.status_code == 429:
                        if "quota" in resp.text.lower():
                            raise GeminiQuotaExceededError("Gemini embedding quota exhausted (HTTP 429).")
                        if attempt == 0:
                            time.sleep(1.5)
                            continue
                        raise GeminiRateLimitError("Gemini embedding rate limited (HTTP 429).")
                    if resp.status_code in [500, 502, 503, 504] and attempt == 0:
                        time.sleep(1.0)
                        continue
                    raise GeminiProviderError(f"Gemini embedding error ({resp.status_code}): {sanitize_text(resp.text[:120])}")
            except (GeminiAuthError, GeminiQuotaExceededError, GeminiRateLimitError, GeminiProviderError):
                raise
            except Exception as e:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                clean_e = sanitize_text(str(e))
                logger.error(f"Gemini embedding failed: {clean_e}")
                raise GeminiProviderError(f"Gemini embedding failed: {clean_e}")

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured. Embedding unavailable.")
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        batch_size = 25
        url = f"{self.base_url}/models/{self.embedding_model}:batchEmbedContents"
        headers = self._get_auth_headers()

        with httpx.Client(timeout=35.0) as client:
            for i in range(0, len(texts), batch_size):
                chunk_slice = texts[i:i + batch_size]
                requests = []
                for t in chunk_slice:
                    clean_text = t.strip()[:2048] or "empty"
                    requests.append({
                        "model": f"models/{self.embedding_model}",
                        "content": {"parts": [{"text": clean_text}]}
                    })
                payload = {"requests": requests}
                
                succeeded = False
                for attempt in range(2):
                    try:
                        resp = client.post(url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            embs = [item["values"] for item in data.get("embeddings", [])]
                            all_embeddings.extend(embs)
                            succeeded = True
                            break
                        if resp.status_code in [401, 403]:
                            raise GeminiAuthError(f"Gemini batch embedding auth failed (HTTP {resp.status_code}).")
                        if resp.status_code == 429:
                            if "quota" in resp.text.lower():
                                raise GeminiQuotaExceededError("Gemini batch embedding quota exhausted (HTTP 429).")
                            if attempt == 0:
                                time.sleep(2.0)
                                continue
                            raise GeminiRateLimitError("Gemini batch embedding rate limit exceeded (HTTP 429).")
                        if resp.status_code in [500, 502, 503, 504] and attempt == 0:
                            time.sleep(1.5)
                            continue
                        logger.warning(f"batchEmbedContents returned {resp.status_code}: {sanitize_text(resp.text[:100])}")
                        break
                    except (GeminiAuthError, GeminiQuotaExceededError, GeminiRateLimitError):
                        raise
                    except Exception as e:
                        if attempt == 0:
                            time.sleep(1.0)
                            continue
                        logger.warning(f"batchEmbedContents failed: {sanitize_text(str(e))}")
                        break

                if not succeeded:
                    # Fallback to per-item embedding for this batch slice
                    for t in chunk_slice:
                        all_embeddings.append(self.generate_embedding(t))

        return all_embeddings
