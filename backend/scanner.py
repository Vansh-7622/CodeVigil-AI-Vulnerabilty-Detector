"""
CodeVigil - Vulnerability Detection Engine
Uses Python AST parsing + pattern-based rules to detect common security vulnerabilities.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Vulnerability:
    line: int
    end_line: int | None
    column: int
    severity: Literal["critical", "high", "medium", "low", "info"]
    cwe_id: str
    cwe_name: str
    title: str
    snippet: str
    description: str = ""
    fix_suggestion: str = ""


# ── Python AST-based Rules ──────────────────────────────────────────

class PythonAnalyzer(ast.NodeVisitor):
    """Walk the AST and flag vulnerable patterns."""

    DANGEROUS_CALLS = {
        "eval": ("CWE-95", "Improper Neutralization of Directives in Dynamically Evaluated Code", "critical"),
        "exec": ("CWE-95", "Improper Neutralization of Directives in Dynamically Evaluated Code", "critical"),
        "compile": ("CWE-95", "Code Injection via compile()", "high"),
        "__import__": ("CWE-502", "Dynamic Import", "medium"),
    }

    DANGEROUS_MODULES = {
        "pickle": ("CWE-502", "Deserialization of Untrusted Data", "critical"),
        "marshal": ("CWE-502", "Deserialization of Untrusted Data", "high"),
        "shelve": ("CWE-502", "Deserialization of Untrusted Data", "high"),
        "yaml": ("CWE-502", "Deserialization of Untrusted Data (use yaml.safe_load)", "high"),
    }

    DANGEROUS_OS_CALLS = {"system", "popen", "popen2", "popen3", "popen4"}
    DANGEROUS_SUBPROCESS = {"call", "Popen", "run", "check_output", "check_call", "getoutput", "getstatusoutput"}

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.vulns: list[Vulnerability] = []
        self.imports: dict[str, str] = {}  # alias -> module

    def _snippet(self, lineno: int) -> str:
        idx = lineno - 1
        if 0 <= idx < len(self.source_lines):
            return self.source_lines[idx].rstrip()
        return ""

    def _add(self, node: ast.AST, severity, cwe_id, cwe_name, title):
        self.vulns.append(Vulnerability(
            line=node.lineno,
            end_line=getattr(node, "end_lineno", None),
            column=node.col_offset,
            severity=severity,
            cwe_id=cwe_id,
            cwe_name=cwe_name,
            title=title,
            snippet=self._snippet(node.lineno),
        ))

    # ── Visitors ──

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = alias.name
            if alias.name in self.DANGEROUS_MODULES:
                cwe_id, cwe_name, sev = self.DANGEROUS_MODULES[alias.name]
                self._add(node, sev, cwe_id, cwe_name, f"Import of dangerous module '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            mod_root = node.module.split(".")[0]
            if mod_root in self.DANGEROUS_MODULES:
                cwe_id, cwe_name, sev = self.DANGEROUS_MODULES[mod_root]
                self._add(node, sev, cwe_id, cwe_name, f"Import from dangerous module '{node.module}'")
            for alias in node.names:
                name = alias.asname or alias.name
                self.imports[name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._resolve_call_name(node)

        # Direct dangerous calls: eval(), exec()
        if func_name in self.DANGEROUS_CALLS:
            cwe_id, cwe_name, sev = self.DANGEROUS_CALLS[func_name]
            self._add(node, sev, cwe_id, cwe_name, f"Use of dangerous function '{func_name}()'")

        # os.system(), os.popen(), etc.
        if func_name and func_name.startswith("os."):
            method = func_name.split(".")[-1]
            if method in self.DANGEROUS_OS_CALLS:
                self._add(node, "critical", "CWE-78", "OS Command Injection",
                          f"Use of '{func_name}()' — vulnerable to command injection")

        # subprocess with shell=True
        if func_name and ("subprocess" in func_name):
            method = func_name.split(".")[-1]
            if method in self.DANGEROUS_SUBPROCESS:
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self._add(node, "critical", "CWE-78", "OS Command Injection",
                                  f"'{func_name}()' called with shell=True")

        # SQL injection: cursor.execute() with f-string or format
        if func_name and func_name.endswith(".execute"):
            if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                self._add(node, "critical", "CWE-89", "SQL Injection",
                          "SQL query built with string formatting — use parameterized queries")
            if node.args and isinstance(node.args[0], ast.Call):
                inner = self._resolve_call_name(node.args[0])
                if inner and inner.endswith(".format"):
                    self._add(node, "critical", "CWE-89", "SQL Injection",
                              "SQL query built with .format() — use parameterized queries")

        # yaml.load() without SafeLoader
        if func_name and func_name.endswith("yaml.load"):
            safe = any(
                (kw.arg == "Loader" and isinstance(kw.value, ast.Attribute) and "Safe" in kw.value.attr)
                for kw in node.keywords
            )
            if not safe:
                self._add(node, "critical", "CWE-502", "Deserialization of Untrusted Data",
                          "yaml.load() without SafeLoader — use yaml.safe_load()")

        # pickle.loads / pickle.load
        if func_name and "pickle.load" in func_name:
            self._add(node, "critical", "CWE-502", "Deserialization of Untrusted Data",
                      f"'{func_name}()' can execute arbitrary code on untrusted data")

        # hashlib with weak algorithms
        if func_name and func_name.startswith("hashlib."):
            algo = func_name.split(".")[-1]
            if algo in ("md5", "sha1"):
                self._add(node, "medium", "CWE-328", "Use of Weak Hash",
                          f"'{algo}' is cryptographically weak — use sha256 or better")

        # Flask/Django debug=True
        if func_name and func_name.endswith(".run"):
            for kw in node.keywords:
                if kw.arg == "debug" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self._add(node, "high", "CWE-489", "Active Debug Code",
                              "Application running with debug=True in production")

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        """Detect hardcoded secrets / credentials."""
        if isinstance(node.value, str) and len(node.value) >= 16:
            parent_line = self._snippet(node.lineno).lower()
            secret_keywords = ["password", "secret", "api_key", "apikey", "token", "private_key",
                               "access_key", "auth", "credential"]
            if any(kw in parent_line for kw in secret_keywords):
                self._add(node, "high", "CWE-798", "Hardcoded Credentials",
                          "Possible hardcoded secret/credential detected")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Bare except or overly broad except Exception."""
        if node.type is None:
            self._add(node, "low", "CWE-396", "Overly Broad Catch",
                      "Bare 'except:' catches all exceptions including KeyboardInterrupt")
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        self._add(node, "info", "CWE-617", "Reachable Assertion",
                  "assert statements are removed with -O flag — don't use for security checks")
        self.generic_visit(node)

    def _resolve_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            real = self.imports.get(node.func.id, node.func.id)
            return real
        if isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(self.imports.get(current.id, current.id))
            parts.reverse()
            return ".".join(parts)
        return None


# ── JavaScript Regex-based Rules ────────────────────────────────────

JS_RULES: list[tuple[re.Pattern, str, str, str, str]] = [
    # (pattern, severity, cwe_id, cwe_name, title)
    (re.compile(r'\beval\s*\('), "critical", "CWE-95", "Code Injection", "Use of eval() — executes arbitrary code"),
    (re.compile(r'\.innerHTML\s*='), "high", "CWE-79", "Cross-site Scripting (XSS)", "Direct innerHTML assignment — use textContent or sanitize"),
    (re.compile(r'document\.write\s*\('), "high", "CWE-79", "Cross-site Scripting (XSS)", "document.write() can inject unsanitized content"),
    (re.compile(r'\.outerHTML\s*='), "high", "CWE-79", "Cross-site Scripting (XSS)", "Direct outerHTML assignment — potential XSS vector"),
    (re.compile(r'new\s+Function\s*\('), "critical", "CWE-95", "Code Injection", "new Function() is equivalent to eval()"),
    (re.compile(r'setTimeout\s*\(\s*["\']'), "high", "CWE-95", "Code Injection", "setTimeout with string argument acts like eval()"),
    (re.compile(r'setInterval\s*\(\s*["\']'), "high", "CWE-95", "Code Injection", "setInterval with string argument acts like eval()"),
    (re.compile(r'(password|secret|api_key|apikey|token|private_key)\s*[:=]\s*["\'][^"\']{8,}'), "high", "CWE-798", "Hardcoded Credentials", "Possible hardcoded secret/credential"),
    (re.compile(r'__proto__'), "medium", "CWE-1321", "Prototype Pollution", "Direct __proto__ access — potential prototype pollution"),
    (re.compile(r'JSON\.parse\s*\(\s*(req|request)'), "medium", "CWE-502", "Deserialization of Untrusted Data", "Parsing untrusted JSON without validation"),
    (re.compile(r'child_process'), "high", "CWE-78", "OS Command Injection", "child_process usage — validate and sanitize all inputs"),
    (re.compile(r'\.exec\s*\(\s*(req|request|user)'), "critical", "CWE-78", "OS Command Injection", "Executing commands with user-controlled input"),
    (re.compile(r'console\.(log|debug|info)\s*\(.*?(password|token|secret|key)', re.IGNORECASE), "medium", "CWE-532", "Insertion of Sensitive Info into Log", "Logging potentially sensitive data"),
    (re.compile(r'Math\.random\s*\('), "low", "CWE-330", "Insufficient Randomness", "Math.random() is not cryptographically secure — use crypto.getRandomValues()"),
    (re.compile(r'(cors\s*\(\s*\)|origin\s*:\s*["\']?\*)'), "medium", "CWE-942", "Overly Permissive CORS", "Wildcard CORS allows any origin to access resources"),
]


def analyze_javascript(code: str) -> list[Vulnerability]:
    vulns = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue
        for pattern, severity, cwe_id, cwe_name, title in JS_RULES:
            if pattern.search(line):
                vulns.append(Vulnerability(
                    line=i,
                    end_line=i,
                    column=0,
                    severity=severity,
                    cwe_id=cwe_id,
                    cwe_name=cwe_name,
                    title=title,
                    snippet=line.rstrip(),
                ))
    return vulns


# ── Main Scanner Entry ──────────────────────────────────────────────

def scan_code(code: str, language: str) -> list[Vulnerability]:
    """
    Scan code for vulnerabilities.
    language: "python" or "javascript"
    """
    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [Vulnerability(
                line=e.lineno or 1, end_line=None, column=e.offset or 0,
                severity="info", cwe_id="N/A", cwe_name="Syntax Error",
                title=f"Could not parse: {e.msg}", snippet="",
            )]
        analyzer = PythonAnalyzer(code.split("\n"))
        analyzer.visit(tree)
        return analyzer.vulns

    elif language == "javascript":
        return analyze_javascript(code)

    return []
