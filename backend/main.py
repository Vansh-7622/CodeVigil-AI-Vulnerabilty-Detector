"""
main.py — CodeVigil ML Backend
No external AI APIs. Uses local ML model + rule-based engine.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from ml_engine import scan_code

app = FastAPI(title="CodeVigil ML API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    code: str
    language: Optional[str] = "auto"


class PredictRequest(BaseModel):
    code: str


@app.get("/health")
def health():
    return {"status": "ok", "model": "local_ml", "api_dependencies": "none"}


@app.post("/predict")
def predict(req: PredictRequest):
    result = scan_code(req.code)
    return {
        "vulnerable": result["vulnerable"],
        "confidence": result["overall_confidence"],
    }


@app.post("/scan")
def scan(req: ScanRequest):
    result = scan_code(req.code)

    vulnerabilities = []
    for f in result["findings"]:
        vulnerabilities.append({
            "line": f["line"],
            "severity": f["severity"],
            "cwe_id": f.get("cwe", "N/A"),
            "cwe_name": f["vuln_type"],
            "title": f["vuln_type"],
            "snippet": f.get("match", ""),
            "explanation": f["explanation"],
            "impact": "",
            "fixed_code": f.get("fix", ""),
            "source": f.get("source", "rule"),
        })

    return {
        "language": req.language,
        "total_issues": result["total_findings"],
        "severity_counts": result["severity_counts"],
        "vulnerabilities": vulnerabilities,
        "model_confidence": result["overall_confidence"],
    }


@app.post("/scan/file")
async def scan_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    content = await file.read()
    try:
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 text")

    ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript",
               ".java": "java", ".c": "c", ".cpp": "cpp"}
    if not language:
        ext = "." + file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
        language = ext_map.get(ext, "auto")

    result = scan_code(code)
    vulnerabilities = []
    for f in result["findings"]:
        vulnerabilities.append({
            "line": f["line"],
            "severity": f["severity"],
            "cwe_id": f.get("cwe", "N/A"),
            "cwe_name": f["vuln_type"],
            "title": f["vuln_type"],
            "snippet": f.get("match", ""),
            "explanation": f["explanation"],
            "impact": "",
            "fixed_code": f.get("fix", ""),
            "source": f.get("source", "rule"),
        })

    return {
        "language": language,
        "total_issues": result["total_findings"],
        "severity_counts": result["severity_counts"],
        "vulnerabilities": vulnerabilities,
        "model_confidence": result["overall_confidence"],
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)