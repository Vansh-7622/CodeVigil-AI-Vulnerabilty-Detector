import { useState, useCallback, useRef, useEffect } from "react";
import Editor from "@monaco-editor/react";
import "./app.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const LANGS = [
  { id: "python", label: "Python", icon: "🐍", color: "#3572A5", ext: "main.py", mono: "python", desc: "Web backends, AI/ML, scripting" },
  { id: "javascript", label: "JavaScript", icon: "⚡", color: "#f1e05a", ext: "app.js", mono: "javascript", desc: "Frontend, Node.js, full-stack" },
  { id: "typescript", label: "TypeScript", icon: "🔷", color: "#3178c6", ext: "app.ts", mono: "typescript", desc: "Type-safe JavaScript" },
  { id: "java", label: "Java", icon: "☕", color: "#b07219", ext: "Main.java", mono: "java", desc: "Enterprise, Android, backends" },
  { id: "c", label: "C / C++", icon: "⚙️", color: "#555555", ext: "main.c", mono: "c", desc: "Systems, embedded, low-level" },
];

const SAMPLES = {
  python: `import pickle
import os
import subprocess
import hashlib

# Hardcoded credentials
API_KEY = "sk_live_abc123secretkey999"
password = "admin_password_12345"

def process(user_input):
    data = eval(user_input)
    os.system('rm -rf ' + user_input)
    subprocess.call(user_input, shell=True)
    return data

def get_user(cursor, name):
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cursor.fetchall()

def load_data(path):
    with open(path, 'rb') as f:
        return pickle.load(f)

def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()

try:
    something_risky()
except:
    pass

assert user.is_admin, "Must be admin"
`,
  javascript: `const express = require('express');
const { exec } = require('child_process');
const app = express();

const API_SECRET = "sk_live_supersecretkey12345";
app.use(require('cors')());

app.get('/search', (req, res) => {
  document.innerHTML = req.query.search;
  exec(req.query.cmd);
  const result = eval(req.body.expression);
  const fn = new Function(req.body.code);
  console.log("Auth token:", req.headers.token);
  const sessionId = Math.random().toString(36);
  res.send(result);
});
`,
  typescript: `import express, { Request, Response } from 'express';

const API_KEY: any = "sk_live_secret_key_12345678";

// @ts-ignore
const handler = (req: Request, res: Response) => {
  const data = JSON.parse(req.body) as any;
  const result = eval(data.expression);
  document.innerHTML = data.content;

  // @ts-nocheck
  console.log("Token:", req.headers.authorization);
  const id = Math.random().toString(36);
  res.json({ result, id });
};
`,
  java: `import java.sql.*;
import java.io.*;
import java.security.MessageDigest;

public class UserService {
    private String dbPassword = "production_db_pass_2024";

    public User getUser(String userId) throws Exception {
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE id=" + userId;
        stmt.executeQuery(query);

        Runtime.getRuntime().exec(userId);

        ObjectInputStream ois = new ObjectInputStream(
            new FileInputStream("data.ser")
        );
        Object obj = ois.readObject();

        MessageDigest md = MessageDigest.getInstance("MD5");

        File f = new File(request.getParameter("path"));
        Random rng = new Random();

        System.out.println("Password: " + dbPassword);
        return null;
    }
}
`,
  c: `#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define API_TOKEN "hardcoded_api_token_secret"

int main() {
    char buffer[64];
    char dest[32];

    gets(buffer);
    strcpy(dest, buffer);
    strcat(dest, buffer);
    sprintf(dest, user_format);
    scanf("%s", buffer);

    printf(user_string);
    system(user_input);
    popen(cmd, "r");

    int size = atoi(argv[1]);
    void *ptr = malloc(n * sizeof(int));

    char *tmp = mktemp("/tmp/XXXXXX");
    int r = rand();

    return 0;
}
`,
};

const SEV = {
  critical: { color: "#ef4444", bg: "rgba(239,68,68,0.12)", label: "CRITICAL" },
  high:     { color: "#f97316", bg: "rgba(249,115,22,0.12)", label: "HIGH" },
  medium:   { color: "#eab308", bg: "rgba(234,179,8,0.12)",  label: "MEDIUM" },
  low:      { color: "#3b82f6", bg: "rgba(59,130,246,0.12)", label: "LOW" },
  info:     { color: "#94a3b8", bg: "rgba(148,163,184,0.12)", label: "INFO" },
};

const FEATURES = [
  { icon: "🧠", title: "AI-Powered Analysis", desc: "Llama 3 explains each vulnerability in plain English with real-world impact scenarios" },
  { icon: "🌳", title: "AST Deep Scanning", desc: "Python uses Abstract Syntax Tree parsing — not just regex — for accurate detection" },
  { icon: "🔧", title: "Auto-Fix Suggestions", desc: "One-click secure code alternatives for every vulnerability found" },
  { icon: "🌐", title: "5 Languages", desc: "Python, JavaScript, TypeScript, Java, and C/C++ with 60+ CWE patterns" },
  { icon: "📋", title: "CWE Classification", desc: "Industry-standard Common Weakness Enumeration IDs for every finding" },
  { icon: "⚡", title: "Instant Results", desc: "Fast scanning powered by Groq's inference engine — results in seconds" },
];

/* ═══════════════════════════════════════════════════════════════
   PAGE 1: LANDING
   ═══════════════════════════════════════════════════════════════ */
function LandingPage({ onStart }) {
  return (
    <div className="landing">
      <div className="landing-bg">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
        <div className="grid-overlay" />
      </div>

      <nav className="landing-nav">
        <div className="nav-logo">
          <div className="nav-shield">🛡️</div>
          <span className="nav-brand"><span>Code</span><span className="accent">Vigil</span></span>
        </div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#languages">Languages</a>
          <a href="https://github.com/Vansh-7622/CodeVigil-AI-Vulnerabilty-Detector" target="_blank" rel="noreferrer">GitHub ↗</a>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-badge">
          <span className="badge-dot" /> AI-Powered Security Scanner
        </div>
        <h1 className="hero-title">
          Find vulnerabilities<br />
          <span className="hero-gradient">before hackers do.</span>
        </h1>
        <p className="hero-sub">
          CodeVigil scans your code using AST analysis and Llama 3 AI to detect security flaws,
          explain their impact, and suggest fixes — across 5 programming languages.
        </p>
        <div className="hero-actions">
          <button className="cta-primary" onClick={onStart}>
            Start Scanning →
          </button>
          <a className="cta-secondary" href="https://github.com/Vansh-7622/CodeVigil-AI-Vulnerabilty-Detector" target="_blank" rel="noreferrer">
            View on GitHub
          </a>
        </div>
        <div className="hero-stats">
          <div className="hero-stat"><span className="stat-num">60+</span><span className="stat-label">CWE Patterns</span></div>
          <div className="stat-divider" />
          <div className="hero-stat"><span className="stat-num">5</span><span className="stat-label">Languages</span></div>
          <div className="stat-divider" />
          <div className="hero-stat"><span className="stat-num">AI</span><span className="stat-label">Powered Fixes</span></div>
        </div>
      </section>

      <section className="features" id="features">
        <h2 className="section-title">How it works</h2>
        <div className="features-grid">
          {FEATURES.map((f, i) => (
            <div key={i} className="feature-card" style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lang-showcase" id="languages">
        <h2 className="section-title">Supported Languages</h2>
        <div className="lang-cards">
          {LANGS.map((l, i) => (
            <div key={l.id} className="lang-card" style={{ animationDelay: `${i * 0.08}s` }} onClick={onStart}>
              <div className="lang-card-icon">{l.icon}</div>
              <div className="lang-card-dot" style={{ background: l.color }} />
              <h4>{l.label}</h4>
              <p>{l.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <p>Built by <strong>Vansh Sorathiya</strong> • PDEU B.Tech CSE 2027</p>
        <p className="footer-tech">FastAPI · React · Monaco Editor · Llama 3 via Groq · Python AST</p>
      </footer>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PAGE 2: LANGUAGE SELECTION
   ═══════════════════════════════════════════════════════════════ */
function LanguagePage({ onSelect, onBack }) {
  return (
    <div className="lang-page">
      <div className="landing-bg">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
      </div>
      <button className="back-btn" onClick={onBack}>← Back</button>
      <div className="lang-page-content">
        <h2>Choose your language</h2>
        <p className="lang-page-sub">Select the language of the code you want to scan</p>
        <div className="lang-select-grid">
          {LANGS.map((l, i) => (
            <button
              key={l.id}
              className="lang-select-card"
              style={{ animationDelay: `${i * 0.08}s` }}
              onClick={() => onSelect(l.id)}
            >
              <div className="lsc-icon">{l.icon}</div>
              <div className="lsc-info">
                <h3>{l.label}</h3>
                <p>{l.desc}</p>
              </div>
              <div className="lsc-dot" style={{ background: l.color }} />
              <span className="lsc-arrow">→</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PAGE 3: SCANNER
   ═══════════════════════════════════════════════════════════════ */
function ScannerPage({ lang, onBack, onChangeLang }) {
  const [code, setCode] = useState(SAMPLES[lang] || "");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [fixes, setFixes] = useState({});
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const decRef = useRef([]);

  const langInfo = LANGS.find((l) => l.id === lang);

  useEffect(() => {
    setCode(SAMPLES[lang] || "");
    setResults(null);
    setSelected(null);
    setFixes({});
    if (editorRef.current) decRef.current = editorRef.current.deltaDecorations(decRef.current, []);
  }, [lang]);

  const onMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    monaco.editor.defineTheme("codevigil-dark", {
      base: "vs-dark", inherit: true, rules: [],
      colors: {
        "editor.background": "#0f1520",
        "editor.foreground": "#e2e8f0",
        "editor.lineHighlightBackground": "#1e293b40",
        "editorLineNumber.foreground": "#475569",
        "editorLineNumber.activeForeground": "#e2e8f0",
        "editor.selectionBackground": "#334155",
        "editorCursor.foreground": "#3b82f6",
      },
    });
    monaco.editor.setTheme("codevigil-dark");
  };

  const markVulns = useCallback((vulns) => {
    if (!editorRef.current || !monacoRef.current) return;
    const m = monacoRef.current;
    decRef.current = editorRef.current.deltaDecorations(
      decRef.current,
      vulns.map((v) => ({
        range: new m.Range(v.line, 1, v.line, 1),
        options: {
          isWholeLine: true,
          className: `vuln-line-${v.severity}`,
          glyphMarginClassName: `vuln-glyph-${v.severity}`,
          overviewRuler: { color: SEV[v.severity]?.color, position: m.editor.OverviewRulerLane.Full },
        },
      }))
    );
  }, []);

  const scan = useCallback(async () => {
    setLoading(true); setError(null); setSelected(null); setFixes({});
    try {
      const r = await fetch(`${API_URL}/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language: lang }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Error ${r.status}`);
      const data = await r.json();
      setResults(data);
      markVulns(data.vulnerabilities);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [code, lang, markVulns]);

  const jumpTo = (line) => {
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  };

  const vulns = results?.vulnerabilities || [];

  return (
    <div className="scanner-page">
      {/* Scanner Header */}
      <header className="scanner-header">
        <div className="sh-left">
          <button className="back-btn-small" onClick={onBack}>←</button>
          <div className="sh-logo">
            <span className="sh-shield">🛡️</span>
            <span className="sh-brand">Code<span className="accent">Vigil</span></span>
          </div>
        </div>
        <div className="sh-center">
          <div className="lang-pills">
            {LANGS.map((l) => (
              <button key={l.id} className={`lang-pill ${lang === l.id ? "active" : ""}`} onClick={() => onChangeLang(l.id)}>
                <span className="lang-dot" style={{ background: l.color }} />
                {l.label}
              </button>
            ))}
          </div>
        </div>
        <div className="sh-right">
          <button className={`scan-btn ${loading ? "scanning" : ""}`} onClick={scan} disabled={loading}>
            {loading ? <><span className="spinner" /> Scanning...</> : <>🔍 Scan Code</>}
          </button>
        </div>
      </header>

      {/* Scanner Body */}
      <div className="scanner-body">
        <div className="editor-panel">
          <div className="panel-tab-bar">
            <div className="file-tab">
              <span className="dot" style={{ background: langInfo?.color }} />
              {langInfo?.ext}
            </div>
            <span className="panel-meta">{code.split("\n").length} lines • {langInfo?.label}</span>
          </div>
          <div className="editor-wrapper">
            <Editor
              height="100%"
              language={langInfo?.mono || "plaintext"}
              value={code}
              onChange={(v) => setCode(v || "")}
              onMount={onMount}
              options={{
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                glyphMargin: true,
                folding: true,
                renderLineHighlight: "none",
                padding: { top: 8 },
                smoothScrolling: true,
                cursorBlinking: "smooth",
                cursorSmoothCaretAnimation: "on",
              }}
            />
          </div>
        </div>

        <div className="results-panel">
          <div className="results-header">
            <span>🛡️ Vulnerability Report</span>
            {results && <span className="rh-count">{results.total_issues} found</span>}
          </div>
          <div className="results-content">
            {!results && !loading && !error && (
              <div className="empty-state">
                <div className="empty-shield">🛡️</div>
                <h3>Ready to scan</h3>
                <p>Paste your {langInfo?.label} code or use the sample, then click <strong className="accent">Scan Code</strong></p>
              </div>
            )}
            {error && <div className="error-box"><strong>Error:</strong> {error}<div className="hint">Make sure backend is running at {API_URL}. First request may take ~50s on free tier.</div></div>}
            {loading && (
              <div className="loading-state">
                <div className="loading-ring" />
                <p>Scanning {langInfo?.label} code...</p>
                <p className="sub">AST analysis + AI explanations</p>
              </div>
            )}
            {results && !loading && (
              <>
                <div className="summary-card">
                  <div className="summary-total">
                    {results.total_issues === 0
                      ? <span className="safe">✅ Clean — no vulnerabilities found!</span>
                      : <><span className="count">{results.total_issues}</span> issues in {langInfo?.label}</>
                    }
                  </div>
                  <div className="severity-pills">
                    {Object.entries(SEV).map(([k, v]) => {
                      const c = results.severity_counts?.[k];
                      if (!c) return null;
                      return (
                        <div key={k} className="sev-pill" style={{ background: v.bg, color: v.color }}>
                          <span className="dot" style={{ background: v.color }} />
                          <span className="num">{c}</span>
                          <span className="lbl">{v.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="vuln-list">
                  {vulns.map((v, i) => {
                    const s = SEV[v.severity] || SEV.info;
                    return (
                      <div key={i} className={`vuln-card ${selected === i ? "selected" : ""}`}
                        style={{ borderLeftColor: s.color }}
                        onClick={() => { setSelected(selected === i ? null : i); jumpTo(v.line); }}>
                        <div className="vuln-top">
                          <span className="vuln-badge" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                          <span className="vuln-line-num">L{v.line}</span>
                        </div>
                        <div className="vuln-title">{v.title}</div>
                        <div className="vuln-cwe">{v.cwe_id} — {v.cwe_name}</div>
                        {v.explanation && <div className="vuln-explain">{v.explanation}</div>}
                        {v.impact && <div className="vuln-impact"><span className="vi-icon">⚠️</span>{v.impact}</div>}
                        {v.fixed_code && (
                          <div className="fix-section">
                            <button className="fix-btn" onClick={(e) => { e.stopPropagation(); setFixes((p) => ({ ...p, [i]: !p[i] })); }}>
                              {fixes[i] ? "Hide Fix ▲" : "🔧 Show Fix ▼"}
                            </button>
                            {fixes[i] && <pre className="fix-code">{v.fixed_code}</pre>}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   APP ROUTER
   ═══════════════════════════════════════════════════════════════ */
export default function App() {
  const [page, setPage] = useState("landing"); // landing | language | scanner
  const [lang, setLang] = useState("python");

  const goToLangSelect = () => setPage("language");
  const goToScanner = (selectedLang) => { setLang(selectedLang); setPage("scanner"); };
  const goToLanding = () => setPage("landing");
  const goBackFromScanner = () => setPage("language");

  if (page === "landing") return <LandingPage onStart={goToLangSelect} />;
  if (page === "language") return <LanguagePage onSelect={goToScanner} onBack={goToLanding} />;
  return <ScannerPage lang={lang} onBack={goBackFromScanner} onChangeLang={(l) => { setLang(l); }} />;
}