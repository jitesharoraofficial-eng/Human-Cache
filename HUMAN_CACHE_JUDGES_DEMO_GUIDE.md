# HUMAN CACHE — JUDGES' LIVE DEMONSTRATION GUIDE
## STEP-BY-STEP, REPEATABLE EVALUATION SCRIPT

**Application:** Human Cache (Personal AI Knowledge Vault & Retention Engine)  
**Target Audience:** Competition Judges & Technical Reviewers  
**Prerequisites:** Backend server running on port 8000, Frontend running on port 3000.  

---

## 1. Quick Launch Instructions

### Terminal 1: Backend
```powershell
cd "c:\Users\manna\OneDrive\Attachments\Desktop\Human Cache Demo"
$env:PYTHONPATH="."
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health Check:* Open `http://127.0.0.1:8000/api/v1/health` in your browser. Verify `{"status": "healthy"}`.

### Terminal 2: Frontend
```powershell
cd "c:\Users\manna\OneDrive\Attachments\Desktop\Human Cache Demo\frontend"
npm run dev
```
*App URL:* Open `http://localhost:3000` in Google Chrome or any modern browser.

---

## 2. Demonstration Flow Overview

This 10-minute walkthrough showcases how Human Cache solves the cognitive retention gap by transforming raw capture into long-term mastery without manual overhead:

```
[1. Onboarding & Personalization]
             │
             ▼
[2. Smart External Capture & Auto-Categorization]
             │
             ▼
[3. Deep Conceptual Learn & High-Coverage Explanations]
             │
             ▼
[4. Adaptive Flashcard Decks & Section Landmarks]
             │
             ▼
[5. Simplified Knowledge Connectivity & Plain-English Bridges]
             │
             ▼
[6. Autonomous AI Memory Coach & 4-Way Retention Actions]
```

---

## 3. Step-by-Step Demonstration Script

### Step 1: Clean Registration & Pedagogical Onboarding
1. **Navigate:** Open `http://localhost:3000` and click **"Create an Account"**.
2. **Register:** Enter a unique email (e.g., `judge_demo@example.com`), password (`Password123!`), and name (`Judge Demo`).
3. **Onboarding Questionnaire:**
   - Select your primary learning goals: e.g., *"Professional Certification"*, *"Academic Research"*.
   - Select core focus topics: e.g., *"Cognitive Psychology"*, *"Strategic Management"*.
4. **Result to Point Out:** Notice that the system immediately curates initial categories in the sidebar without fabricating fake study history or streaks. The initial retention dashboard reflects an honest, clean zero-state.

---

### Step 2: Smart Share & AI Auto-Capture Inbox
1. **Navigate:** Click **"Smart Capture"** in the navigation bar.
2. **Demonstrate URL Capture:**
   - In the Capture Inbox input, enter an educational URL or paste an article text snippet.
   - Example Text Snippet:
     > *"Heuristics are cognitive shortcuts that ease the mental load of decision-making. Daniel Kahneman and Amos Tversky identified framing effects, where decisions change depending on whether options are presented as potential gains or losses. In strategic marketing, brand positioning leverages these framing heuristics to anchor consumer perceived value."*
3. **Click "Analyze & Capture":**
   - The AI evaluates the content and automatically suggests the category **"Cognitive Psychology"** (or **"Business"**) with an estimated confidence score.
   - Point out that the user has complete control: you can either accept the recommendation or choose any other category from the dropdown before confirming.
4. **Click "Confirm & Save":**
   - The item is saved directly into the user's secure knowledge vault and scheduled for conceptual chunking and embedding.

---

### Step 3: High-Coverage Explanations & Distinct Depths
1. **Navigate:** Click **"Learn"** in the sidebar.
2. **Select Topic:** Choose *"Cognitive Heuristics & Framing"*.
3. **Toggle Depth Selector:**
   - **Brief:** Switch to **Brief**. Observe a concise, high-yield summary focusing on fundamental definitions and key terms.
   - **Semi-Detailed:** Switch to **Semi-Detailed**. Notice the addition of real-world examples and practical applications.
   - **Detailed:** Switch to **Detailed**. Point out the conceptual coverage badge:
     - Outlines covered: *System 1 vs System 2, Framing Bias, Anchoring Heuristic*.
     - High-yield **Exam Traps** section highlighting subtle conceptual confusions.
4. **Key Judge Talking Point:** Explain how the *Concept Inventory Builder* inspects all source sections rather than retrieving only 4 superficial chunks.

---

### Step 4: Adaptive Flashcard Decks & Source Landmarks
1. **Navigate:** Click **"Flashcards"** in the sidebar.
2. **Generate Deck:** Click **"Generate Adaptive Deck"**.
3. **Observations for Judges:**
   - **Adaptive Sizing:** Rather than an arbitrary fixed set of 3 cards, the deck dynamically scales to the concept density of the material (e.g., 6–10 cards for multi-section documents).
   - **Section Landmarks:** Each card displays its originating section tag (e.g., `Section: Kahneman & Tversky Heuristics`).
   - **Quality Check:** Notice that all flashcard prompts are distinct; duplicate questions have been eliminated by the deduplication engine.

---

### Step 5: Simplified Knowledge Connectivity (Part 5 Highlight)
1. **Navigate:** Click **"Knowledge Graph"** in the top navigation.
2. **Observe Level 1: Simple (Default View):**
   - The graph displays only primary cluster hubs.
   - Labels and nodes do **not** overlap due to the deterministic orbital layout.
   - Hover over an edge: Instead of technical database keys, notice the **plain-English reason**:
     > *"Mastering Cognitive Bias is essential before studying Choice Architecture."*
3. **Toggle Progressive Disclosure Modes:**
   - Click the **"Explore"** pill: Subtopics and secondary prerequisites expand smoothly.
   - Click the **"Detailed"** pill: The entire academic topological graph with centrality metrics appears for deep research.
4. **Interactive Concept Side-Drawer:**
   - Click on the **"Marketing Strategy"** node.
   - An interactive side drawer slides open from the right displaying:
     - Real-time estimated memory retention percentage.
     - Direct clickable links to originating source documents.
     - One-click shortcuts to launch associated Quizzes, Flashcard Drills, or Mind Maps.
5. **Cross-Document Bridges:**
   - Navigate to **"Connectivity"** in the sidebar.
   - Filter by **"Cross-Document"**.
   - Show how the system discovered a conceptual bridge connecting a Psychology document to a Marketing document, grounded by exact source citations.

---

### Step 6: Autonomous AI Memory Coach & 4-Way User Actions
1. **Navigate:** Click the **"Bell Icon"** (Notifications) in the upper right header.
2. **Observe Autonomous Reminders:**
   - An intelligent notification appears: *"Your retention for Cognitive Heuristics has fallen to 62% — Review recommended."*
   - Mention that this reminder was scheduled autonomously by the background Ebbinghaus engine without requiring manual app visits.
3. **Demonstrate 4-Way User Action Contract:**
   - **Start:** One-click action that opens the pre-prepared quiz directly.
   - **Dismiss:** Acknowledges the reminder and marks it read.
   - **Remind Me Later:** Opens snooze options (1 hour, 3 hours, 24 hours, or custom date).
   - **No Need:** Suppresses future reminders for this concept while preserving it in your vault.

---

## 4. Troubleshooting & Fallback Guarantees

- **No Gemini API Key Configured?**
  - Human Cache includes a verified `DeterministicAIEngine` fallback that runs entirely locally, generating realistic, grounded educational material without crashing or failing.
- **Port Conflict?**
  - Backend runs on `127.0.0.1:8000`. If port 8000 is occupied, set `--port 8001` and update `NEXT_PUBLIC_API_URL=http://localhost:8001` in `frontend/.env.local`.
- **Database Reset Needed for Clean Run?**
  - Run `.\venv\Scripts\python.exe -c "from backend.database import init_db; init_db()"` to recreate schema tables if necessary.
