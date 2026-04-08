"""
CodeVigil - FastAPI Backend
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scanner import scan_code, SUPPORTED_LANGUAGES
from llm_engine import enrich_all

app = FastAPI(title="CodeVigil", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    code: str
    language: str = "python"


class ScanResponse(BaseModel):
    language: str
    total_issues: int
    severity_counts: dict[str, int]
    vulnerabilities: list[dict]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan", response_model=ScanResponse)
async def scan_code_endpoint(req: ScanRequest):
    lang = req.language.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}")

    vulns = scan_code(req.code, lang)
    enriched = await enrich_all(vulns, req.code, lang)

    severity_counts = {}
    for v in enriched:
        severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1

    return ScanResponse(
        language=lang,
        total_issues=len(enriched),
        severity_counts=severity_counts,
        vulnerabilities=enriched,
    )


@app.post("/scan/file", response_model=ScanResponse)
async def scan_file_endpoint(
    file: UploadFile = File(...),
    language: str = Form(None),
):
    content = await file.read()
    try:
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 text")

    # Auto-detect language from extension
    if not language:
        name = file.filename or ""
        ext_map = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp"}
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        language = ext_map.get(ext)
        if not language:
            raise HTTPException(400, f"Could not detect language. Pass language param. Supported: {', '.join(SUPPORTED_LANGUAGES)}")

    language = language.lower().strip()
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}")

    vulns = scan_code(code, language)
    enriched = await enrich_all(vulns, code, language)

    severity_counts = {}
    for v in enriched:
        severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1

    return ScanResponse(
        language=language,
        total_issues=len(enriched),
        severity_counts=severity_counts,
        vulnerabilities=enriched,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)