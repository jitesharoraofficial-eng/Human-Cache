"""
Logging & Secret Redaction Configuration for Human Cache.

Ensures credentials, API keys, tokens, and authorization headers are never logged
in plain text across application logs, HTTPX client logs, or exception traces.
"""
import re
import logging
from typing import Optional
from backend.config import settings

class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that intercepts LogRecord messages and arguments to redact
    sensitive query parameters, authorization headers, and raw API keys.
    """
    def __init__(self, sensitive_keys: Optional[list] = None):
        super().__init__()
        self.sensitive_keys = sensitive_keys or []
        # Add configured keys if present
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) >= 6:
            self.sensitive_keys.append(settings.GEMINI_API_KEY)
        if settings.SECRET_KEY and len(settings.SECRET_KEY) >= 6:
            self.sensitive_keys.append(settings.SECRET_KEY)

        self.patterns = [
            # URL query params: ?key=..., &key=..., &api_key=...
            (re.compile(r'(?i)([?&])(key|api_key|token|secret|access_token)=([^&\s"\'>]+)'), r'\1\2=[REDACTED]'),
            # Headers: x-goog-api-key: ...
            (re.compile(r'(?i)(x-goog-api-key[\s:=]+)([\'"]?[a-zA-Z0-9_\-]+[\'"]?)'), r'\1[REDACTED]'),
            # Headers: Authorization: Bearer ...
            (re.compile(r'(?i)(Authorization[\s:=]+Bearer\s+)([a-zA-Z0-9_\.\-]+)'), r'\1[REDACTED]'),
            # Inline key=...
            (re.compile(r'(?i)\b(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*[\'"][^\'"]+[\'"]'), r'\1="[REDACTED]"'),
        ]

    def sanitize(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        res = text
        for secret in self.sensitive_keys:
            if secret and len(secret) >= 6 and secret in res:
                res = res.replace(secret, "[REDACTED]")
        for pat, repl in self.patterns:
            res = pat.sub(repl, res)
        return res

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.sanitize(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.sanitize(v) if isinstance(v, str) else v for v in record.args)
        return True


def sanitize_text(text: str) -> str:
    """Helper utility to sanitize any string before inclusion in output or logs."""
    flt = SensitiveDataFilter()
    return flt.sanitize(text)


def setup_secure_logging():
    """
    Attaches the sensitive data filter to root and third-party HTTP loggers,
    and sets HTTP client log levels to WARNING to prevent URL query string exposure.
    """
    flt = SensitiveDataFilter()
    
    # Secure root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(flt)
    for handler in root_logger.handlers:
        handler.addFilter(flt)

    # Secure HTTPX and HTTPCORE loggers
    for logger_name in ["httpx", "httpcore", "urllib3", "human_cache", "concept_inventory"]:
        l = logging.getLogger(logger_name)
        l.addFilter(flt)
        for h in l.handlers:
            h.addFilter(flt)
        if logger_name in ["httpx", "httpcore", "urllib3"]:
            # Suppress default request-level info dumps that log raw URLs
            l.setLevel(logging.WARNING)
