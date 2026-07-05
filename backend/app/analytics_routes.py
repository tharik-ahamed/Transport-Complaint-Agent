"""
Phase 3 Analytics Routes
========================
Provides aggregated statistics for the admin dashboard.

All endpoints require admin JWT.

GET /api/v1/analytics/sentiment   — Sentiment distribution counts
GET /api/v1/analytics/categories  — Category distribution counts
GET /api/v1/analytics/severity    — Severity distribution counts
GET /api/v1/analytics/priorities  — Priority distribution counts
GET /api/v1/analytics/summary     — All-in-one dashboard summary
"""
import json
import logging
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Complaint
from app.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"],
    dependencies=[Depends(verify_token)],   # All analytics require admin JWT
)


# ── Helpers ────────────────────────────────────────────────────────────

def _parse_json_field(value: str | None, fallback) -> list | dict:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


# ══════════════════════════════════════════════════════════════════════
# Analytics endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("/sentiment", summary="Sentiment distribution across all complaints")
async def get_sentiment_analytics(db: Session = Depends(get_db)):
    """Returns counts per sentiment level: Positive, Neutral, Negative, Highly Negative."""
    complaints = db.query(Complaint).all()
    buckets = {
        "Positive": 0,
        "Neutral": 0,
        "Negative": 0,
        "Highly Negative": 0,
        "Unknown": 0,
    }
    for c in complaints:
        s = c.sentiment or "Unknown"
        if s in buckets:
            buckets[s] += 1
        else:
            buckets["Unknown"] += 1

    total = len(complaints)
    return {
        "total": total,
        "distribution": {
            k: {"count": v, "percentage": round(v / total * 100, 1) if total else 0}
            for k, v in buckets.items()
        },
    }


@router.get("/categories", summary="Category distribution across all complaints")
async def get_category_analytics(db: Session = Depends(get_db)):
    """Returns counts per AI-classified category."""
    complaints = db.query(Complaint).all()
    counter: Counter = Counter()
    for c in complaints:
        cats = _parse_json_field(c.ai_categories, [c.category] if c.category else ["Other"])
        for cat in cats:
            if cat:
                counter[cat] += 1

    total_tagged = sum(counter.values())
    return {
        "total_complaints": len(complaints),
        "total_category_tags": total_tagged,
        "distribution": {
            k: {"count": v, "percentage": round(v / total_tagged * 100, 1) if total_tagged else 0}
            for k, v in counter.most_common()
        },
    }


@router.get("/severity", summary="Severity distribution across all complaints")
async def get_severity_analytics(db: Session = Depends(get_db)):
    """Returns counts per severity level: Low, Medium, High, Critical."""
    complaints = db.query(Complaint).all()
    buckets = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    for c in complaints:
        s = c.severity or "Unknown"
        if s in buckets:
            buckets[s] += 1
        else:
            buckets["Unknown"] += 1

    total = len(complaints)
    return {
        "total": total,
        "distribution": {
            k: {"count": v, "percentage": round(v / total * 100, 1) if total else 0}
            for k, v in buckets.items()
        },
    }


@router.get("/priorities", summary="Priority distribution across all complaints")
async def get_priority_analytics(db: Session = Depends(get_db)):
    """Returns counts per priority level: P1, P2, P3, P4."""
    complaints = db.query(Complaint).all()
    buckets = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "Unknown": 0}
    for c in complaints:
        p = c.priority_level or "Unknown"
        if p in buckets:
            buckets[p] += 1
        else:
            buckets["Unknown"] += 1

    total = len(complaints)
    return {
        "total": total,
        "distribution": {
            k: {
                "count": v,
                "percentage": round(v / total * 100, 1) if total else 0,
                "label": {
                    "P1": "Immediate Action",
                    "P2": "High Priority",
                    "P3": "Normal",
                    "P4": "Low Priority",
                }.get(k, k),
            }
            for k, v in buckets.items()
        },
    }


@router.get("/summary", summary="Dashboard summary — all analytics in one call")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns combined analytics for the admin dashboard in a single call:
    - Headline metrics (total, critical, high-priority, duplicates)
    - Sentiment distribution
    - Category distribution
    - Severity distribution
    - Priority distribution
    - Trend data (complaints per date)
    """
    complaints = db.query(Complaint).order_by(Complaint.created_at.asc()).all()
    total = len(complaints)

    sentiment_dist: Counter = Counter()
    category_dist: Counter = Counter()
    severity_dist: Counter = Counter()
    priority_dist: Counter = Counter()
    trend: dict[str, int] = {}
    critical_count = 0
    high_priority_count = 0
    duplicate_incident_ids: set = set()

    for c in complaints:
        # Sentiment
        sentiment_dist[c.sentiment or "Unknown"] += 1

        # Categories
        cats = _parse_json_field(c.ai_categories, [c.category] if c.category else ["Other"])
        for cat in cats:
            if cat:
                category_dist[cat] += 1

        # Severity
        sev = c.severity or "Unknown"
        severity_dist[sev] += 1
        if sev == "Critical":
            critical_count += 1

        # Priority
        pri = c.priority_level or "Unknown"
        priority_dist[pri] += 1
        if pri in ("P1", "P2"):
            high_priority_count += 1

        # Duplicates
        if c.duplicate_detected and c.incident_id:
            duplicate_incident_ids.add(c.incident_id)

        # Trend (group by submission date)
        date_key = c.created_at.date().isoformat() if c.created_at else "unknown"
        trend[date_key] = trend.get(date_key, 0) + 1

    # Trend as sorted list
    trend_list = [{"date": k, "count": v} for k, v in sorted(trend.items())]

    return {
        "metrics": {
            "total_complaints": total,
            "critical_complaints": critical_count,
            "high_priority_complaints": high_priority_count,
            "duplicate_groups": len(duplicate_incident_ids),
        },
        "sentiment": dict(sentiment_dist),
        "categories": dict(category_dist.most_common(10)),
        "severity": dict(severity_dist),
        "priorities": dict(priority_dist),
        "trend": trend_list,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 4 Performance Analytics
# ══════════════════════════════════════════════════════════════════════

@router.get("/performance", summary="Phase 4 resolution and department performance metrics")
async def get_performance_analytics(db: Session = Depends(get_db)):
    """
    Returns:
    - Average resolution time (seconds + human-readable)
    - Department workload (complaints per dept)
    - SLA compliance percentage
    - Top 10 most problematic routes
    - Top 10 most complained-about buses
    - Escalation rate
    """
    from datetime import datetime as dt

    complaints = db.query(Complaint).all()
    total = len(complaints)

    # ── Resolution time ───────────────────────────────────────────────
    resolved_times = []
    for c in complaints:
        if c.resolved_at and c.created_at:
            delta = (c.resolved_at - c.created_at).total_seconds()
            if delta > 0:
                resolved_times.append(delta)

    avg_resolution_seconds = sum(resolved_times) / len(resolved_times) if resolved_times else 0
    avg_h = int(avg_resolution_seconds // 3600)
    avg_m = int((avg_resolution_seconds % 3600) // 60)
    avg_resolution_str = f"{avg_h}h {avg_m}m" if avg_h else f"{avg_m}m"

    # ── Department workload ───────────────────────────────────────────
    dept_workload: Counter = Counter()
    dept_resolved: Counter = Counter()
    for c in complaints:
        dept = c.assigned_department or "Unassigned"
        dept_workload[dept] += 1
        if c.complaint_status in ("Resolved", "Closed"):
            dept_resolved[dept] += 1

    # ── SLA compliance ────────────────────────────────────────────────
    sla_total = sla_ok = 0
    sla_breached_count = sla_warning_count = 0
    escalated_count = 0
    for c in complaints:
        if c.sla_status:
            sla_total += 1
            if c.sla_status == "Within SLA":
                sla_ok += 1
            elif c.sla_status == "SLA Breached":
                sla_breached_count += 1
            elif c.sla_status == "SLA Warning":
                sla_warning_count += 1
        if c.escalation_status:
            escalated_count += 1

    sla_compliance_pct = round((sla_ok / sla_total) * 100, 1) if sla_total else 0

    # ── Top problematic routes ────────────────────────────────────────
    route_counter: Counter = Counter()
    for c in complaints:
        if c.route_number:
            route_counter[c.route_number] += 1

    # ── Top complained buses ──────────────────────────────────────────
    bus_counter: Counter = Counter()
    for c in complaints:
        if c.bus_number:
            bus_counter[c.bus_number] += 1

    return {
        "total_complaints": total,
        "resolved_count": len(resolved_times),
        "resolution_time": {
            "average_seconds": round(avg_resolution_seconds, 0),
            "average_human": avg_resolution_str,
            "samples": len(resolved_times),
        },
        "sla_compliance": {
            "percentage": sla_compliance_pct,
            "within_sla": sla_ok,
            "sla_warning": sla_warning_count,
            "sla_breached": sla_breached_count,
            "total_tracked": sla_total,
        },
        "escalation": {
            "escalated_count": escalated_count,
            "escalation_rate_pct": round((escalated_count / total) * 100, 1) if total else 0,
        },
        "department_workload": dict(dept_workload.most_common()),
        "department_resolved": dict(dept_resolved.most_common()),
        "top_routes": dict(route_counter.most_common(10)),
        "top_buses": dict(bus_counter.most_common(10)),
    }
