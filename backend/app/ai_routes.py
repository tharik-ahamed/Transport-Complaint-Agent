"""
Phase 2 AI Routes
=================
POST /api/v1/ai/analyze-complaint         — Re-analyze a complaint by ID  [JWT required]
GET  /api/v1/complaints/{id}/analysis     — Retrieve stored AI analysis    [JWT required]
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AIAnalysisResult, AnalyzeRequest, ComplaintIntelligenceResponse

from app import crud
from app.config import AI_ENABLED
from app.auth import verify_token    # Warning 2 fix

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["AI Analysis"])


@router.post(
    "/ai/analyze-complaint",
    response_model=AIAnalysisResult,
    dependencies=[Depends(verify_token)],   # Warning 2 fix: JWT required
    summary="Run AI analysis on a complaint — requires admin JWT",
)
async def analyze_complaint(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Run (or re-run) AI analysis on an existing complaint.
    Updates the complaint record with results and returns the full analysis.
    Requires a valid Bearer JWT token.
    """
    complaint = crud.get_complaint_by_id(db, request.complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint '{request.complaint_id}' not found",
        )

    try:
        from app.ai.agent import complaint_agent
        analysis = complaint_agent.analyze(complaint.complaint_description)
        crud.update_complaint_analysis(db, complaint.complaint_id, analysis)
        db.refresh(complaint)
    except Exception as e:
        logger.error(f"AI analysis failed for {request.complaint_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(e)}",
        )

    ai_mode = "gemini" if AI_ENABLED else "fallback"
    return AIAnalysisResult.from_complaint(complaint, ai_mode=ai_mode)


@router.get(
    "/complaints/{complaint_id}/analysis",
    response_model=AIAnalysisResult,
    dependencies=[Depends(verify_token)],   # Warning 2 fix: JWT required
    summary="Get stored AI analysis for a complaint — requires admin JWT",
)
async def get_complaint_analysis(complaint_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the stored AI analysis for a complaint.
    If the complaint has never been analyzed, AI fields will be null.
    Requires a valid Bearer JWT token.
    """
    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint '{complaint_id}' not found",
        )

    ai_mode = "gemini" if AI_ENABLED else "fallback"
    return AIAnalysisResult.from_complaint(complaint, ai_mode=ai_mode)


@router.get(
    "/complaints/{complaint_id}/intelligence",
    response_model=ComplaintIntelligenceResponse,
    dependencies=[Depends(verify_token)],   # Warning 2 fix: JWT required
    summary="Get detailed AI intelligence telemetry for a complaint — requires admin JWT",
)
async def get_complaint_intelligence(complaint_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the Phase 3 intelligence metrics for a complaint.
    Includes sentiment, classified categories, severity, priority, duplicates, and recommendation.
    Requires a valid Bearer JWT token.
    """
    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint '{complaint_id}' not found",
        )

    # Deserialize ai_categories JSON string
    categories = []
    if complaint.ai_categories:
        try:
            import json
            categories = json.loads(complaint.ai_categories)
        except Exception:
            categories = [complaint.ai_categories]
    else:
        categories = [complaint.category]

    # Structure duplicates response
    duplicates_info = {
        "duplicate_detected": bool(complaint.duplicate_detected),
        "master_incident_id": complaint.incident_id,
        "duplicate_count": complaint.duplicate_count
    }

    return ComplaintIntelligenceResponse(
        sentiment=complaint.sentiment or "Neutral",
        categories=categories,
        severity=complaint.severity or "Low",
        priority=complaint.priority_level or "P4",
        duplicates=duplicates_info,
        recommendation=complaint.recommended_action or "Review passenger complaint details and request passenger feedback."
    )

