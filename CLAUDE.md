# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CodeVigil is a hybrid static-analysis + local ML-powered security vulnerability detector. It scans source code for known vulnerability patterns using a rule engine and a locally trained TF-IDF + Random Forest classifier — no external API calls required.

## Development Commands

### Backend (FastAPI — Python)
```bash
cd backend
pip install -r requirements.txt   # one-time setup
python main.py                     # runs uvicorn at http://localhost:8000
```
No `.env` file needed — the backend is fully offline.

### Frontend (React + Vite)
```bash
cd frontend
npm install    # one-time setup
npm run dev    # http://localhost:5173
npm run build  # production build
npm run lint   # ESLint
```

The frontend hardcodes `API_URL = "http://localhost:8000"` in `App.jsx`.

### Model Training (optional — pre-trained model included)
```bash
python model/train.py   # regenerates model/vuln_model.joblib
```

## Architecture

The app has three pages managed by simple `useState` routing in `App.jsx` (no router library):
- `landing` → `language` → `scanner`

**Data flow:**
1. User pastes code in the Monaco editor (`ScannerPage` in `frontend/src/App.jsx`)
2. `POST /scan` → `backend/main.py` → `ml_engine.py`
3. `ml_engine.py` runs two passes:
   - Rule engine: 23 regex patterns across CWE categories (XSS, SQLi, command injection, etc.)
   - ML model: per-line TF-IDF + Random Forest predictions for lines not caught by rules
4. Results return with `explanation`, `fixed_code`, `source` (rule vs ml_model), and `model_confidence`
5. Results render as vuln cards in the results panel; Monaco decorations mark vulnerable lines with colored glyphs

**Backend modules:**
- `backend/main.py` — FastAPI app with two endpoints: `POST /scan` (JSON body) and `POST /scan/file` (multipart upload with auto language detection)
- `backend/ml_engine.py` — rule engine (`RULES` list), ML model loader (`_get_model()`), and `scan_code()` dispatcher that merges both sources

**Frontend (`frontend/src/`):**
- `App.jsx` — entire frontend: `LandingPage`, `LanguagePage`, `ScannerPage` components plus `LANGS`, `SAMPLES`, and `SEV` config constants
- `app.css` — all styles (dark theme)
- `main.jsx` — React root mount

**Model (`model/`):**
- `vuln_model.joblib` — pre-trained sklearn Pipeline (TfidfVectorizer → RandomForestClassifier)
- `train.py` — training script; regenerates the joblib from labeled data in `data/`

## Key Design Decisions

- **No external API:** Replaced the original Groq/Llama 3 integration with a local sklearn model. Zero API keys, zero cold-start latency.
- **Rules take priority over ML:** `scan_code()` runs rule matching first; ML only fills in lines not already flagged by a rule. This avoids noisy ML false-positives on well-understood patterns.
- **ML threshold at 0.85:** Per-line ML findings are only emitted when the model confidence exceeds 85% to keep false positive rates low.
- **Python uses AST (original scanner), others use regex:** The rule engine works on raw text across all languages.
- **No auth/rate limiting on the API:** The backend has `allow_origins=["*"]` CORS — intentional for a demo tool.
- **`source` field on every finding:** Each vulnerability carries `"source": "rule"` or `"source": "ml_model"` so the UI can display a badge.

## Supported Languages

`SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "java", "c", "cpp"]`

TypeScript rules are `JS_RULES + TS_EXTRA`; `cpp` reuses `C_RULES`.
