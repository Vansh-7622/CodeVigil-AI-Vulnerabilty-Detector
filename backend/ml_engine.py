"""
ml_engine.py
Replaces llm_engine.py (Groq API) with local ML model + rule-based engine.
No external API calls.
"""

import os, re
import joblib
from pathlib import Path
def custom_tokenizer(text):
    """Security-aware tokenizer for TF-IDF."""
    tokens = re.findall(
        r'</?[a-zA-Z][a-zA-Z0-9]*'
        r'|[a-zA-Z_]\w*\('
        r'|[a-zA-Z_]\w*'
        r"|\'[^\']*\'"
        r'|"[^"]*"'
        r'|\d+'
        r'|[=<>!]{1,2}'
        r'|[^\s\w]',
        text
    )
    return [t.lower() for t in tokens]

# Resolve model path relative to this file's location
_THIS_DIR = Path(__file__).resolve().parent
MODEL_PATH = _THIS_DIR.parent / "model" / "vuln_model.joblib"

# Load model once at startup
_pipeline = None


def _get_model():
    global _pipeline
    if _pipeline is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Run: python model/train.py"
            )
        _pipeline = joblib.load(str(MODEL_PATH))
    return _pipeline


# ══════════════════════════════════════════════════════════════════════════════
# RULE-BASED ENGINE
# ══════════════════════════════════════════════════════════════════════════════

RULES = [
    {
        "pattern": re.compile(r'<script[\s>]', re.I),
        "vuln_type": "XSS", "cwe": "CWE-79", "severity": "high",
        "explanation": "Inline <script> tags can execute arbitrary JavaScript in a user's browser, enabling cookie theft, session hijacking, or defacement.",
        "fix": "Sanitize all user input with a library like DOMPurify. Use textContent instead of innerHTML.",
    },
    {
        "pattern": re.compile(r'(onerror|onload|onmouseover|onfocus|onclick|ontoggle|onstart)\s*=', re.I),
        "vuln_type": "XSS", "cwe": "CWE-79", "severity": "high",
        "explanation": "HTML event handler attributes can execute JavaScript when triggered, enabling XSS attacks.",
        "fix": "Remove inline event handlers. Attach events programmatically after sanitizing user data.",
    },
    {
        "pattern": re.compile(r'\.(innerHTML|outerHTML)\s*=', re.I),
        "vuln_type": "XSS", "cwe": "CWE-79", "severity": "high",
        "explanation": "Setting innerHTML with unsanitized data allows attackers to inject scripts.",
        "fix": "Use textContent or a sanitization library (DOMPurify) before inserting into DOM.",
    },
    {
        "pattern": re.compile(r'dangerouslySetInnerHTML', re.I),
        "vuln_type": "XSS", "cwe": "CWE-79", "severity": "high",
        "explanation": "React's dangerouslySetInnerHTML bypasses its built-in XSS protection.",
        "fix": "Sanitize with DOMPurify before passing to dangerouslySetInnerHTML, or restructure to avoid it.",
    },
    {
        "pattern": re.compile(r'document\.write\s*\(', re.I),
        "vuln_type": "XSS", "cwe": "CWE-79", "severity": "high",
        "explanation": "document.write can inject unsanitized content directly into the page.",
        "fix": "Use DOM methods (createElement, textContent) instead of document.write.",
    },
    {
        "pattern": re.compile(
            r'(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\s+.*'
            r'(\+\s*\w|\%s[^,]|f["\']|\.format\(|\' *\+)', re.I),
        "vuln_type": "SQL Injection", "cwe": "CWE-89", "severity": "critical",
        "explanation": "Building SQL queries with string concatenation/formatting allows attackers to inject arbitrary SQL, potentially reading or deleting entire databases.",
        "fix": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
    },
    {
        "pattern": re.compile(r"OR\s+['\"]?1['\"]?\s*=\s*['\"]?1", re.I),
        "vuln_type": "SQL Injection", "cwe": "CWE-89", "severity": "critical",
        "explanation": "The classic OR 1=1 tautology bypasses authentication and WHERE clause filtering.",
        "fix": "Never embed user input directly in SQL. Use parameterized queries or an ORM.",
    },
    {
        "pattern": re.compile(r'os\.(system|popen)\s*\(.*\+', re.I),
        "vuln_type": "Command Injection", "cwe": "CWE-78", "severity": "critical",
        "explanation": "Concatenating user input into OS commands allows arbitrary command execution on the server.",
        "fix": "Use subprocess.run() with a list of arguments (shell=False). Validate and whitelist inputs.",
    },
    {
        "pattern": re.compile(r'subprocess\.\w+\(.*shell\s*=\s*True', re.I),
        "vuln_type": "Command Injection", "cwe": "CWE-78", "severity": "critical",
        "explanation": "shell=True passes the command through the system shell, enabling injection via metacharacters.",
        "fix": "Use shell=False with a list of arguments: subprocess.run(['cmd', 'arg1', 'arg2'])",
    },
    {
        "pattern": re.compile(r'\b(eval|exec)\s*\(', re.I),
        "vuln_type": "Code Injection", "cwe": "CWE-95", "severity": "critical",
        "explanation": "eval()/exec() execute arbitrary code. If user input reaches them, attackers gain full control.",
        "fix": "Avoid eval/exec entirely. Use ast.literal_eval() for safe parsing, or JSON for data interchange.",
    },
    {
        "pattern": re.compile(r'pickle\.(load|loads)\s*\(', re.I),
        "vuln_type": "Unsafe Deserialization", "cwe": "CWE-502", "severity": "critical",
        "explanation": "pickle can execute arbitrary code during deserialization — never use with untrusted data.",
        "fix": "Use JSON or MessagePack for data exchange. If pickle is required, only load from trusted, verified sources.",
    },
    {
        "pattern": re.compile(r'yaml\.load\s*\([^)]*(?!Loader\s*=\s*yaml\.SafeLoader)', re.I),
        "vuln_type": "Unsafe Deserialization", "cwe": "CWE-502", "severity": "high",
        "explanation": "yaml.load() without SafeLoader can execute arbitrary Python objects.",
        "fix": "Use yaml.safe_load() or yaml.load(data, Loader=yaml.SafeLoader).",
    },
    {
        "pattern": re.compile(
            r'(password|secret|api_key|token|private_key|aws_secret)\s*=\s*["\'][^"\']{4,}["\']', re.I),
        "vuln_type": "Hardcoded Credentials", "cwe": "CWE-798", "severity": "high",
        "explanation": "Hardcoded secrets in source code can be extracted from version control or compiled binaries.",
        "fix": "Store secrets in environment variables or a vault service. Use os.environ.get('SECRET').",
    },
    {
        "pattern": re.compile(r'\b(gets|strcpy|strcat|sprintf|scanf)\s*\(', re.I),
        "vuln_type": "Buffer Overflow", "cwe": "CWE-120", "severity": "critical",
        "explanation": "These C functions don't check buffer bounds, enabling stack/heap overflow attacks.",
        "fix": "Use bounded alternatives: fgets, strncpy, strncat, snprintf.",
    },
    {
        "pattern": re.compile(r'\b(md5|sha1|sha-1)\b|getInstance\s*\(\s*["\']?(DES|ECB)', re.I),
        "vuln_type": "Weak Cryptography", "cwe": "CWE-328", "severity": "medium",
        "explanation": "MD5, SHA-1, DES, and ECB mode are cryptographically broken or weak.",
        "fix": "Use SHA-256 or SHA-3 for hashing. Use AES-GCM for encryption. Use bcrypt/argon2 for passwords.",
    },
    {
        "pattern": re.compile(r'(Math\.random|random\.random)\s*\(', re.I),
        "vuln_type": "Weak Randomness", "cwe": "CWE-330", "severity": "low",
        "explanation": "Math.random()/random.random() are not cryptographically secure — predictable for tokens/sessions.",
        "fix": "Use crypto.randomBytes() (Node) or secrets.token_hex() (Python) for security-sensitive randomness.",
    },
    {
        "pattern": re.compile(r'Runtime\.getRuntime\(\)\s*\.exec\s*\(', re.I),
        "vuln_type": "Command Injection", "cwe": "CWE-78", "severity": "critical",
        "explanation": "Runtime.exec() with user input allows arbitrary command execution on the server.",
        "fix": "Use ProcessBuilder with a fixed command list. Never pass unsanitized user input.",
    },
    {
        "pattern": re.compile(r'child_process\.(exec|execSync)\s*\(', re.I),
        "vuln_type": "Command Injection", "cwe": "CWE-78", "severity": "critical",
        "explanation": "child_process.exec runs commands through a shell, enabling injection attacks.",
        "fix": "Use child_process.execFile() or spawn() with argument arrays instead.",
    },
    {
        "pattern": re.compile(r'new\s+Function\s*\(', re.I),
        "vuln_type": "Code Injection", "cwe": "CWE-95", "severity": "critical",
        "explanation": "new Function() dynamically creates functions from strings — equivalent to eval().",
        "fix": "Avoid dynamic function creation. Use predefined functions or a safe expression parser.",
    },
    {
        "pattern": re.compile(r'ObjectInputStream.*readObject\s*\(', re.I | re.S),
        "vuln_type": "Unsafe Deserialization", "cwe": "CWE-502", "severity": "critical",
        "explanation": "Java ObjectInputStream.readObject() can execute arbitrary code via crafted serialized objects.",
        "fix": "Use a whitelist-based ObjectInputFilter, or switch to JSON/protobuf for data exchange.",
    },
    {
        "pattern": re.compile(r'console\.log\s*\(.*(?:token|password|secret|auth|key)', re.I),
        "vuln_type": "Sensitive Data in Logs", "cwe": "CWE-532", "severity": "medium",
        "explanation": "Logging sensitive data like tokens or passwords can expose credentials in log files.",
        "fix": "Never log sensitive values. Use structured logging with redaction for sensitive fields.",
    },
    {
        "pattern": re.compile(r'\bsystem\s*\(\s*\w', re.I),
        "vuln_type": "Command Injection", "cwe": "CWE-78", "severity": "high",
        "explanation": "The system() function passes input to the OS shell, enabling command injection.",
        "fix": "Use execvp() or a safer alternative. Validate and whitelist all inputs.",
    },
    {
        "pattern": re.compile(r'printf\s*\(\s*\w+\s*\)', re.I),
        "vuln_type": "Format String", "cwe": "CWE-134", "severity": "high",
        "explanation": "Passing user-controlled strings as the format argument to printf enables format string attacks.",
        "fix": 'Always use a fixed format string: printf("%s", user_input);',
    },
    {
        "pattern": re.compile(r'mktemp\s*\(', re.I),
        "vuln_type": "Insecure Temp File", "cwe": "CWE-377", "severity": "medium",
        "explanation": "mktemp() creates predictable filenames, enabling race condition attacks.",
        "fix": "Use mkstemp() which creates and opens the file atomically.",
    },
]


def rule_based_scan(code: str) -> list[dict]:
    """Run rule-based pattern matching."""
    findings = []
    for rule in RULES:
        matches = list(rule["pattern"].finditer(code))
        for m in matches:
            line_num = code[:m.start()].count("\n") + 1
            findings.append({
                "line": line_num,
                "match": m.group()[:80],
                "vuln_type": rule["vuln_type"],
                "cwe": rule["cwe"],
                "severity": rule["severity"],
                "explanation": rule["explanation"],
                "fix": rule["fix"],
                "source": "rule",
            })
    return findings


def ml_predict(code: str) -> dict:
    """Run ML model on the full code snippet."""
    try:
        model = _get_model()
        prob = model.predict_proba([code])[0][1]
        return {
            "vulnerable": prob > 0.5,
            "confidence": round(float(prob), 4),
            "source": "ml_model",
        }
    except FileNotFoundError:
        return {"vulnerable": False, "confidence": 0.0, "source": "rules_only_fallback"}


def scan_code(code: str) -> dict:
    """
    Combined scan: rule-based + ML model.
    Replaces the old Groq API enrichment.
    """
    # 1. Rule-based findings
    rule_findings = rule_based_scan(code)

    # 2. ML overall prediction
    ml_result = ml_predict(code)

    # 3. Per-line ML analysis
    line_predictions = []
    try:
        model = _get_model()
        lines = code.strip().split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue
            prob = model.predict_proba([stripped])[0][1]
            if prob > 0.85:
                line_predictions.append({
                    "line": i, "snippet": stripped[:100],
                    "confidence": round(float(prob), 4), "source": "ml_model",
                })
    except FileNotFoundError:
        pass

    # 4. Merge — rules take priority, ML fills gaps
    flagged_lines = {f["line"] for f in rule_findings}
    for lp in line_predictions:
        if lp["line"] not in flagged_lines:
            rule_findings.append({
                "line": lp["line"],
                "match": lp["snippet"],
                "vuln_type": "Potentially Unsafe Pattern",
                "cwe": "N/A",
                "severity": "medium" if lp["confidence"] > 0.8 else "low",
                "explanation": f"ML model flagged this line with {lp['confidence']:.0%} confidence as potentially vulnerable.",
                "fix": "Review this line for security issues — ensure inputs are validated and outputs are sanitized.",
                "source": "ml_model",
            })

    is_vulnerable = len(rule_findings) > 0 or ml_result["vulnerable"]

    return {
        "vulnerable": is_vulnerable,
        "overall_confidence": ml_result["confidence"],
        "total_findings": len(rule_findings),
        "findings": sorted(rule_findings, key=lambda f: f["line"]),
        "severity_counts": _count_severities(rule_findings),
    }


def _count_severities(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "info")
        if sev in counts:
            counts[sev] += 1
    return counts