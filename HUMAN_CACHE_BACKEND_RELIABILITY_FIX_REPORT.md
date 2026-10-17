# HUMAN CACHE — BACKEND STARTUP & AI PROVIDER RELIABILITY FIX REPORT

**Date:** October 16, 2026  
**Roles:** Senior FastAPI Engineer, Gemini API Integration Specialist, Security Engineer, QA Lead  
**Scope:** Backend Startup, Concept Inventory Parsing, Gemini Provider Resilience, Secret Redaction, and Startup Safety  
**Status:** All 5 Operational & Security Issues Remediated and Verified | Database Intact  

---

## 1. Executive Summary

During backend startup and early runtime, the following critical issues occurred:
1. `Could not load inventory for doc ...: no such group` and `Error checking inventory for ...: no such group` repeatedly logged on document processing.
2. Upstream Gemini generation failed with HTTP 503 Service Unavailable (high demand spikes).
3. Upstream Gemini generation failed with HTTP 429 Too Many Requests (rate limits and quota exhaustion).
4. Gemini API keys and credentials were being exposed in HTTP request URLs and HTTPX client logs (`?key=...`).
5. AI generation requests were being triggered automatically at startup and on every 60-second scheduler loop, before the user initiated learning.

Each issue was investigated to its root cause, resolved in code, and verified with dedicated regression tests.

---

## 2. Root Cause Analysis & Technical Resolutions

### Task A — Inventory Regex IndexError: `no such group`

#### Root Cause:
In `backend/concept_inventory.py`, the heading detection list `HEADING_PATTERNS` contained:
```python
HEADING_PATTERNS = [
    re.compile(r'^(?:#{1,4}\s+|Chapter\s+\d+[:\s]+|[0-9]+\.[0-9]*\s+|Section\s+\d+[:\s]+)([A-Z][^\n]{2,70})', re.MULTILINE),
    re.compile(r'^[A-Z][A-Za-z0-9\s,\-]{2,40}:$', re.MULTILINE),  # <-- NO CAPTURING GROUP!
    re.compile(r'^\b([A-Z][A-Z\s0-9]{3,40})\b$', re.MULTILINE)
]
```
When `_extract_inventory_from_chunks` encountered section headings like `Introduction:` or `Overview:`, the second regex matched. However, the subsequent line unconditionally executed `sec_heading = m.group(1).strip()`. Because the second regex had 0 capturing groups, Python raised `IndexError: no such group`, logging:
- `backend/ai/generation.py`: `Could not load inventory for doc ...: no such group`
- `backend/ai/retrieval.py`: `Error checking inventory for ...: no such group`

#### Resolution:
1. **Added Capturing Group:** Updated `HEADING_PATTERNS[1]` to:
   ```python
   re.compile(r'^([A-Z][A-Za-z0-9\s,\-]{2,40}):$', re.MULTILINE)
   ```
2. **Defensive Group Indexing:** Guarded all pattern matching with `m.lastindex`:
   ```python
   sec_heading = (m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)).strip().rstrip(':')
   ```
   Applied identical defensive checks to definition, formula, and process regexes across `backend/concept_inventory.py` and `backend/extractor.py`.

---

### Task B — Gemini Provider Reliability & Model Hierarchy

#### Root Cause:
1. **Invalid Configured Model IDs:** `.env` and `backend/config.py` were configured with `GEMINI_MODEL="gemini-3.5-flash"`. Testing against the live Google Gemini REST API revealed that `gemini-3.5-flash` and `gemini-3.5-flash-lite` do not exist, causing initial requests to fail immediately with HTTP 404.
2. **Model State Differentiation:**
   Live endpoint inspection confirmed the current model statuses on the user's tier:
   - `gemini-3-flash-preview`: Active and healthy (returns HTTP 200 OK).
   - `gemini-flash-latest`, `gemini-3.8-flash`: Valid models subject to occasional demand spikes (HTTP 503).
   - `gemini-2.5-flash`, `gemini-2.5-pro`: Deprecated/unavailable to new tier users (HTTP 404).
3. **Flawed Retry & Fallback Cascading:**
   - 401/403 (Auth failure) was being retried instead of failing fast.
   - 429 (Quota exhaustion) was cascading through 4 other models, generating 4 additional 429 errors and worsening quota depletion.
   - 503 (Temporary demand spikes) did not parse the `Retry-After` header.
4. **Silent Canned Academic Content:**
   When all Gemini models failed, the application silently fell back to `DeterministicAIEngine`, masking provider outages from the user and UI.

#### Resolution:
1. **Configured Active Model:** Updated default `GEMINI_MODEL` in `.env` and `backend/config.py` to `gemini-3-flash-preview`. Automatically mapped any legacy `gemini-3.5-flash` references to `gemini-3-flash-preview`.
2. **Explicit Custom Exceptions:** Implemented structured exceptions in `backend/ai/gemini_provider.py`:
   - `GeminiAuthError` (401/403): Fails fast immediately with 0 retries and 0 cascading.
   - `GeminiQuotaExceededError` (429 quota): Detects quota exhaustion and halts cascading immediately.
   - `GeminiRateLimitError` (429 rate limit): Respects `Retry-After` and applies 1 bounded backoff retry.
   - `GeminiServiceUnavailableError` (503): Respects `Retry-After` (bounded to $\le 2.0$s), retries once, then advances candidate models.
   - `GeminiModelNotFoundError` (404): Skips directly to next candidate model without retrying the invalid model ID.
3. **Transparent Provider Error Reporting:**
   In `backend/ai/generation.py`, when `provider.is_available()` is True but upstream Gemini fails:
   - `explain_topic` returns `coverage_status: "provider_unavailable"` with a clear warning: `"⚠️ AI Explanation is temporarily unavailable due to upstream provider limits or high demand (HTTP 503/429). Please retry in a moment."`
   - `chat_with_tutor` returns `provider_unavailable: True` with an informative system notice rather than fabricated or generic academic templates.
   - `generate_quiz` and `generate_flashcards` raise clear `RuntimeError` describing upstream provider unavailability rather than silently returning pre-canned cards.

---

### Task C — Secret Redaction in URLs and Logs

#### Root Cause:
Requests in `backend/ai/gemini_provider.py` and `backend/ai_engine.py` appended the API key directly to the URL query string:
`https://generativelanguage.googleapis.com/v1beta/models/...:generateContent?key=AIzaSy...`
Because `httpx` and `httpcore` log request URLs at INFO level, the secret key was exposed in standard application logs and exception traces.

#### Resolution:
1. **Header-Based Authentication:**
   Removed `?key=...` from all request URLs (`generateContent`, `embedContent`, `batchEmbedContents`). All requests now supply credentials strictly via the official header:
   ```json
   {
     "Content-Type": "application/json",
     "x-goog-api-key": self.api_key
   }
   ```
2. **Centralized Secret Redaction Filter (`backend/logging_config.py`):**
   Implemented `SensitiveDataFilter(logging.Filter)` which intercepts and sanitizes:
   - URL query parameters matching `(?i)[?&](key|api_key|token|secret)=...` $\to$ `key=[REDACTED]`
   - Headers matching `(?i)x-goog-api-key[\s:=]+...` $\to$ `x-goog-api-key: [REDACTED]`
   - Authorization headers matching `(?i)Authorization[\s:=]+Bearer\s+...` $\to$ `Authorization: Bearer [REDACTED]`
   - Any raw occurrences of configured `GEMINI_API_KEY` or `SECRET_KEY`.
3. **HTTP Client Log Level Configuration:**
   Configured `httpx`, `httpcore`, and `urllib3` logger levels to `WARNING` in `setup_secure_logging()`, preventing automatic URL logging in standard execution.
4. **Unified Gateway:**
   Refactored `call_gemini_api` in `backend/ai_engine.py` to route through `GeminiProvider`, eliminating duplicate raw HTTP requests.

---

### Task D — Startup Safety & Unbounded Background AI Calls

#### Root Cause:
During startup in `backend/main.py`:
1. `on_startup` invoked `run_proactive_notification_cycle(db, DEMO_USER_ID)`.
2. Simultaneously, `memory_coach_scheduler.start()` launched a worker thread that executed `run_proactive_notification_cycle(db, user.id)` across all active users every 60 seconds.
3. Inside `run_proactive_notification_cycle`:
   For every topic with `estimated_retention < 0.70` or `status == "overdue"`, the cycle called `prepare_or_reuse_learning_resources(db, user_id, topic.id)`.
   If a quiz or flashcard deck did not exist yet for that topic, `prepare_or_reuse_learning_resources` called `rag_engine.generate_quiz(...)` and `rag_engine.generate_flashcards(...)`.
4. As a result, starting the backend immediately made 5–15 live LLM generation calls before any user logged in, instantly exhausting the free-tier quota and triggering 429 and 503 errors.

#### Resolution:
1. **Deferred Generation in Background Scans:**
   Added `auto_generate: bool = True` parameter to `prepare_or_reuse_learning_resources`:
   ```python
   def prepare_or_reuse_learning_resources(db, user_id, topic_id, auto_generate=True):
       ...
       if not auto_generate:
           return {
               "status": "ready" if (existing_quiz or existing_deck) else "deferred",
               "topic_id": topic_id,
               "topic_name": topic.canonical_name,
               "quiz_id": existing_quiz.id if existing_quiz else None,
               "deck_id": existing_deck.id if existing_deck else None,
               "action_url": f"/recall?topic_id={topic_id}" if existing_quiz else f"/learn?topic_id={topic_id}"
           }
   ```
2. **Decoupled Notification Engine:**
   In `backend/notification_engine.py`, `run_proactive_notification_cycle` now passes `auto_generate=False`. It computes memory decay mathematically and creates notifications linking to the topic, without generating quizzes or flashcards in the background.
3. **On-Demand Generation:**
   Quiz and flashcard generation is now deferred until the user explicitly initiates study (e.g. clicking the notification, opening the recall drill, or uploading new documents).
4. **Scheduler Warmup Delay:**
   Added a 10-second non-blocking warmup in `MemoryCoachScheduler._worker_loop` before the first evaluation, ensuring startup and database migrations complete without contention.

---

## 3. Files Modified & Created

| File | Change Description |
| :--- | :--- |
| `backend/concept_inventory.py` | Added capturing group to `HEADING_PATTERNS[1]`; added `m.lastindex` guards across heading, definition, formula, and process regexes. |
| `backend/extractor.py` | Added safe group fallback guards in `unit_chapter_pattern` loop. |
| `backend/config.py` | Updated default `GEMINI_MODEL` from `gemini-3.5-flash` to active `gemini-3-flash-preview`. |
| `.env` | Updated `GEMINI_MODEL` to `gemini-3-flash-preview`. |
| `backend/logging_config.py` | **NEW:** Created `SensitiveDataFilter`, `sanitize_text`, and `setup_secure_logging` for centralized credential redaction. |
| `backend/ai/gemini_provider.py` | Hardened with header-based auth (`x-goog-api-key`), custom exceptions (`GeminiAuthError`, `GeminiQuotaExceededError`, `GeminiServiceUnavailableError`), bounded retries with `Retry-After`, and valid model candidates. |
| `backend/ai_engine.py` | Unified `call_gemini_api` to route through hardened `GeminiProvider` rather than making raw URL requests. |
| `backend/ai/generation.py` | Added explicit provider unavailable error handling in `explain_topic`, `chat_with_tutor`, `generate_quiz`, and `generate_flashcards`. |
| `backend/resource_prep_service.py` | Added `auto_generate: bool = True` to `prepare_or_reuse_learning_resources`, allowing deferred resource generation. |
| `backend/notification_engine.py` | Updated `run_proactive_notification_cycle` to pass `auto_generate=False`, preventing background LLM calls. |
| `backend/scheduler.py` | Initialized `setup_secure_logging()`; added 10-second startup warmup in worker loop. |
| `backend/main.py` | Initialized `setup_secure_logging()` on startup. |
| `tests/test_startup_and_provider_reliability.py` | **NEW:** 10 regression tests covering inventory regex safety, auth failure, quota exhaustion, 503 backoff, secret redaction, and startup safety. |

---

## 4. Verification & Automated Test Results

### 1. Startup & Provider Reliability Regression Suite
All 10 tests in `tests/test_startup_and_provider_reliability.py` passed:
```text
tests/test_startup_and_provider_reliability.py::test_concept_inventory_regex_heading_patterns_safe PASSED [ 10%]
tests/test_startup_and_provider_reliability.py::test_concept_inventory_builder_end_to_end_no_such_group PASSED [ 20%]
tests/test_startup_and_provider_reliability.py::test_gemini_provider_auth_failure_raises_immediately PASSED [ 30%]
tests/test_startup_and_provider_reliability.py::test_gemini_provider_quota_exhaustion_raises_without_cascading PASSED [ 40%]
tests/test_startup_and_provider_reliability.py::test_gemini_provider_503_retries_with_backoff PASSED [ 50%]
tests/test_startup_and_provider_reliability.py::test_explain_topic_returns_provider_unavailable_on_failure PASSED [ 60%]
tests/test_startup_and_provider_reliability.py::test_secret_redaction_in_urls_and_headers PASSED [ 70%]
tests/test_startup_and_provider_reliability.py::test_sensitive_data_logging_filter PASSED [ 80%]
tests/test_startup_and_provider_reliability.py::test_startup_notification_cycle_does_not_trigger_ai_generation PASSED [ 90%]
tests/test_startup_and_provider_reliability.py::test_prepare_or_reuse_learning_resources_deferred_when_auto_generate_false PASSED [100%]
======================== 10 passed in 3.28s ========================
```

### 2. Full Regression Suite (Notifications, Upload Safety, Connectivity)
```text
====================== 28 passed, 23 warnings in 52.92s =======================
```

### 3. Pre-Phase-3 Document Coverage & Graph Suite
```text
======================= 6 passed in 120.92s =======================
```

### 4. Startup Smoke Test
```text
Testing FastAPI startup event...
Health response: 200 {'status': 'healthy', 'service': 'Human Cache API', 'llm_provider': 'gemini', 'storage': 'local-disk', 'timestamp': '2026-10-16T17:18:22.319794'}
FastAPI startup and shutdown executed cleanly!
```
- No `no such group` exceptions.
- Zero secret credentials in logs.
- Zero unprompted LLM requests on startup.

### 5. Frontend TypeScript Compilation
```bash
npx.cmd tsc --noEmit
# Exit Code: 0 (Zero type errors)
```

---

## 5. Remaining Provider Limitations & Operational Guidance

1. **Free-Tier Rate Limits (15 RPM):** The Gemini free-tier imposes a strict limit of 15 requests per minute. Deferring background generation until explicit user action prevents quota bursts, but rapid manual clicking across multiple topics within 60 seconds may still encounter temporary 429 delays. The bounded backoff handler will pause and retry safely.
2. **Upstream Service Spikes (503):** Google Gemini preview models experience periodic high-demand spikes. Our bounded retry handler with exponential backoff handles brief spikes gracefully and surfaces transparent notices if upstream capacity remains saturated.
3. **Paid API Invariant Preserved:** No paid models or billing configuration changes were introduced. All configurations remain within standard Developer Free-Tier specifications.
