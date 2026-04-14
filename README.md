# CodeVigil — ML-Powered Security Vulnerability Detector

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb?style=flat&logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-3572A5?style=flat&logo=python)](https://python.org)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-f7931e?style=flat&logo=scikitlearn)](https://scikit-learn.org/)

CodeVigil is a hybrid **static-analysis + local ML** security scanner. Paste code in the Monaco editor, click **Scan**, and get:

- Line-level vulnerability highlights with CWE classification
- Plain-English explanations of *why* each finding is dangerous
- Secure fix suggestions for every vulnerability
- ML confidence score + per-finding source label (RULE vs ML)
- Export full scan results as JSON

**Supported languages:** Python · JavaScript · TypeScript · Java · C / C++

> **Fully offline** — runs on a local TF-IDF + Random Forest model. No API keys needed.

---

## Screenshots

### Landing Page
![Landing Page](docs/screenshots/landing.png)

### Language Selection
![Language Selection](docs/screenshots/language-select.png)

### Scanner — Vulnerability Results
![Scanner with results](docs/screenshots/scanner-results.png)

> **To add screenshots:** create a `docs/screenshots/` folder and drop in `landing.png`, `language-select.png`, and `scanner-results.png`.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Browser (React + Vite)                 │
│                                                          │
│  ┌────────────┐   ┌──────────────┐   ┌───────────────┐  │
│  │ LandingPage│ → │LanguagePage  │ → │  ScannerPage  │  │
│  └────────────┘   └──────────────┘   └──────┬────────┘  │
│                                             │            │
│                                    Monaco Editor         │
│                                    (inline glyph marks)  │
└─────────────────────────────────────────────┬────────────┘
                                              │ POST /scan
                                              │ { code, language }
                                              ▼
┌──────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Python)                 │
│                                                          │
│  main.py                                                 │
│  ├── POST /scan        (JSON body)                       │
│  └── POST /scan/file   (multipart, auto-detects lang)    │
│                  │                                       │
│                  ▼                                       │
│  ml_engine.py                                            │
│  ├── rule_based_scan()  — 23 regex patterns              │
│  ├── ml_predict()       — TF-IDF + Random Forest         │
│  └── scan_code()        — merges both; ML fills gaps     │
│                  │                                       │
│  model/vuln_model.joblib  (pre-trained, local)           │
└──────────────────────────────────────────────────────────┘
                                              │
                              JSON ScanResponse
                              { vulnerabilities[], severity_counts,
                                model_confidence, ... }
```

### Key design decisions

| Decision | Reason |
|---|---|
| Rules take priority over ML | Avoids noisy ML false-positives on well-understood patterns |
| ML threshold at 0.85 confidence | Keeps per-line ML findings low false-positive |
| `source` field on every finding | UI can show RULE vs ML badge per vulnerability |
| No external API | Zero cold-start, zero keys, works fully offline |

---

## Detected Vulnerability Patterns

| CWE | Vulnerability | Severity |
|---|---|---|
| CWE-79 | XSS (`innerHTML`, `dangerouslySetInnerHTML`, event handlers) | High |
| CWE-89 | SQL Injection (string-concatenated queries) | Critical |
| CWE-78 | Command Injection (`os.system`, `subprocess shell=True`, `Runtime.exec`) | Critical |
| CWE-95 | Code Injection (`eval`, `exec`, `new Function`) | Critical |
| CWE-502 | Unsafe Deserialization (`pickle.load`, `yaml.load`, `ObjectInputStream`) | Critical |
| CWE-798 | Hardcoded Credentials (passwords, API keys, tokens in source) | High |
| CWE-120 | Buffer Overflow (`gets`, `strcpy`, `sprintf`, `scanf`) | Critical |
| CWE-328 | Weak Cryptography (MD5, SHA-1, DES, ECB mode) | Medium |
| CWE-330 | Weak Randomness (`Math.random`, `random.random`) | Low |
| CWE-134 | Format String (`printf(user_string)`) | High |
| CWE-377 | Insecure Temp File (`mktemp`) | Medium |
| CWE-532 | Sensitive Data in Logs (`console.log` with token/password) | Medium |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Monaco Editor (`@monaco-editor/react`) |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| Scanner | 23-rule regex engine + sklearn ML model |
| ML Model | TF-IDF Vectorizer → Random Forest Classifier (sklearn Pipeline) |
| Serialization | joblib |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+

### 1. Clone

```bash
git clone https://github.com/Vansh-7622/CodeVigil-AI-Vulnerabilty-Detector.git
cd CodeVigil-AI-Vulnerabilty-Detector
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

No `.env` file needed — the backend is fully offline.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

### 4. (Optional) Retrain the ML Model

```bash
python model/train.py
# Regenerates model/vuln_model.joblib from data/
```

---

## API Reference

### `POST /scan`

```json
// Request
{
  "code": "import pickle\npickle.load(f)",
  "language": "python"
}

// Response
{
  "language": "python",
  "total_issues": 1,
  "severity_counts": { "critical": 1 },
  "model_confidence": 0.91,
  "vulnerabilities": [
    {
      "line": 2,
      "severity": "critical",
      "cwe_id": "CWE-502",
      "cwe_name": "Unsafe Deserialization",
      "title": "Unsafe Deserialization",
      "snippet": "pickle.load(",
      "explanation": "pickle can execute arbitrary code during deserialization...",
      "fixed_code": "Use JSON or MessagePack instead...",
      "source": "rule"
    }
  ]
}
```

### `POST /scan/file`

Upload a source file directly. Language is auto-detected from extension (`.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`).

### `GET /health`

```json
{ "status": "ok", "model": "local_ml", "api_dependencies": "none" }
```

---

## Project Structure

```
CodeVigil/
├── backend/
│   ├── main.py          # FastAPI app, /scan and /scan/file endpoints
│   ├── ml_engine.py     # Rule engine + ML model, scan_code() dispatcher
│   └── requirements.txt
├── model/
│   ├── vuln_model.joblib  # Pre-trained sklearn pipeline (not committed if large)
│   └── train.py           # Retraining script
├── data/                  # Labeled training data (not committed)
└── frontend/
    ├── src/
    │   ├── App.jsx      # All UI: LandingPage, LanguagePage, ScannerPage
    │   ├── app.css      # Dark theme styles
    │   └── main.jsx     # React root
    ├── index.html
    └── package.json
```

---

## License

MIT

Built by **Vansh Sorathiya** · PDEU B.Tech CSE 2027
