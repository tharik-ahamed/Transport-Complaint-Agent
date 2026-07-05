"""
Phase 6 Executive API Routes
============================
Existing routes (unchanged):
  GET  /api/v1/health-index
  GET  /api/v1/governance/recommendations
  GET  /api/v1/heatmap
  GET  /api/v1/explanations/{id}

Report routes — path-based (NEW, spec-required):
  GET  /api/v1/reports/daily/pdf
  GET  /api/v1/reports/daily/docx
  GET  /api/v1/reports/weekly/pdf
  GET  /api/v1/reports/weekly/docx
  GET  /api/v1/reports/monthly/pdf
  GET  /api/v1/reports/monthly/docx

Report routes — query-param (kept for backward compat):
  GET  /api/v1/reports/daily?format=pdf|docx
  GET  /api/v1/reports/weekly?format=pdf|docx
  GET  /api/v1/reports/monthly?format=pdf|docx

Copilot:
  POST /api/v1/copilot/query

All endpoints require admin JWT.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import verify_token
from app.executive_engine import (
    compute_health_index,
    generate_report_data,
    build_pdf_report,
    build_docx_report,
    get_governance_recommendations,
    get_heatmap_data,
    get_ai_explanation,
    handle_copilot_query,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Phase 6 Executive"],
    dependencies=[Depends(verify_token)],
)


# ── Copilot schema ─────────────────────────────────────────────────────

class CopilotQueryRequest(BaseModel):
    question: str


# ── Internal helper ────────────────────────────────────────────────────

def _stream_report(data: dict, fmt: str, filename: str) -> StreamingResponse:
    """Build and stream a PDF or DOCX report as a file download."""
    fmt = fmt.lower().strip()
    if fmt == "docx":
        content = build_docx_report(data)
        media_type = (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        )
        ext = ".docx"
    else:
        content = build_pdf_report(data)
        media_type = "application/pdf"
        ext = ".pdf"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}{ext}"',
            "Content-Length": str(len(content)),
        },
    )


# ══════════════════════════════════════════════════════════════════════
# COPILOT
# ══════════════════════════════════════════════════════════════════════

@router.post("/copilot/query", summary="Executive AI Copilot — natural language queries")
async def copilot_query(
    body: CopilotQueryRequest,
    db: Session = Depends(get_db),
):
    """
    Answers operational questions in natural language.
    Uses OpenAI if OPENAI_API_KEY is set, then Gemini if GEMINI_API_KEY is set,
    then falls back to the built-in rule-based local engine.
    Always returns a valid response — never fails due to missing API keys.
    """
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return handle_copilot_query(db, body.question)


# ══════════════════════════════════════════════════════════════════════
# HEALTH INDEX, GOVERNANCE, HEATMAP, EXPLANATIONS  (unchanged)
# ══════════════════════════════════════════════════════════════════════

@router.get("/health-index", summary="Transport Health Index (0–100)")
async def get_health_index(db: Session = Depends(get_db)):
    """Returns a weighted operational index with qualitative rating."""
    return compute_health_index(db)


@router.get("/governance/recommendations", summary="Strategic governance recommendations")
async def get_governance_recs(db: Session = Depends(get_db)):
    """Returns prioritised governance decisions to improve transit quality."""
    return get_governance_recommendations(db)


@router.get("/heatmap", summary="Geographic complaint hotspot map")
async def get_heatmap(db: Session = Depends(get_db)):
    """Returns complaint density by incident location."""
    return get_heatmap_data(db)


@router.get("/explanations/{complaint_id}", summary="Explainable AI — severity rationale")
async def get_explanation(complaint_id: str, db: Session = Depends(get_db)):
    """Explains the AI severity and classification decision for a complaint."""
    res = get_ai_explanation(db, complaint_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


# ══════════════════════════════════════════════════════════════════════
# MANAGEMENT REPORTS — PATH-BASED  (spec requirement)
# GET /api/v1/reports/{period}/pdf
# GET /api/v1/reports/{period}/docx
# ══════════════════════════════════════════════════════════════════════

@router.get("/reports/daily/pdf", summary="Daily operations report — PDF")
async def daily_report_pdf(db: Session = Depends(get_db)):
    """Generates and downloads the daily operations report as PDF."""
    data = generate_report_data(db, "daily")
    return _stream_report(data, "pdf", "daily_operations_report")


@router.get("/reports/daily/docx", summary="Daily operations report — DOCX")
async def daily_report_docx(db: Session = Depends(get_db)):
    """Generates and downloads the daily operations report as DOCX."""
    data = generate_report_data(db, "daily")
    return _stream_report(data, "docx", "daily_operations_report")


@router.get("/reports/weekly/pdf", summary="Weekly operations report — PDF")
async def weekly_report_pdf(db: Session = Depends(get_db)):
    """Generates and downloads the weekly operations report as PDF."""
    data = generate_report_data(db, "weekly")
    return _stream_report(data, "pdf", "weekly_operations_report")


@router.get("/reports/weekly/docx", summary="Weekly operations report — DOCX")
async def weekly_report_docx(db: Session = Depends(get_db)):
    """Generates and downloads the weekly operations report as DOCX."""
    data = generate_report_data(db, "weekly")
    return _stream_report(data, "docx", "weekly_operations_report")


@router.get("/reports/monthly/pdf", summary="Monthly operations report — PDF")
async def monthly_report_pdf(db: Session = Depends(get_db)):
    """Generates and downloads the monthly operations report as PDF."""
    data = generate_report_data(db, "monthly")
    return _stream_report(data, "pdf", "monthly_operations_report")


@router.get("/reports/monthly/docx", summary="Monthly operations report — DOCX")
async def monthly_report_docx(db: Session = Depends(get_db)):
    """Generates and downloads the monthly operations report as DOCX."""
    data = generate_report_data(db, "monthly")
    return _stream_report(data, "docx", "monthly_operations_report")


# ══════════════════════════════════════════════════════════════════════
# MANAGEMENT REPORTS — QUERY-PARAM  (backward compatibility)
# GET /api/v1/reports/{period}?format=pdf|docx
# ══════════════════════════════════════════════════════════════════════

@router.get("/reports/daily", summary="Daily operations report (query-param format)")
async def daily_report(
    format: Optional[str] = Query("pdf", description="pdf or docx"),
    db: Session = Depends(get_db),
):
    data = generate_report_data(db, "daily")
    return _stream_report(data, format or "pdf", "daily_operations_report")


@router.get("/reports/weekly", summary="Weekly operations report (query-param format)")
async def weekly_report(
    format: Optional[str] = Query("pdf", description="pdf or docx"),
    db: Session = Depends(get_db),
):
    data = generate_report_data(db, "weekly")
    return _stream_report(data, format or "pdf", "weekly_operations_report")


@router.get("/reports/monthly", summary="Monthly operations report (query-param format)")
async def monthly_report(
    format: Optional[str] = Query("pdf", description="pdf or docx"),
    db: Session = Depends(get_db),
):
    data = generate_report_data(db, "monthly")
    return _stream_report(data, format or "pdf", "monthly_operations_report")
