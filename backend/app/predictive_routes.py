"""
Phase 5 Predictive Analytics Routes
=====================================
All endpoints are read-only analytics. Computation is triggered on-demand
and results are cached in the Phase 5 DB tables.

GET /api/v1/analytics/trends          — Trend analysis
GET /api/v1/analytics/routes/risk     — Route risk prediction
GET /api/v1/analytics/drivers/risk    — Driver risk assessment
GET /api/v1/analytics/buses/risk      — Bus health intelligence
GET /api/v1/analytics/forecast        — Complaint volume forecasting
GET /api/v1/analytics/recommendations — Preventive recommendations
GET /api/v1/analytics/alerts          — Smart alerts
GET /api/v1/analytics/predictive      — All-in-one response (for dashboard)

All endpoints require admin JWT.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import verify_token
from app.predictive_engine import run_all_analytics

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Phase 5 Predictive"],
    dependencies=[Depends(verify_token)],
)

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300
_cache: dict = {}


def _get_cached_or_compute(db: Session) -> dict:
    """Return cached analytics if fresh, otherwise recompute."""
    global _cache
    now = datetime.now()
    if "data" in _cache and "ts" in _cache:
        age = (now - _cache["ts"]).total_seconds()
        if age < _CACHE_TTL:
            return _cache["data"]
    result = run_all_analytics(db)
    _cache = {"data": result, "ts": now}
    return result


# ── Individual endpoints ───────────────────────────────────────────────

@router.get("/trends", summary="Trend analysis across all complaint history")
async def get_trends(db: Session = Depends(get_db)):
    """Analyzes historical complaint data and returns trend insights."""
    data = _get_cached_or_compute(db)
    return {
        "generated_at": data["generated_at"],
        "total_trends": len(data["trends"]),
        "trends": data["trends"],
    }


@router.get("/routes/risk", summary="Route risk prediction scores")
async def get_route_risks(db: Session = Depends(get_db)):
    """Predicts which routes are at risk of future issues."""
    data = _get_cached_or_compute(db)
    route_risks = data["route_risks"]
    critical = [r for r in route_risks if r["risk_level"] == "Critical"]
    high = [r for r in route_risks if r["risk_level"] == "High"]
    return {
        "generated_at": data["generated_at"],
        "total_routes": len(route_risks),
        "critical_count": len(critical),
        "high_count": len(high),
        "routes": route_risks,
    }


@router.get("/drivers/risk", summary="Driver risk assessment")
async def get_driver_risks(db: Session = Depends(get_db)):
    """Identifies drivers requiring intervention based on complaint patterns."""
    data = _get_cached_or_compute(db)
    return {
        "generated_at": data["generated_at"],
        "total_drivers": len(data["driver_risks"]),
        "drivers": data["driver_risks"],
    }


@router.get("/buses/risk", summary="Bus health and maintenance risk")
async def get_bus_risks(db: Session = Depends(get_db)):
    """Predicts maintenance risk for each bus based on complaint patterns."""
    data = _get_cached_or_compute(db)
    return {
        "generated_at": data["generated_at"],
        "total_buses": len(data["bus_risks"]),
        "buses": data["bus_risks"],
    }


@router.get("/forecast", summary="Complaint volume forecast")
async def get_forecast(db: Session = Depends(get_db)):
    """Forecasts daily, weekly, and monthly complaint volumes using linear extrapolation."""
    data = _get_cached_or_compute(db)
    return {
        "generated_at": data["generated_at"],
        **data["forecast"],
    }


@router.get("/recommendations", summary="Preventive recommendations")
async def get_recommendations(db: Session = Depends(get_db)):
    """Generates actionable preventive recommendations based on risk assessments."""
    data = _get_cached_or_compute(db)
    return {
        "generated_at": data["generated_at"],
        "total": len(data["recommendations"]),
        "recommendations": data["recommendations"],
    }


@router.get("/alerts", summary="Smart threshold-based alerts")
async def get_smart_alerts(db: Session = Depends(get_db)):
    """Returns alerts triggered by risk thresholds and complaint spikes."""
    data = _get_cached_or_compute(db)
    unread = [a for a in data["alerts"] if a.get("status") != "read"]
    return {
        "generated_at": data["generated_at"],
        "total": len(data["alerts"]),
        "unread": len(unread),
        "alerts": data["alerts"],
    }


@router.get("/predictive", summary="All-in-one predictive analytics response")
async def get_all_predictive(
    refresh: bool = Query(False, description="Force cache refresh"),
    db: Session = Depends(get_db),
):
    """
    Returns all Phase 5 predictive analytics in a single call.
    Used by the Predictive Dashboard for efficient data loading.
    Pass ?refresh=true to bypass 5-minute cache.
    """
    global _cache
    if refresh:
        _cache = {}
    data = _get_cached_or_compute(db)
    return data
