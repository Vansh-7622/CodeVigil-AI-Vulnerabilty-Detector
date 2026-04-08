# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CodeVigil is a hybrid static-analysis + LLM-powered security vulnerability detector. It scans source code for known vulnerability patterns, then uses Groq's Llama 3.3 70B to generate plain-English explanations, impact assessments, and secure fix suggestions.

## Development Commands

### Backend (FastAPI — Python)
```bash
cd backend
pip install -r requirements.txt   # one-time setup
python main.py                     # runs uvicorn at http://localhost:8000
```
Requires `backend/.env` with `GROQ_API_KEY=your_key_here`.

### Frontend (React + Vite)
```bash
cd frontend
npm install    # one-time setup
npm run dev    # http://localhost:5173
npm run build  # production build
npm run lint   # ESLint
```

The frontend reads `VITE_API_URL` env var (defaults to `http://localhost:8000`).

## Architecture

The app has three pages managed by simple `useState` routing in `App.jsx` (no router library):
- `landing` → `language` → `scanner`

**Data flow:**
1. User pastes code in the Monaco editor (`ScannerPage` in `frontend/src/App.jsx`)
2. `POST /scan` → `backend/main.py` → `scanner.py` → `llm_engine.py`
3. `scanner.py` runs language-specific analysis: Python uses the AST (`PythonAnalyzer` class), all other languages use regex rule lists (`JS_RULES`, `JAVA_RULES`, `C_RULES`, `TS_EXTRA`)
4. `llm_engine.py` calls Groq API concurrently (max 10 vulns) via `asyncio.gather` and returns `explanation`, `impact`, and `fixed_code` for each finding
5. Results render as vuln cards in the results panel; Monaco decorations mark vulnerable lines with colored glyphs

**Backend modules:**
- `backend/main.py` — FastAPI app, two endpoints: `POST /scan` (JSON body) and `POST /scan/file` (multipart upload with auto language detection)
- `backend/scanner.py` — `Vulnerability` dataclass, `PythonAnalyzer(ast.NodeVisitor)`, regex rule lists per language, `scan_code()` dispatcher
- `backend/llm_engine.py` — async Groq API calls via `httpx`, `enrich_all()` caps LLM enrichment at 10 vulnerabilities

**Frontend (`frontend/src/`):**
- `App.jsx` — entire frontend: `LandingPage`, `LanguagePage`, `ScannerPage` components plus `LANGS`, `SAMPLES`, and `SEV` config constants
- `app.css` — all styles (dark theme)
- `main.jsx` — React root mount

## Key Design Decisions

- **LLM cap at 10:** `enrich_all()` only sends the first 10 vulnerabilities to the LLM to control latency and API costs. Vulnerabilities 11+ are returned without explanation/impact/fixed_code fields.
- **Python uses AST, others use regex:** `PythonAnalyzer` walks the AST and tracks imports for accurate resolution (e.g., subprocess alias detection). JS/TS/Java/C use line-by-line regex and skip comment lines.
- **No auth/rate limiting on the API:** The backend has `allow_origins=["*"]` CORS — intentional for a demo tool.
- **Groq via raw httpx:** `llm_engine.py` calls the Groq OpenAI-compatible endpoint directly without the Groq SDK to minimize dependencies.

## Supported Languages

`SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "java", "c", "cpp"]`

TypeScript scans use `JS_RULES + TS_EXTRA`; `cpp` uses the same `C_RULES` as `c`.
