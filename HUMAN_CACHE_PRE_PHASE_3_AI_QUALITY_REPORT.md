# Human Cache — Pre-Phase 3 AI Quality, RAG Relevance & Extension Repair Report

**Date:** October 15, 2026  
**Status:** Completed & Verified  
**Baseline Rollback Point:** `human_cache.db.bak_pre_phase3_repair` (Verified: 30,687,232 bytes, intact)  
**Test Suite Status:** 104 / 104 Unit & Integration Tests Passing (100%)  
**Frontend Build Status:** Next.js 16.4.0 Turbopack Production Build Successful (0 TypeScript or JSX Errors)

---

## 1. Executive Summary & Root Cause Analysis

Manual user testing following Phase 2 identified critical functional and UX defects across AI tutoring quality, RAG relevance, onboarding personalization, browser extension ingestion, and console noise. Our deep code audit and live runtime inspection uncovered the following concrete root causes:

1. **Silent Fallback to Deterministic Canned Templates (Gemini HTTP 429 Quota Exhaustion):**  
   - *Root Cause:* The configured models `gemini-3.8-flash` and `gemini-flash-latest` had completely exhausted their free-tier request quota on the user's active API key, throwing `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED`.  
   - *Behavior:* Because `GeminiProvider.generate()` caught exceptions and returned fallback text without transient retries or active candidate model fallback, the system silently degraded into returning hardcoded canned explanations.  
   - *Resolution:* Verified active models on the key: `gemini-3.5-flash` and `gemini-3.5-flash-lite` have active quota and respond with low latency (<1.2s). Configured `gemini-3.5-flash` as primary, added candidate model failover (`gemini-3.5-flash` -> `gemini-3.5-flash-lite` -> `gemini-flash-latest`), and implemented exponential backoff retries.

2. **Personalization Misalignment & False "History" Subject Injection:**  
   - *Root Cause:* `getRecommendedSubjects()` in `frontend/src/lib/personalization.ts` lacked parameters for `collegeDegree` and `collegeField`, and contained an unconditional fallback `recommended.add("History")` whenever no matches occurred. When an engineering student selected `B.Tech (Computer Science & Engineering)`, zero keyword matches were made against standard school subjects, causing the system to inject "History" into their profile and dashboard focus.  
   - *Resolution:* Added `collegeDegree` and `collegeField` to `getRecommendedSubjects()`, prioritized engineering subjects (`Computer Science`, `Mathematics`, `Physics`, `Artificial Intelligence`, `Engineering Foundations`), removed humanities precedence over engineering streams, and exposed all persisted profile attributes (`college_degree`, `college_field`, `academic_year`, `custom_instructions`) directly to the LLM agent prompt.

3. **Browser Extension HTTP 403 Ingestion Failure (Wikipedia & Cloudflare Blocks):**  
   - *Root Cause:* Server-side scraping in `backend/url_capture_service.py` sent a bot User-Agent string (`HumanCacheBot/1.0`) without required contact identifiers, violating Wikimedia's automated agent policy and triggering HTTP 403 Forbidden. User also lacked the ability to save the rendered page when servers blocked automated retrieval.  
   - *Resolution:* Updated User-Agent to standards-compliant `HumanCache/1.0 (https://humancache.ai; contact@humancache.ai) EducationalBot/1.0`. Updated `extension/content.js` and `extension/popup.js` to extract rendered article text directly from the active tab and send it as `page_content` in `CaptureUrlRequest`. If server-side fetch receives 403, the backend safely falls back to the client-provided content without bypassing SSRF network validations.

4. **Monolithic Page Chunking & Cross-Document Contamination:**  
   - *Root Cause:* In `backend/extractor.py`, `chunk_pages_and_text` dumped entire multi-thousand character pages as single giant chunks whenever multi-page documents were uploaded. In `backend/ai/generation.py`, endpoints did not resolve topic-to-document relationships, causing semantic retrieval to search across all uploaded files belonging to the user and contaminating engineering topics with unrelated humanities notes.  
   - *Resolution:* Implemented document-aware hierarchical chunking (Units -> Chapters -> Sections -> Subtopics) producing 500-1100 character semantic chunks. Linked `Topic` to `DocumentTopic` to enforce topic-scoped retrieval, preventing cross-document contamination.

5. **Missing Automatic Study Resource Preparation:**  
   - *Root Cause:* Uploading a document only extracted graph nodes without proactively preparing recall quizzes, flashcard decks, summary notes, or mind maps.  
   - *Resolution:* Created `auto_prepare_document_learning_suite()` in `backend/resource_prep_service.py` and hooked it into FastAPI `BackgroundTasks` in `upload_document` and `confirm_capture`.

6. **Frontend Console Warnings & Share Target Manifest:**  
   - *Root Cause:* React Flow lacked a registered custom node component for type `topicNode`, web manifest lacked `enctype` in `share_target`, and dummy VAPID 65-byte zero buffers triggered `DOMException` in Chrome.  
   - *Resolution:* Registered `TopicNode` with handles in `nodeTypes`, added `"enctype": "application/x-www-form-urlencoded"`, and removed the invalid dummy key buffer.

---

## 2. Detailed Technical Fixes

### A. Gemini Provider Reliability & Structured Output
- **Model Configuration:** Configured default model `gemini-3.5-flash` in `backend/config.py` and `.env`.
- **Failover Candidates:** `[self.model, "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]`.
- **Transient Retry:** 2-attempt backoff on HTTP 429, 500, 503, and network timeouts.
- **Structured JSON Parsing:** Added markdown block regex extraction (`r'```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```'`) with schema prompt hints, preventing Pydantic schema validation failures.

### B. Context Assembly & Personalization Engine
- **Profile Fields Exposed:** In `backend/agent/context.py`, the prompt assembler extracts and injects:
  - `college_degree` and `college_field` (e.g., "B.Tech in Computer Science & Engineering")
  - `class_grade` and `academic_year`
  - `profession_role` and `profession_industry`
  - `subjects_of_interest` and `custom_subjects`
  - `custom_instructions`
- **Specific Directives:**
  - When asked *"What do you know about my learning preferences?"*, the AI Agent responds by summarizing the learner's actual profile fields without generic apologies.
  - When asked academic questions (e.g., *"Explain Newton's third law in simple words"*), provides structured, intuitive explanations.
  - When asked follow-ups in Hinglish (e.g., *"Ab iska rocket wala example samjhao"*), seamlessly transitions to crisp Hinglish explaining action-reaction propulsion.

### C. Browser Extension & Safe In-Tab Capture Fallback
- **Wikimedia/Bot Policy Compliance:** Updated headers in `backend/url_capture_service.py` with standard contact URI.
- **Client-Provided Content Fallback:**
  - Extended `CaptureUrlRequest` in `backend/schemas.py` with `title` and `page_content`.
  - In `extension/content.js`, added `getPageContent` message listener extracting clean article text up to 100k chars.
  - In `extension/popup.js`, actively queries the tab for rendered content before submitting.
  - In `backend/main.py` (`capture_url`), if server fetch returns 403 or anti-bot block, falls back to `page_content` without SSRF bypass.

### D. Document-Aware Hierarchy & Topic-Scoped RAG
- **Hierarchical Parsing in `backend/extractor.py`:**
  - Detects `Unit <num>`, `Chapter <num>`, `Section <num>`, and formal headers.
  - Splits paragraphs into bounded 500-1100 character chunks with sentence-boundary preservation.
  - Each chunk preserves `page_number` and `section_heading`.
- **Topic-Scoped Retrieval in `backend/ai/generation.py`:**
  - `explain_topic()`, `generate_quiz()`, and `generate_flashcards()` resolve `DocumentTopic` IDs for the given topic.
  - Retrieval strictly filters against those document IDs, preventing cross-document contamination.
  - If no document chunks match, outputs honest citation: `"General AI Knowledge (No matching document chunks found)"` without fabricating page citations.

### E. Upload-Triggered Resource Preparation
- **Service:** `auto_prepare_document_learning_suite(db, user_id, document_id)` in `backend/resource_prep_service.py`.
- **Idempotent Artifacts Created:**
  1. Initial Summary Note (`Note` with `source_type="auto_summary"`).
  2. 3-question drill quiz (`Quiz`).
  3. Adaptive flashcards deck (`FlashcardDeck` with 3-5 cards).
  4. Interactive concept mind map (`MindMap`).
- **Trigger:** Dispatched via FastAPI `BackgroundTasks` in `upload_document` and `confirm_capture`.

### F. Console Warnings & UI Cleanliness
- **React Flow Warning:** Added custom `TopicNode` with top/bottom handles and passed `nodeTypes={{ topicNode: TopicNode }}` to `<ReactFlow />` in `frontend/src/components/KnowledgeGraphView.tsx`.
- **Web Manifest Warning:** Added `"enctype": "application/x-www-form-urlencoded"` to `share_target` in `frontend/public/manifest.json`.
- **Push Notification Cleanup:** Replaced dummy 65-byte zero array with clean browser notification registration in `frontend/src/components/SettingsView.tsx`.

---

## 3. Verification & Test Results

### Automated Backend Tests
- **Dedicated Repair Suite:** `tests/test_ai_quality_and_repair.py` (5 tests, all PASSED).
- **Full Suite Run:** `pytest -v` across all 15 test files:
  - `test_agent_core.py` — PASSED
  - `test_ai_and_rag_engine.py` — PASSED
  - `test_ai_quality_and_repair.py` — PASSED
  - `test_auth_and_isolation.py` — PASSED
  - `test_capture_safety.py` — PASSED
  - `test_core.py` — PASSED
  - `test_coverage_and_adaptive_flashcards.py` — PASSED
  - `test_e2e_personalization_flow.py` — PASSED
  - `test_extension_manifest.py` — PASSED
  - `test_mind_maps.py` — PASSED
  - `test_notifications.py` — PASSED
  - `test_personalization_focus.py` — PASSED
  - `test_proactive_notifications.py` — PASSED
  - `test_simplified_connectivity_and_part5.py` — PASSED
  - `test_upload_safety.py` — PASSED
- **Total:** `104 passed, 0 failed` (100% pass rate).

### Frontend Build Verification
- Command: `cmd.exe /c "npm run build"` in `frontend/`
- Output: `Next.js 16.4.0 (Turbopack) Compiled successfully in 3.1s`. 0 errors.

---

## 4. Manual Verification Walkthrough for the User

To verify the repairs end-to-end:

1. **Verify AI Tutor Explanations & Follow-ups:**
   - Log into Human Cache and navigate to **AI Tutor** (`/tutor` or conversation drawer).
   - Enter: *"Explain Newton's third law in simple words."*
     - *Expected:* Clean, intuitive physics explanation with action-reaction pairs (e.g. walking on earth, swimmer pushing water).
   - Follow-up: *"Ab iska rocket wala example samjhao."*
     - *Expected:* Responds in natural conversational Hinglish explaining exhaust gases pushing downward and thrust accelerating the rocket upward.
   - Profile Inquiry: *"What do you know about my learning preferences?"*
     - *Expected:* Accurately recites your degree (e.g. B.Tech), branch, target goals, and depth preferences.

2. **Verify PDF Upload & Topic-Scoped RAG:**
   - Upload a PDF covering a specific subject (e.g., Physics or Computer Science).
   - Check the **Notes**, **Quizzes**, **Flashcards**, and **Mind Maps** tabs:
     - Notice the automatically generated summary note, initial 3-question drill quiz, and initial mind map created by the background task.
   - Ask the AI Tutor questions specific to that document:
     - *Expected:* Citations display genuine document filename, section heading, and page number without hallucinations or bleed from unrelated documents.

3. **Verify Wikipedia Capture via Extension:**
   - Open Wikipedia in Chrome (e.g., an article on Thermodynamics).
   - Click the Human Cache Extension popup and click **Save Page to Human Cache**.
   - *Expected:* Successfully captures without HTTP 403 error, suggesting appropriate category.

4. **Verify Clean Console:**
   - Open Browser Developer Tools (F12) -> Console.
   - Navigate to **Knowledge Graph** (`/knowledge-graph`): No `topicNode` missing warnings.
   - Navigate to **Settings** (`/settings`): No `DOMException` or `VAPID` errors.
