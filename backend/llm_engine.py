"""
CodeVigil - LLM-powered vulnerability explanations and fix suggestions.
Uses Groq API directly via httpx (no SDK dependency).
"""

import os
import json
import httpx
from scanner import Vulnerability
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are CodeVigil, a security-focused code analysis assistant.
You will receive a code vulnerability finding. Your job:

1. Explain WHY this code is vulnerable in 2-3 simple sentences a student can understand.
2. Show the IMPACT — what an attacker could do.
3. Provide a FIXED code snippet that resolves the vulnerability.

Respond ONLY in this JSON format, no markdown, no backticks:
{"explanation": "...", "impact": "...", "fixed_code": "..."}
"""


async def enrich_vulnerability(vuln: Vulnerability, full_code: str, language: str) -> dict:
    lines = full_code.split("\n")
    start = max(0, vuln.line - 3)
    end = min(len(lines), vuln.line + 2)
    context = "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))

    user_msg = f"""Language: {language}
Vulnerability: {vuln.title}
CWE: {vuln.cwe_id} — {vuln.cwe_name}
Severity: {vuln.severity}

Code context (line {vuln.line} is the issue):
```
{context}
```

Vulnerable line:
```
{vuln.snippet}
```"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"].strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(raw)
            return {
                "explanation": parsed.get("explanation", ""),
                "impact": parsed.get("impact", ""),
                "fixed_code": parsed.get("fixed_code", ""),
            }
    except Exception as e:
        return {
            "explanation": f"LLM analysis unavailable: {str(e)}",
            "impact": "",
            "fixed_code": "",
        }


async def enrich_all(vulns: list[Vulnerability], full_code: str, language: str) -> list[dict]:
    import asyncio
    limited = vulns[:10]
    tasks = [enrich_vulnerability(v, full_code, language) for v in limited]
    results = await asyncio.gather(*tasks)

    enriched = []
    for vuln, llm_data in zip(limited, results):
        enriched.append({
            "line": vuln.line,
            "end_line": vuln.end_line,
            "column": vuln.column,
            "severity": vuln.severity,
            "cwe_id": vuln.cwe_id,
            "cwe_name": vuln.cwe_name,
            "title": vuln.title,
            "snippet": vuln.snippet,
            **llm_data,
        })

    for vuln in vulns[10:]:
        enriched.append({
            "line": vuln.line,
            "end_line": vuln.end_line,
            "column": vuln.column,
            "severity": vuln.severity,
            "cwe_id": vuln.cwe_id,
            "cwe_name": vuln.cwe_name,
            "title": vuln.title,
            "snippet": vuln.snippet,
            "explanation": "",
            "impact": "",
            "fixed_code": "",
        })

    return enriched