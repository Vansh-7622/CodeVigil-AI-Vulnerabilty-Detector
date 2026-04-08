# 🛡️ CodeVigil — AI-Powered Code Vulnerability Detector

CodeVigil is a hybrid static-analysis + LLM-powered tool that detects security vulnerabilities in Python and JavaScript code, explains **why** they're dangerous, and suggests fixes — all in real time.

## ✨ Features

- **AST-based scanning** — Uses Python's `ast` module for deep code analysis, not just regex
- **15+ vulnerability patterns** — SQL injection, command injection, XSS, hardcoded secrets, weak hashing, deserialization attacks, and more
- **LLM-powered explanations** — Llama 3 (via Groq) explains each vulnerability in plain English with impact analysis
- **Fix suggestions** — One-click "Show Fix" with secure code alternatives
- **Monaco Editor** — VS Code's editor with inline vulnerability highlighting (colored glyph markers per severity)
- **CWE classification** — Each finding mapped to its CWE ID for industry-standard tracking
- **Python & JavaScript** support

## 🏗️ Architecture

```
┌─────────────────┐     POST /scan      ┌──────────────────────┐
│   React + Vite   │ ──────────────────► │    FastAPI Backend    │
│  Monaco Editor   │ ◄────────────────── │                      │
│                  │    JSON response    │  ┌────────────────┐  │
└─────────────────┘                     │  │  AST Scanner    │  │
                                        │  │  (Python AST +  │  │
                                        │  │   Regex rules)  │  │
                                        │  └───────┬────────┘  │
                                        │          │            │
                                        │  ┌───────▼────────┐  │
                                        │  │  Groq / Llama 3 │  │
                                        │  │  (Explanations  │  │
                                        │  │   + Fixes)      │  │
                                        │  └────────────────┘  │
                                        └──────────────────────┘
```

## 🛠️ Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Frontend  | React, Vite, Monaco Editor          |
| Backend   | FastAPI, Python AST, Regex engine   |
| LLM       | Llama 3.3 70B via Groq API          |
| Styling   | Custom CSS (dark theme)             |

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API key ([console.groq.com](https://console.groq.com))

### Backend
```bash
cd backend
echo "GROQ_API_KEY=your_key_here" > .env
pip install -r requirements.txt
python main.py
# Server runs at http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

## 📊 Detected Vulnerabilities

| CWE ID   | Vulnerability                     | Severity |
|----------|-----------------------------------|----------|
| CWE-95   | Code Injection (eval/exec)        | Critical |
| CWE-78   | OS Command Injection              | Critical |
| CWE-89   | SQL Injection                     | Critical |
| CWE-502  | Unsafe Deserialization (pickle)   | Critical |
| CWE-79   | Cross-site Scripting (XSS)        | High     |
| CWE-798  | Hardcoded Credentials             | High     |
| CWE-328  | Weak Hashing (MD5/SHA1)           | Medium   |
| CWE-1321 | Prototype Pollution               | Medium   |
| CWE-942  | Overly Permissive CORS            | Medium   |
| CWE-532  | Sensitive Info in Logs            | Medium   |
| CWE-330  | Insufficient Randomness           | Low      |
| CWE-396  | Overly Broad Exception Handling   | Low      |
| CWE-617  | Reachable Assertion               | Info     |

## 📸 Screenshots

![CodeVigil UI](screenshot.png)

## 📝 License

MIT
