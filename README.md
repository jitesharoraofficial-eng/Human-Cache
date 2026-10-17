# 🧠 Human Cache

**AI-Powered Personal Learning, Knowledge Graph, Active-Recall & Memory Management Platform**

> Human Cache is an intelligent personal second brain and proactive learning assistant. It unifies uploaded materials, conceptual knowledge graphs, grounded AI tutoring, active-recall quizzes, spaced repetition memory decay tracking, and automated exam revision planning into a single integrated platform.

---

## 🌟 The Core Human Cache Loop

```
CAPTURE → EXTRACT → CONNECT → UNDERSTAND → LEARN → RECALL → TRACK MEMORY → REVISE
```

---

## 🚀 Live Demo Quickstart

### 1. Requirements
- **Python**: 3.11+
- **Node.js**: 18+ and `npm`

### 2. Backend Startup
From the project root:
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1   # or source venv/bin/activate on macOS/Linux

# Run the FastAPI server
uvicorn backend.main:app --port 8000 --host 127.0.0.1
```
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation & Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 3. Frontend Startup
Open a second terminal:
```powershell
cd frontend
npm run dev
```
- **Web App**: [http://localhost:3000](http://localhost:3000)

---

## 🔑 AI Provider Options (Zero-Cost / Offline Demo Mode)

Human Cache runs **100% out of the box** without requiring any paid API keys:
- **Default Mode**: High-yield deterministic academic engine with real document extraction, concept discovery, keyword clustering, and grounded explanations.
- **Live Gemini Integration**: Simply add your key in `.env` or set `GEMINI_API_KEY="your-key-here"`. The system will automatically detect and route synthesis through Google Gemini.

---

## 🧪 Interactive Hackathon Walkthrough

Follow this sequence to experience the full end-to-end journey:

1. **Dashboard Overview**:
   - Open [http://localhost:3000](http://localhost:3000).
   - View retention averages, review-due queues, upcoming exams, and today's scheduled revision tasks.
2. **Categories & Uploads**:
   - Ingest real PDFs, DOCX, Markdown, or raw text.
   - Watch the extraction pipeline create source chunks and discover canonical topics.
3. **Interactive Knowledge Graph**:
   - Explore the NetworkX topology rendered via React Flow.
   - Inspect nodes (Learned vs Review Due) and relationship edges (Prerequisites vs Contrasts).
4. **Learn (AI Tutor)**:
   - Select any concept, choose depth (*Simple*, *Balanced*, *Detailed*, *Academic*), and review grounded explanations.
   - Click **Save as Note** to archive the synthesis directly into your notes vault.
5. **Recall & Quizzes**:
   - Launch an active-recall drill. Answer questions and click **Submit**.
   - Notice how your score immediately updates the Ebbinghaus memory stability and review interval!
6. **Exam Tomorrow & Date Sheet Planner**:
   - Upload an examination timetable or paste exam dates.
   - Inspect the extracted dates on the verification screen, confirm them, and review your daily revision schedule.
7. **Flashcards & Mind Maps**:
   - Practice with flip cards or generate structured hierarchical schemas.
8. **Proactive Notifications**:
   - Inspect notifications triggered by memory retention decay and upcoming exams.
   - Test **Snooze**, **Dismiss**, and **Mute Topic**.
9. **Persistent AI Tutor Drawer**:
   - Click **Ask AI Tutor** at the bottom-right of any screen to ask grounded questions anytime.
10. **Demo Reset**:
    - Click **Reset** in the bottom sidebar to restore the pristine presentation dataset anytime.

---

## 🏗️ Architecture

- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS, `@xyflow/react` (React Flow), Recharts, Lucide Icons.
- **Backend**: FastAPI, SQLAlchemy 2, Pydantic v2, NetworkX, pypdf, python-docx, httpx.
- **Database**: Persistent relational SQLite (swappable with PostgreSQL).
