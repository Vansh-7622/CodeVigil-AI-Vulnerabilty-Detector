"""
CodeVigil - Vulnerability Detection Engine v2
Supports: Python (AST), JavaScript, TypeScript, Java, C/C++ (regex-based)
"""

import ast
import re
from dataclasses import dataclass
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


class PythonAnalyzer(ast.NodeVisitor):
    DANGEROUS_CALLS = {
        "eval": ("CWE-95", "Code Injection", "critical"),
        "exec": ("CWE-95", "Code Injection", "critical"),
        "compile": ("CWE-95", "Code Injection via compile()", "high"),
        "__import__": ("CWE-502", "Dynamic Import", "medium"),
    }
    DANGEROUS_MODULES = {
        "pickle": ("CWE-502", "Deserialization of Untrusted Data", "critical"),
        "marshal": ("CWE-502", "Deserialization of Untrusted Data", "high"),
        "shelve": ("CWE-502", "Deserialization of Untrusted Data", "high"),
        "yaml": ("CWE-502", "Deserialization of Untrusted Data", "high"),
    }
    DANGEROUS_OS = {"system", "popen", "popen2", "popen3", "popen4"}
    DANGEROUS_SUB = {"call", "Popen", "run", "check_output", "check_call", "getoutput", "getstatusoutput"}

    def __init__(self, lines):
        self.lines = lines
        self.vulns = []
        self.imports = {}

    def _snip(self, n):
        return self.lines[n - 1].rstrip() if 0 < n <= len(self.lines) else ""

    def _add(self, node, sev, cid, cname, title):
        self.vulns.append(Vulnerability(node.lineno, getattr(node, "end_lineno", None), node.col_offset, sev, cid, cname, title, self._snip(node.lineno)))

    def visit_Import(self, node):
        for a in node.names:
            self.imports[a.asname or a.name] = a.name
            if a.name in self.DANGEROUS_MODULES:
                c, n, s = self.DANGEROUS_MODULES[a.name]
                self._add(node, s, c, n, f"Import of dangerous module '{a.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            r = node.module.split(".")[0]
            if r in self.DANGEROUS_MODULES:
                c, n, s = self.DANGEROUS_MODULES[r]
                self._add(node, s, c, n, f"Import from dangerous module '{node.module}'")
            for a in node.names:
                self.imports[a.asname or a.name] = f"{node.module}.{a.name}"
        self.generic_visit(node)

    def visit_Call(self, node):
        fn = self._resolve(node)
        if fn in self.DANGEROUS_CALLS:
            c, n, s = self.DANGEROUS_CALLS[fn]
            self._add(node, s, c, n, f"Use of dangerous function '{fn}()'")
        if fn and fn.startswith("os.") and fn.split(".")[-1] in self.DANGEROUS_OS:
            self._add(node, "critical", "CWE-78", "OS Command Injection", f"Use of '{fn}()' — vulnerable to command injection")
        if fn and "subprocess" in fn and fn.split(".")[-1] in self.DANGEROUS_SUB:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self._add(node, "critical", "CWE-78", "OS Command Injection", f"'{fn}()' called with shell=True")
        if fn and fn.endswith(".execute"):
            if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                self._add(node, "critical", "CWE-89", "SQL Injection", "SQL query built with string formatting — use parameterized queries")
            if node.args and isinstance(node.args[0], ast.Call):
                inner = self._resolve(node.args[0])
                if inner and inner.endswith(".format"):
                    self._add(node, "critical", "CWE-89", "SQL Injection", "SQL query built with .format() — use parameterized queries")
        if fn and fn.endswith("yaml.load"):
            safe = any(kw.arg == "Loader" and isinstance(kw.value, ast.Attribute) and "Safe" in kw.value.attr for kw in node.keywords)
            if not safe:
                self._add(node, "critical", "CWE-502", "Deserialization of Untrusted Data", "yaml.load() without SafeLoader")
        if fn and "pickle.load" in fn:
            self._add(node, "critical", "CWE-502", "Deserialization of Untrusted Data", f"'{fn}()' can execute arbitrary code")
        if fn and fn.startswith("hashlib.") and fn.split(".")[-1] in ("md5", "sha1"):
            self._add(node, "medium", "CWE-328", "Use of Weak Hash", f"'{fn.split('.')[-1]}' is cryptographically weak — use sha256+")
        if fn and fn.endswith(".run"):
            for kw in node.keywords:
                if kw.arg == "debug" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self._add(node, "high", "CWE-489", "Active Debug Code", "debug=True in production")
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and len(node.value) >= 16:
            pl = self._snip(node.lineno).lower()
            if any(k in pl for k in ["password", "secret", "api_key", "apikey", "token", "private_key", "access_key", "auth", "credential"]):
                self._add(node, "high", "CWE-798", "Hardcoded Credentials", "Possible hardcoded secret/credential")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self._add(node, "low", "CWE-396", "Overly Broad Catch", "Bare 'except:' catches all exceptions")
        self.generic_visit(node)

    def visit_Assert(self, node):
        self._add(node, "info", "CWE-617", "Reachable Assertion", "assert removed with -O flag — don't use for security")
        self.generic_visit(node)

    def _resolve(self, node):
        if isinstance(node.func, ast.Name):
            return self.imports.get(node.func.id, node.func.id)
        if isinstance(node.func, ast.Attribute):
            parts = []
            cur = node.func
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(self.imports.get(cur.id, cur.id))
            parts.reverse()
            return ".".join(parts)
        return None


def _regex_scan(code, rules, comment_prefixes=("//", "/*")):
    vulns = []
    for i, line in enumerate(code.split("\n"), 1):
        s = line.strip()
        if any(s.startswith(p) for p in comment_prefixes):
            continue
        for pat, sev, cid, cname, title in rules:
            if pat.search(line):
                vulns.append(Vulnerability(i, i, 0, sev, cid, cname, title, line.rstrip()))
    return vulns


JS_RULES = [
    (re.compile(r'\beval\s*\('), "critical", "CWE-95", "Code Injection", "Use of eval() — executes arbitrary code"),
    (re.compile(r'\.innerHTML\s*='), "high", "CWE-79", "XSS", "Direct innerHTML assignment — use textContent or sanitize"),
    (re.compile(r'document\.write\s*\('), "high", "CWE-79", "XSS", "document.write() can inject unsanitized content"),
    (re.compile(r'\.outerHTML\s*='), "high", "CWE-79", "XSS", "Direct outerHTML assignment — potential XSS"),
    (re.compile(r'new\s+Function\s*\('), "critical", "CWE-95", "Code Injection", "new Function() is equivalent to eval()"),
    (re.compile(r'setTimeout\s*\(\s*["\']'), "high", "CWE-95", "Code Injection", "setTimeout with string acts like eval()"),
    (re.compile(r'setInterval\s*\(\s*["\']'), "high", "CWE-95", "Code Injection", "setInterval with string acts like eval()"),
    (re.compile(r'(password|secret|api_key|apikey|token|private_key)\s*[:=]\s*["\'][^"\']{8,}'), "high", "CWE-798", "Hardcoded Credentials", "Possible hardcoded secret/credential"),
    (re.compile(r'__proto__'), "medium", "CWE-1321", "Prototype Pollution", "Direct __proto__ access"),
    (re.compile(r'JSON\.parse\s*\(\s*(req|request)'), "medium", "CWE-502", "Unsafe Deserialization", "Parsing untrusted JSON without validation"),
    (re.compile(r'child_process'), "high", "CWE-78", "Command Injection", "child_process — validate and sanitize inputs"),
    (re.compile(r'\.exec\s*\(\s*(req|request|user)'), "critical", "CWE-78", "Command Injection", "Executing commands with user input"),
    (re.compile(r'console\.(log|debug|info)\s*\(.*?(password|token|secret|key)', re.I), "medium", "CWE-532", "Sensitive Info in Logs", "Logging sensitive data"),
    (re.compile(r'Math\.random\s*\('), "low", "CWE-330", "Insufficient Randomness", "Math.random() is not cryptographically secure"),
    (re.compile(r'(cors\s*\(\s*\)|origin\s*:\s*["\']?\*)'), "medium", "CWE-942", "Permissive CORS", "Wildcard CORS allows any origin"),
    (re.compile(r'dangerouslySetInnerHTML'), "high", "CWE-79", "XSS", "dangerouslySetInnerHTML bypasses React XSS protection"),
    (re.compile(r'require\s*\(\s*(req|user|input)', re.I), "critical", "CWE-95", "Code Injection", "Dynamic require() with user input"),
]

TS_EXTRA = [
    (re.compile(r'\bas\s+any\b'), "low", "CWE-704", "Type Safety Bypass", "'as any' bypasses TypeScript type safety"),
    (re.compile(r'@ts-ignore'), "info", "CWE-710", "Coding Standards", "@ts-ignore suppresses type checking"),
    (re.compile(r'@ts-nocheck'), "medium", "CWE-710", "Coding Standards", "@ts-nocheck disables type checking for entire file"),
    (re.compile(r':\s*any\b'), "low", "CWE-704", "Type Safety Bypass", "Explicit 'any' type reduces type safety"),
]

JAVA_RULES = [
    (re.compile(r'(Statement|createStatement)\s*\('), "high", "CWE-89", "SQL Injection", "Using Statement — use PreparedStatement instead"),
    (re.compile(r'\.execute(Query|Update)\s*\(\s*["\'].*?\+'), "critical", "CWE-89", "SQL Injection", "SQL with string concatenation — use PreparedStatement"),
    (re.compile(r'\.execute(Query|Update)\s*\(\s*String\.format'), "critical", "CWE-89", "SQL Injection", "SQL with String.format — use PreparedStatement"),
    (re.compile(r'Runtime\.getRuntime\(\)\.exec\s*\('), "critical", "CWE-78", "Command Injection", "Runtime.exec() — validate inputs"),
    (re.compile(r'ProcessBuilder\s*\('), "high", "CWE-78", "Command Injection", "ProcessBuilder — ensure inputs are sanitized"),
    (re.compile(r'ObjectInputStream'), "critical", "CWE-502", "Unsafe Deserialization", "ObjectInputStream can deserialize malicious objects"),
    (re.compile(r'\.readObject\s*\('), "critical", "CWE-502", "Unsafe Deserialization", "readObject() can execute arbitrary code"),
    (re.compile(r'XMLDecoder'), "critical", "CWE-502", "Unsafe Deserialization", "XMLDecoder can execute arbitrary code"),
    (re.compile(r'(password|secret|apiKey|token)\s*=\s*"[^"]{8,}"'), "high", "CWE-798", "Hardcoded Credentials", "Possible hardcoded credential"),
    (re.compile(r'MessageDigest\.getInstance\s*\(\s*"(MD5|SHA-?1)"'), "medium", "CWE-328", "Weak Hash", "MD5/SHA1 is weak — use SHA-256+"),
    (re.compile(r'DES|DESede|Blowfish'), "medium", "CWE-327", "Weak Crypto", "DES/3DES/Blowfish — use AES-256"),
    (re.compile(r'ECB'), "medium", "CWE-327", "Weak Crypto", "ECB mode is insecure — use GCM"),
    (re.compile(r'DocumentBuilderFactory|SAXParserFactory'), "high", "CWE-611", "XXE", "XML parser may be vulnerable to XXE"),
    (re.compile(r'new\s+File\s*\(.*?(req|request|user|input)'), "high", "CWE-22", "Path Traversal", "File path from user input — canonicalize paths"),
    (re.compile(r'(logger|log|System\.out)\.(info|debug|print).*?(password|token|secret)', re.I), "medium", "CWE-532", "Sensitive Info in Logs", "Logging sensitive data"),
    (re.compile(r'NullCipher'), "critical", "CWE-327", "Null Encryption", "NullCipher provides no encryption"),
    (re.compile(r'new\s+Random\s*\('), "low", "CWE-330", "Insufficient Randomness", "java.util.Random is predictable — use SecureRandom"),
]

C_RULES = [
    (re.compile(r'\bgets\s*\('), "critical", "CWE-120", "Buffer Overflow", "gets() has no bounds checking — use fgets()"),
    (re.compile(r'\bstrcpy\s*\('), "high", "CWE-120", "Buffer Overflow", "strcpy() — use strncpy() or strlcpy()"),
    (re.compile(r'\bstrcat\s*\('), "high", "CWE-120", "Buffer Overflow", "strcat() — use strncat() or strlcat()"),
    (re.compile(r'\bsprintf\s*\('), "high", "CWE-120", "Buffer Overflow", "sprintf() can overflow — use snprintf()"),
    (re.compile(r'\bscanf\s*\(\s*"%s"'), "high", "CWE-120", "Buffer Overflow", "scanf %s has no width limit — use %Ns"),
    (re.compile(r'\bvsprintf\s*\('), "high", "CWE-120", "Buffer Overflow", "vsprintf() — use vsnprintf()"),
    (re.compile(r'\bprintf\s*\(\s*[a-zA-Z_]'), "high", "CWE-134", "Format String", "printf() with variable format string"),
    (re.compile(r'\bsystem\s*\('), "critical", "CWE-78", "Command Injection", "system() executes shell commands"),
    (re.compile(r'\bpopen\s*\('), "high", "CWE-78", "Command Injection", "popen() executes shell commands"),
    (re.compile(r'\bmalloc\s*\(.*\*.*\)'), "medium", "CWE-190", "Integer Overflow", "malloc() with multiplication — check for overflow"),
    (re.compile(r'\batoi\s*\('), "low", "CWE-190", "No Error Checking", "atoi() — use strtol() instead"),
    (re.compile(r'(password|secret|api_key|token)\s*\[\s*\]\s*=\s*"[^"]{8,}"'), "high", "CWE-798", "Hardcoded Credentials", "Hardcoded credential in string"),
    (re.compile(r'#define\s+(PASSWORD|SECRET|API_KEY|TOKEN)\s+"'), "high", "CWE-798", "Hardcoded Credentials", "Hardcoded credential in macro"),
    (re.compile(r'\brand\s*\(\s*\)'), "low", "CWE-330", "Insufficient Randomness", "rand() is predictable — use /dev/urandom"),
    (re.compile(r'\bmktemp\s*\('), "medium", "CWE-377", "Insecure Temp File", "mktemp() — use mkstemp()"),
]

SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "java", "c", "cpp"]

def scan_code(code: str, language: str) -> list[Vulnerability]:
    language = language.lower().strip()
    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [Vulnerability(e.lineno or 1, None, e.offset or 0, "info", "N/A", "Syntax Error", f"Could not parse: {e.msg}", "")]
        a = PythonAnalyzer(code.split("\n"))
        a.visit(tree)
        return a.vulns
    elif language == "javascript":
        return _regex_scan(code, JS_RULES)
    elif language == "typescript":
        return _regex_scan(code, JS_RULES + TS_EXTRA)
    elif language == "java":
        return _regex_scan(code, JAVA_RULES)
    elif language in ("c", "cpp"):
        return _regex_scan(code, C_RULES)
    return []