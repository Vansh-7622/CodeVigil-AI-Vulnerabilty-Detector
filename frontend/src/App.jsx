import { useState, useCallback, useRef } from "react";
import Editor from "@monaco-editor/react";
import "./app.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SAMPLE_PYTHON = `import pickle
import os
import subprocess
import hashlib

# Hardcoded credentials — BAD!
API_KEY = "sk_live_abc123secretkey999"
password = "admin_password_12345"

def process(user_input):
    """Process user input — MULTIPLE VULNERABILITIES"""
    data = eval(user_input)
    os.system('rm -rf ' + user_input)
    subprocess.call(user_input, shell=True)
    return data

def get_user(cursor, name):
    """Query database — SQL INJECTION"""
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cursor.fetchall()

def load_data(path):
    """Load config from pickle — UNSAFE DESERIALIZATION"""
    with open(path, 'rb') as f:
        return pickle.load(f)

def hash_password(pw):
    """Weak hashing algorithm"""
    return hashlib.md5(pw.encode()).hexdigest()

try:
    something_risky()
except:
    pass

assert user.is_admin, "Must be admin"
`;

const SAMPLE_JS = `const express = require('express');
const { exec } = require('child_process');
const app = express();

// Hardcoded secret — BAD!
const API_SECRET = "sk_live_supersecretkey12345";

app.use(require('cors')());

app.get('/search', (req, res) => {
  // XSS vulnerability
  document.innerHTML = req.query.search;

  // Command injection
  exec(req.query.cmd);

  // Code injection
  const result = eval(req.body.expression);

  // Unsafe dynamic function
  const fn = new Function(req.body.code);

  // Logging secrets
  console.log("Auth token:", req.headers.token);

  // Weak randomness for tokens
  const sessionId = Math.random().toString(36);

  res.send(result);
});

app.listen(3000);
`;

const SEVERITY = {
  critical: { color: "#FF1744", bg: "#FF17441A", glow: "#FF174430", label: "CRITICAL", order: 0 },
  high:     { color: "#FF6D00", bg: "#FF6D001A", glow: "#FF6D0030", label: "HIGH", order: 1 },
  medium:   { color: "#FFD600", bg: "#FFD6001A", glow: "#FFD60030", label: "MEDIUM", order: 2 },
  low:      { color: "#00B0FF", bg: "#00B0FF1A", glow: "#00B0FF30", label: "LOW", order: 3 },
  info:     { color: "#78909C", bg: "#78909C1A", glow: "#78909C30", label: "INFO", order: 4 },
};

function App() {
  const [code, setCode] = useState(SAMPLE_PYTHON);
  const [language, setLanguage] = useState("python");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedVuln, setSelectedVuln] = useState(null);
  const [expandedFixes, setExpandedFixes] = useState({});
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const decorationsRef = useRef([]);

  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Define custom dark theme
    monaco.editor.defineTheme("codevigil", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#0D1117",
        "editor.foreground": "#E6EDF3",
        "editor.lineHighlightBackground": "#161B2200",
        "editorLineNumber.foreground": "#484F58",
        "editorLineNumber.activeForeground": "#E6EDF3",
        "editor.selectionBackground": "#264F78",
        "editorCursor.foreground": "#58A6FF",
      },
    });
    monaco.editor.setTheme("codevigil");
  };

  const highlightVulnerabilities = useCallback((vulns) => {
    if (!editorRef.current || !monacoRef.current) return;
    const monaco = monacoRef.current;
    const editor = editorRef.current;

    const newDecorations = vulns.map((v) => {
      const sev = SEVERITY[v.severity] || SEVERITY.info;
      return {
        range: new monaco.Range(v.line, 1, v.line, 1),
        options: {
          isWholeLine: true,
          className: `vuln-line-${v.severity}`,
          glyphMarginClassName: `vuln-glyph-${v.severity}`,
          overviewRuler: {
            color: sev.color,
            position: monaco.editor.OverviewRulerLane.Full,
          },
          minimap: { color: sev.color, position: monaco.editor.MinimapPosition.Inline },
        },
      };
    });

    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, newDecorations);
  }, []);

  const handleScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedVuln(null);
    setExpandedFixes({});

    try {
      const res = await fetch(`${API_URL}/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }
      const data = await res.json();
      setResults(data);
      highlightVulnerabilities(data.vulnerabilities);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [code, language, highlightVulnerabilities]);

  const handleLanguageSwitch = (lang) => {
    setLanguage(lang);
    setCode(lang === "python" ? SAMPLE_PYTHON : SAMPLE_JS);
    setResults(null);
    setSelectedVuln(null);
    setExpandedFixes({});
    if (editorRef.current) {
      decorationsRef.current = editorRef.current.deltaDecorations(decorationsRef.current, []);
    }
  };

  const jumpToLine = (line) => {
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  };

  const toggleFix = (index) => {
    setExpandedFixes((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const vulns = results?.vulnerabilities || [];

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">&#9781;</span>
            <span className="logo-code">Code</span>
            <span className="logo-vigil">Vigil</span>
          </div>
          <span className="header-tagline">AI-Powered Vulnerability Detector</span>
        </div>
        <div className="header-right">
          <div className="lang-switcher">
            {["python", "javascript"].map((lang) => (
              <button
                key={lang}
                className={`lang-btn ${language === lang ? "active" : ""}`}
                onClick={() => handleLanguageSwitch(lang)}
              >
                {lang === "python" ? "🐍 Python" : "⚡ JavaScript"}
              </button>
            ))}
          </div>
          <button className={`scan-btn ${loading ? "scanning" : ""}`} onClick={handleScan} disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" /> Scanning...
              </>
            ) : (
              <>🔍 Scan Code</>
            )}
          </button>
        </div>
      </header>

      {/* ── Main Layout ── */}
      <div className="main">
        {/* Code Editor */}
        <div className="editor-panel">
          <div className="panel-header">
            <span className="file-icon">📄</span>
            <span className="file-name">{language === "python" ? "main.py" : "app.js"}</span>
            <span className="line-count">{code.split("\n").length} lines</span>
          </div>
          <div className="editor-wrapper">
            <Editor
              height="100%"
              language={language}
              value={code}
              onChange={(val) => setCode(val || "")}
              onMount={handleEditorMount}
              options={{
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                lineNumbers: "on",
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

        {/* Results Panel */}
        <div className="results-panel">
          <div className="panel-header">
            <span>🛡️ Vulnerability Report</span>
          </div>

          <div className="results-content">
            {/* Empty state */}
            {!results && !loading && !error && (
              <div className="empty-state">
                <div className="empty-icon">🛡️</div>
                <p>Paste your code and click <strong>Scan Code</strong> to analyze for vulnerabilities</p>
                <p className="empty-hint">Supports Python & JavaScript</p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="error-box">
                <strong>Error:</strong> {error}
                <p className="error-hint">Make sure the backend is running at {API_URL}</p>
              </div>
            )}

            {/* Loading */}
            {loading && (
              <div className="loading-state">
                <div className="loading-spinner" />
                <p>Analyzing code patterns...</p>
                <p className="loading-sub">Running AST analysis + LLM explanations</p>
              </div>
            )}

            {/* Results */}
            {results && !loading && (
              <>
                {/* Summary Bar */}
                <div className="summary-bar">
                  <div className="summary-total">
                    {results.total_issues === 0 ? (
                      <span className="safe">✅ No vulnerabilities found!</span>
                    ) : (
                      <span className="issues">{results.total_issues} issues detected</span>
                    )}
                  </div>
                  <div className="severity-badges">
                    {Object.entries(SEVERITY).map(([key, cfg]) => {
                      const count = results.severity_counts?.[key];
                      if (!count) return null;
                      return (
                        <div key={key} className="severity-badge" style={{ background: cfg.bg, color: cfg.color }}>
                          <span className="badge-dot" style={{ background: cfg.color }} />
                          <span className="badge-count">{count}</span>
                          <span className="badge-label">{cfg.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Vulnerability Cards */}
                <div className="vuln-list">
                  {vulns.map((v, i) => {
                    const sev = SEVERITY[v.severity] || SEVERITY.info;
                    const isSelected = selectedVuln === i;
                    const isFixOpen = expandedFixes[i];

                    return (
                      <div
                        key={i}
                        className={`vuln-card ${isSelected ? "selected" : ""}`}
                        style={{ borderLeftColor: sev.color }}
                        onClick={() => {
                          setSelectedVuln(isSelected ? null : i);
                          jumpToLine(v.line);
                        }}
                      >
                        <div className="vuln-header">
                          <span className="vuln-severity" style={{ background: sev.bg, color: sev.color }}>
                            {sev.label}
                          </span>
                          <span className="vuln-line">Line {v.line}</span>
                        </div>

                        <div className="vuln-title">{v.title}</div>
                        <div className="vuln-cwe">{v.cwe_id} — {v.cwe_name}</div>

                        {v.explanation && <div className="vuln-explanation">{v.explanation}</div>}

                        {v.impact && (
                          <div className="vuln-impact">
                            <span className="impact-icon">⚠️</span> {v.impact}
                          </div>
                        )}

                        {v.fixed_code && (
                          <div className="vuln-fix-section">
                            <button
                              className="fix-toggle"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleFix(i);
                              }}
                            >
                              {isFixOpen ? "Hide Fix ▲" : "🔧 Show Fix ▼"}
                            </button>
                            {isFixOpen && (
                              <pre className="fix-code">{v.fixed_code}</pre>
                            )}
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

export default App;
