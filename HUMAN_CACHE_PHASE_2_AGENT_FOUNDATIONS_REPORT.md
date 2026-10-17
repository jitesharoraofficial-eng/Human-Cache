# HUMAN CACHE — PHASE 2: AGENT CORE FOUNDATIONS REPORT

**Author:** Principal Agentic AI Architect & Full-Stack Lead  
**Target Milestone:** Phase 2 Completion — Agent Core Foundations  
**Application:** Human Cache (Microsoft Hackathon AI Learning Agent)  
**Date:** October 15, 2026  
**Status:** **PHASE 2 COMPLETE & VERIFIED** (99/99 Automated Tests Passing, 100% Production Build Pass)

---

## 1. Executive Summary

Phase 2 establishes the foundational conversational and tool-execution backbone for Human Cache’s evolution into an autonomous, personalized AI Learning Agent. 

All Phase 2 requirements have been successfully implemented with zero data loss, strict database isolation, additive schema migrations, typed tool guardrails, multi-turn conversational persistence, multi-lingual (English, Hindi, Hinglish) understanding, and clear provenance citation distinction.

### Key Achievements:
1. **Zero Data Loss & Additive Migration:** Pre-migration verified backup created (`human_cache.db.bak_phase2_pre`). Alembic additive migration (`fa10ec3b92c4`) applied cleanly to create `agent_conversations` and `agent_messages`. All 207 existing users and 278 documents remain completely intact.
2. **Persistent Conversation Threads:** Complete thread lifecycle (create, fetch, multi-turn message append, update title/archive, delete) with strict user isolation, cascade deletes, and bounded 10-turn context windows.
3. **Context-Aware Learner Assembler:** Dynamic prompt compilation combining onboarding preferences, target exams, retention states, conversation turns, and retrieved document chunks with hybrid dense + lexical filtering.
4. **Strict Source Grounding & Anti-Hallucination:** Grounded citations explicitly distinguish `uploaded_document` (with document title, page number, section heading, snippet preview) from `general_knowledge` fallback. The agent explicitly declines to hallucinate exams, notes, or progress that do not exist.
5. **Typed, Permission-Aware Tool Registry:** Pydantic-validated registry exposing 5 wrapped read/generate learning tools (`retrieve_knowledge_chunks`, `generate_practice_quiz`, `generate_adaptive_flashcards`, `generate_mind_map`, `query_learner_retention`) and 2 consequential tools (`modify_study_schedule`, `delete_document`) requiring explicit user confirmation.
6. **Upgraded Frontend Interface:** `PersistentAITutor.tsx` and `api.ts` upgraded with multi-turn chat persistence across refreshes, session history drawer, new thread button, citation chips, model provenance metadata, and responsive mobile layout.
7. **Complete Quality Verification:** 99 of 99 pytest test cases passing (including 9 comprehensive agent core integration tests), and Next.js Turbopack production build passing cleanly.

---

## 2. Database Safety & Additive Migration Audit

### 2.1 Database Path and Backup Verification
- **Target Database:** `c:\Users\manna\OneDrive\Attachments\Desktop\Human Cache Demo\human_cache.db`
- **Pre-Migration Backup:** `human_cache.db.bak_phase2_pre` (29,044,736 bytes)
- **Live User Count:** 207 users (verified before and after migration)
- **Live Document Count:** 278 documents (verified before and after migration)

### 2.2 Additive Migration Details
- **Migration Script:** `alembic/versions/fa10ec3b92c4_add_agent_conversations_and_messages.py`
- **Down Revision:** `4cf1cb76eeeb` (Phase 1 Web Push subscriptions)
- **Tables Added:**
  1. `agent_conversations`:
     - `id` (VARCHAR(36), PK)
     - `user_id` (VARCHAR(36), FK -> users.id, indexed, ON DELETE CASCADE)
     - `title` (VARCHAR(255), default "New Study Session")
     - `target_exam` (VARCHAR(100), nullable)
     - `subject` (VARCHAR(100), nullable)
     - `is_archived` (BOOLEAN, default False)
     - `created_at` (DATETIME, default utcnow)
     - `updated_at` (DATETIME, default utcnow, indexed)
  2. `agent_messages`:
     - `id` (VARCHAR(36), PK)
     - `conversation_id` (VARCHAR(36), FK -> agent_conversations.id, indexed, ON DELETE CASCADE)
     - `role` (VARCHAR(20), check in 'user', 'assistant', 'system')
     - `content` (TEXT, non-null)
     - `citations_json` (TEXT, nullable, serialized JSON list of `AgentCitation`)
     - `meta_json` (TEXT, nullable, serialized JSON dict with model, latency, tokens, language)
     - `created_at` (DATETIME, default utcnow, indexed)

---

## 3. Persistent Conversation Architecture & REST APIs

### 3.1 REST API Contracts (`/api/v1/agent`)

| HTTP Method | Endpoint | Description | Auth / Scoping |
|---|---|---|---|
| `GET` | `/api/v1/agent/conversations` | List user conversation threads with pagination (`skip`, `limit`) | User scoped |
| `POST` | `/api/v1/agent/conversations` | Create a new conversation thread | User scoped |
| `GET` | `/api/v1/agent/conversations/{id}` | Get conversation thread details and full message turn history | User scoped (404 on cross-user access) |
| `PATCH` | `/api/v1/agent/conversations/{id}` | Rename title or update archive state | User scoped |
| `DELETE` | `/api/v1/agent/conversations/{id}` | Delete conversation thread (cascade deletes messages) | User scoped |
| `POST` | `/api/v1/agent/conversations/{id}/messages` | Post a user message turn and generate assistant reply turn | User scoped |
| `GET` | `/api/v1/agent/tools` | List all available registered agent tools and schemas | Authenticated user |
| `POST` | `/api/v1/agent/tools/{tool_name}/execute` | Execute a tool with Pydantic argument validation | Scoped to caller user id |

### 3.2 Backward Compatibility
The legacy `/api/v1/tutor/chat` endpoint is fully preserved. It automatically interfaces with the new `AgentConversationService` and `LearnerContextAssembler` under the hood, delivering grounded responses with citations without breaking legacy clients.

---

## 4. Context Assembler & Multilingual Prompt Engineering

### 4.1 Architecture (`backend/agent/context.py`)
`LearnerContextAssembler` pulls together:
1. **Learner Onboarding Profile:** Roles, target learning goals, preferred explanation depth, teaching styles.
2. **Upcoming Exam Constraints:** Scheduled exams with days-remaining counts.
3. **Memory Retention States:** Identifies concepts marked as `unlearned` or `review_due` to steer tutor explanations.
4. **Bounded History Window:** Bounded to the last 10 turns (5 user / 5 assistant) to prevent context bloat and runaway token consumption.
5. **Grounded Source Retrieval:** User-isolated RAG chunks filtered through a dual dense + lexical validation stage.

### 4.2 Multi-Lingual Understanding (English, Hindi & Hinglish)
The prompt instructions equip the agent to naturally understand:
- English: Standard academic and conceptual queries.
- Hindi (Devanagari): Direct Hindi conceptual explanations.
- Conversational Hinglish: Technical mixed vernacular commonly used by Indian students (e.g., *"Mujhe Bernoulli's equation ka concept samjhao, pressure gradient kaise change hota hai?"*).
The agent responds in the learner's chosen language or natural code-mixed vernacular while keeping scientific symbols, formulas, and terminology intact.

### 4.3 Provenance & Anti-Hallucination Guardrails
- **Uploaded Document Match:** Attributed with `source_type="uploaded_document"`, document title, page number, and source snippet.
- **General Knowledge Fallback:** Attributed with `source_type="general_knowledge"`, document title="AI General Knowledge", locator="Foundational Model Knowledge".
- **Anti-Hallucination:** Explicitly prohibited from fabricating study notes, quiz scores, or dates. If a learner asks about an unuploaded topic, the agent answers from foundational knowledge and prompts the user to upload related notes.

---

## 5. Typed Tool Registry & Safety Guardrails

### 5.1 Registered Tools (`backend/agent/tools.py`)

| Tool Name | Type | Input Arguments | Consequential? | Confirmation Required? |
|---|---|---|---|---|
| `retrieve_knowledge_chunks` | Read | `query: str`, `top_k: int = 4`, `document_ids: Optional[List[str]]` | No | No |
| `generate_practice_quiz` | Generate | `topic_ids: Optional[List[str]]`, `question_count: int = 3`, `difficulty: str = "medium"` | No | No |
| `generate_adaptive_flashcards` | Generate | `topic_id: str`, `detail_level: str = "semi-detailed"`, `card_count: int = 5` | No | No |
| `generate_mind_map` | Generate | `central_topic: str`, `detail_level: str = "semi-detailed"` | No | No |
| `query_learner_retention` | Read | `min_retention: float = 0.0`, `max_retention: float = 1.0` | No | No |
| `modify_study_schedule` | Action | `exam_id: str`, `new_exam_date: str`, `reason: Optional[str]` | **Yes** | **Yes (`user_confirmed=True`)** |
| `delete_document` | Action | `document_id: str`, `reason: Optional[str]` | **Yes** | **Yes (`user_confirmed=True`)** |

### 5.2 Consequential Safety Guardrail
Any invocation of a consequential tool without `user_confirmed: true` is intercepted by the registry, returning a safety warning payload:
```json
{
  "status": "confirmation_required",
  "message": "Action 'modify_study_schedule' is consequential and requires explicit user confirmation.",
  "required_confirmation": true
}
```

---

## 6. Frontend AI Tutor Transformation

### 6.1 Upgraded Files
- `frontend/src/lib/api.ts`: Added typed API methods for agent conversations, messages, and tools.
- `frontend/src/components/PersistentAITutor.tsx`: Completely rebuilt from an ephemeral chat widget into a multi-turn, persistent AI Learning Agent assistant.

### 6.2 Frontend Features Implemented
- **Persistent Threads:** Seamlessly loads previous sessions and persists active conversation across page reloads via `localStorage`.
- **Sessions Drawer:** Header toggle opens a slide-down session browser displaying all previous study sessions with message counts and dates.
- **"+ New Thread" Action:** One-click creation of a fresh study session.
- **Thread Management:** Instant deletion of threads with optimistic UI updates.
- **Rich Source Attribution:** Clean chip badges distinguishing uploaded document sources (with page and locator tooltips) from general AI knowledge.
- **Markdown & Code Rendering:** Built-in `MarkdownRenderer` with KaTeX and code blocks.
- **Responsive Layout:** Adaptive styling that scales comfortably on mobile screens (`fixed inset-x-3 bottom-3 top-16`) and desktop monitors (`sm:w-[440px] sm:h-[620px]`).

---

## 7. Verification & Automated Test Results

### 7.1 Agent Core Regression Suite (`tests/test_agent_core.py`)
All 9 automated integration tests passed:
- `test_conversation_thread_lifecycle`: Creates thread, verifies multi-turn conversation persistence across turns and requests.
- `test_cross_user_conversation_isolation`: Verifies User B cannot access User A's conversation threads or message turns (404/403 enforced).
- `test_conversation_rename_archive_and_delete`: Verifies updating titles, archiving, and cascade deletion.
- `test_hinglish_and_multilingual_context`: Verifies conversational Hinglish input and multilingual instruction handling.
- `test_rag_provenance_citations`: Verifies strict distinction between uploaded notes citations and general knowledge citations.
- `test_tool_registry_inspection_and_execution`: Verifies registry tool listing and safe execution of `query_learner_retention` and `retrieve_knowledge_chunks`.
- `test_tool_registry_invalid_arguments_rejection`: Verifies Pydantic schema validation rejects malformed tool inputs with 422.
- `test_consequential_tool_safeguard`: Verifies consequential tools are rejected without explicit confirmation.
- `test_tutor_chat_backward_compatibility`: Verifies legacy `/api/v1/tutor/chat` endpoint functions with citations.

### 7.2 Full Test Suite Results
```text
================= 99 passed, 80 warnings in 182.67s (0:03:02) =================
```
100% of all 99 automated test cases in the Human Cache test suite pass cleanly against isolated test fixtures.

### 7.3 Frontend Production Build
```text
▲ Next.js 16.4.0 (Turbopack)
✓ Compiled successfully in 6.6s
✓ Finished TypeScript in 4.8s
✓ Generating static pages using 5 workers (4/4) in 1202ms
✓ Finalizing page optimization ...
Route (app)
┌ ○ /
└ ○ /_not-found
```
Zero TypeScript compiler errors or Turbopack bundling warnings.

---

## 8. Manual Verification Checklist

Follow this checklist to manually verify Phase 2 features in the browser:

1. **Launch Environment:**
   - Backend: `.\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
   - Frontend: `npm run dev` in `frontend/` (or run production build with `npm run start`)
2. **Persistent Conversation Across Refresh:**
   - Click **"Ask AI Agent"** floating pill in bottom-right corner.
   - Type *"Explain Newton's third law of motion"* and send.
   - Observe response with citation pill.
   - Refresh the browser (F5).
   - Click **"Ask AI Agent"** again: Observe that the previous session and all message turns are immediately restored.
3. **Multi-Turn Follow-Up & Hinglish:**
   - Type *"Iska ek practical example de do rocket propulsion ke context me"* (Hinglish).
   - Verify the assistant understands the context of Newton's third law from the previous turn and explains rocket propulsion naturally in code-mixed Hinglish/English.
4. **Session Drawer & New Thread:**
   - Click the session history icon (`Layers` icon) in the tutor header.
   - Verify the current session is listed.
   - Click **"+ New"** in the drawer header: Verify a fresh study thread starts.
   - Switch back to the previous session: Verify older messages load.
5. **Grounded Source Attribution:**
   - Ask a question relating to an uploaded document (e.g. Bernoulli's principle or market research): Observe the green document citation chip with page number.
   - Ask an unrelated query (e.g. Renaissance art): Observe the slate *"AI General Knowledge"* chip.

---

## 9. Phase 3 Transition Readiness

Phase 2 establishes all structural agent primitives required for Phase 3:
- **Conversation State Management:** Thread and message models ready for autonomous multi-turn loops.
- **Tool Foundation:** All existing learning tools wrapped with typed schemas and safety guardrails.
- **Grounding Layer:** Context assembler ready to receive autonomous planner goals and reflection chains.

### Boundaries Maintained:
- **No Phase 3 Orchestration Yet:** Autonomous multi-step loops and dynamic intent routers have NOT been activated.
- **No Syllabus-Only Engine Yet:** Dedicated syllabus intelligence engine reserved for Phase 4.
- **No Cloud/Azure Migration Yet:** Local Gemini integration preserved as default; database remains SQLite.

**Phase 2 is officially complete, verified, and ready for review.**
