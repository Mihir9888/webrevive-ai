"""WebRevive AI - FastAPI Backend Service.

Provides RESTful endpoints for web accessibility auditing, local LLM refactoring,
and compliance report generation.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field, HttpUrl

from webrevive_cli.commands.analyze import query_ollama
from webrevive_cli.commands.report import (
    compute_statistics,
    generate_html_report,
    generate_markdown_report,
)
from webrevive_cli.commands.scan import execute_playwright_scan, filter_violations

# In-memory storage for scans (in production backed by PostgreSQL / SQLAlchemy)
SCANS_DB: Dict[str, Dict[str, Any]] = {}

app = FastAPI(
    title="WebRevive AI API",
    description="Autonomous AI-Based Web Accessibility Auditing and Automated Content Refactoring Engine",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS Configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://frontend:3000")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")


class ScanRequest(BaseModel):
    url: str = Field(..., description="Target web page URL to audit")
    wcag_filter: Optional[str] = Field(None, description="Comma-separated WCAG tags, e.g. 'wcag2a,wcag2aa'")
    timeout_sec: int = Field(30, ge=5, le=120, description="Page timeout in seconds")
    headless: bool = Field(True, description="Run headless browser")


class AnalyzeRequest(BaseModel):
    scan_id: Optional[str] = Field(None, description="Existing scan ID to analyze")
    violation: Optional[Dict[str, Any]] = Field(None, description="Direct violation payload to analyze")
    model: Optional[str] = Field(None, description="Ollama model to use")


@app.get("/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    """Container health check probe."""
    return {
        "status": "healthy",
        "service": "webrevive-backend",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/scan", status_code=status.HTTP_201_CREATED, tags=["Auditing"])
def create_scan(request: ScanRequest) -> Dict[str, Any]:
    """Execute Playwright + axe-core accessibility audit on target URL."""
    scan_id = str(uuid.uuid4())

    try:
        results = execute_playwright_scan(
            url=request.url,
            wcag_filter=request.wcag_filter,
            timeout_sec=request.timeout_sec,
            headless=request.headless,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scanning failed: {str(exc)}",
        )

    stats = compute_statistics(results)
    scan_record = {
        "id": scan_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "url": results.get("url"),
        "title": results.get("title"),
        "statistics": stats,
        "violations": results.get("violations", []),
        "passes_count": len(results.get("passes", [])),
        "inapplicable_count": len(results.get("inapplicable", [])),
        "incomplete_count": len(results.get("incomplete", [])),
        "raw_results": results,
    }
    SCANS_DB[scan_id] = scan_record

    return {
        "scan_id": scan_id,
        "url": scan_record["url"],
        "title": scan_record["title"],
        "health_score": stats["health_score"],
        "violations_count": stats["total_violations"],
        "critical_count": stats["critical_count"],
        "serious_count": stats["serious_count"],
        "moderate_count": stats["moderate_count"],
        "minor_count": stats["minor_count"],
    }


@app.get("/api/v1/scan/{scan_id}", tags=["Auditing"])
def get_scan(scan_id: str) -> Dict[str, Any]:
    """Retrieve complete audit details for a specific scan ID."""
    record = SCANS_DB.get(scan_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record '{scan_id}' not found.",
        )
    return record


@app.post("/api/v1/analyze", tags=["AI Refactoring"])
def analyze_violation(request: AnalyzeRequest) -> Dict[str, Any]:
    """Analyze an accessibility violation using the local Ollama LLM."""
    violation_data = None
    target_url = "https://example.com"

    if request.scan_id:
        record = SCANS_DB.get(request.scan_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan ID '{request.scan_id}' not found.",
            )
        violations = record.get("violations", [])
        if not violations:
            return {"message": "No violations present in this scan."}
        violation_data = violations[0]
        target_url = record.get("url", target_url)
    elif request.violation:
        violation_data = request.violation
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'scan_id' or 'violation' object.",
        )

    model_name = request.model or OLLAMA_MODEL

    from webrevive_cli.commands.analyze import build_analysis_prompt
    prompt = build_analysis_prompt(violation_data, target_url)

    try:
        response = query_ollama(
            prompt=prompt,
            model=model_name,
            ollama_url=OLLAMA_BASE_URL,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama AI inference failed: {str(exc)}. Ensure Ollama is running.",
        )

    return {
        "model": model_name,
        "rule_id": violation_data.get("id"),
        "impact": violation_data.get("impact"),
        "ai_solution": response,
    }


@app.get("/api/v1/reports/{scan_id}/export", tags=["Reporting"])
def export_report(
    scan_id: str,
    format: str = Query("html", enum=["html", "md", "json"]),
):
    """Export formatted accessibility audit report in HTML, Markdown, or JSON."""
    record = SCANS_DB.get(scan_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record '{scan_id}' not found.",
        )

    raw_results = record.get("raw_results", record)

    if format == "html":
        content = generate_html_report(raw_results, title=f"Audit Report: {record.get('title')}")
        return HTMLResponse(content=content)
    elif format == "md":
        content = generate_markdown_report(raw_results, title=f"Audit Report: {record.get('title')}")
        return PlainTextResponse(content=content, media_type="text/markdown")
    else:
        return record
