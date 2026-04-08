import { useState, useCallback, useRef } from "react";
import Editor from "@monaco-editor/react";
import "./app.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const LANGS = [
  { id: "python", label: "Python", icon: "🐍", color: "#3572A5", ext: "main.py", mono: "python" },
  { id: "javascript", label: "JS", icon: "⚡", color: "#f1e05a", ext: "app.js", mono: "javascript" },
  { id: "typescript", label: "TS", icon: "🔷", color: "#3178c6", ext: "app.ts", mono: "typescript" },
  { id: "java", label: "Java", icon: "☕", color: "#b07219", ext: "Main.java", mono: "java" },
  { id: "c", label: "C/C++", icon: "⚙️", color: "#555555", ext: "main.c", mono: "c" },
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
  critical: { color: "#ef4444", bg: "rgba(239,68,68,0.1)", label: "CRITICAL" },
  high:     { color: "#f97316", bg: "rgba(249,115,22,0.1)", label: "HIGH" },
  medium:   { color: "#eab308", bg: "rgba(234,179,8,0.1)",  label: "MEDIUM" },
  low:      { color: "#3b82f6", bg: "rgba(59,130,246,0.1)", label: "LOW" },
  info:     { color: "#94a3b8", bg: "rgba(148,163,184,0.1)", label: "INFO" },
};

export default function App() {
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState(SAMPLES.python);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [fixes, setFixes] = useState({});
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const decRef = useRef([]);

  const langInfo = LANGS.find((l) => l.id === lang);

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
          overviewRuler: { color: SEV[v.severity]?.color || "#94a3b8", position: m.editor.OverviewRulerLane.Full },
          minimap: { color: SEV[v.severity]?.color || "#94a3b8", position: m.editor.MinimapPosition.Inline },
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

  const switchLang = (id) => {
    setLang(id); setCode(SAMPLES[id] || ""); setResults(null); setSelected(null); setFixes({});
    if (editorRef.current) decRef.current = editorRef.current.deltaDecorations(decRef.current, []);
  };

  const jumpTo = (line) => {
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  };

  const vulns = results?.vulnerabilities || [];

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <div className="logo-shield">🛡️</div>
            <div className="logo-text"><span>Code</span><span>Vigil</span></div>
            <span className="logo-version">v2.0</span>
          </div>
          <div className="header-stats">
            <span><span className="stat-val">5</span> Languages</span>
            <span><span className="stat-val">60+</span> CWE Patterns</span>
            <span><span className="stat-val">AI</span> Powered</span>
          </div>
        </div>
        <div className="header-right">
          <div className="lang-pills">
            {LANGS.map((l) => (
              <button key={l.id} className={`lang-pill ${lang === l.id ? "active" : ""}`} onClick={() => switchLang(l.id)}>
                <span className="lang-dot" style={{ background: l.color }} />
                {l.label}
              </button>
            ))}
          </div>
          <button className={`scan-btn ${loading ? "scanning" : ""}`} onClick={scan} disabled={loading}>
            {loading ? <><span className="spinner" /> Scanning...</> : <>🔍 Scan Code</>}
          </button>
        </div>
      </header>

      <div className="main">
        <div className="editor-panel">
          <div className="panel-tab-bar">
            <div className="file-tab">
              <span className="dot" style={{ background: langInfo?.color }} />
              {langInfo?.ext}
            </div>
            <span className="panel-meta">{code.split("\n").length} lines</span>
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
            {results && <span style={{ color: "#ef4444", fontFamily: "JetBrains Mono" }}>{results.total_issues} found</span>}
          </div>
          <div className="results-content">
            {!results && !loading && !error && (
              <div className="empty-state">
                <div className="empty-shield">🛡️</div>
                <h3>Ready to scan</h3>
                <p>Paste your code or use a sample, then click <strong style={{ color: "#ef4444" }}>Scan Code</strong> to detect vulnerabilities with AI-powered analysis.</p>
              </div>
            )}
            {error && <div className="error-box"><strong>Error:</strong> {error}<div className="hint">Ensure backend is running at {API_URL}</div></div>}
            {loading && (
              <div className="loading-state">
                <div className="loading-ring" />
                <p>Scanning for vulnerabilities...</p>
                <p className="sub">AST analysis + AI explanations via Llama 3</p>
              </div>
            )}
            {results && !loading && (
              <>
                <div className="summary-card">
                  <div className="summary-total">
                    {results.total_issues === 0
                      ? <span className="safe">✅ Clean — no vulnerabilities found</span>
                      : <><span className="count">{results.total_issues}</span> issues detected in {langInfo?.label}</>
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
                          <span className="vuln-line">L{v.line}</span>
                        </div>
                        <div className="vuln-title">{v.title}</div>
                        <div className="vuln-cwe">{v.cwe_id} — {v.cwe_name}</div>
                        {v.explanation && <div className="vuln-explain">{v.explanation}</div>}
                        {v.impact && <div className="vuln-impact"><span className="vuln-impact-icon">⚠️</span>{v.impact}</div>}
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