"""
Phase 4 Routes
==============
All new complaint workflow and department management endpoints.

GET  /api/v1/complaints/assigned          — All assigned complaints (optional ?department=)
GET  /api/v1/complaints/escalated         — All escalated complaints
GET  /api/v1/complaints/sla               — SLA monitoring list (optional ?status=)
GET  /api/v1/departments/dashboard        — Department-level stats

POST /api/v1/complaints/{id}/assign       — Manually assign to department
POST /api/v1/complaints/{id}/escalate     — Manually escalate
POST /api/v1/complaints/{id}/resolve      — Resolve with notes
POST /api/v1/complaints/{id}/status       — Update workflow status

All endpoints require admin JWT.
"""
import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Complaint
from app import crud
from app.schemas import (
    ComplaintResponse,
    AssignRequest,
    EscalateRequest,
    ResolveRequest,
    StatusUpdateRequest,
    DeptDashboardResponse,
    AssignedComplaintSummary,
)
from app.auth import verify_token
from app.workflow import compute_sla, refresh_sla_status

logger = logging.getLogger(__name__)

# ── Router — NOTE: registered BEFORE routes.router in main.py ─────────
# Static paths (/assigned, /escalated, /sla) must be registered before
# the parameterized /{complaint_id} route to avoid conflicts.
workflow_router = APIRouter(
    prefix="/api/v1/complaints",
    tags=["Phase 4 Workflow"],
    dependencies=[Depends(verify_token)],
)

dept_router = APIRouter(
    prefix="/api/v1/departments",
    tags=["Phase 4 Departments"],
    dependencies=[Depends(verify_token)],
)


# ══════════════════════════════════════════════════════════════════════
# Static GET endpoints (must be before /{id})
# ══════════════════════════════════════════════════════════════════════

@workflow_router.get("/assigned", summary="List all assigned complaints")
async def get_assigned_complaints(
    department: Optional[str] = Query(None, description="Filter by department name"),
    db: Session = Depends(get_db),
):
    """Returns complaints that have been assigned to a department. Optional ?department= filter."""
    q = db.query(Complaint).filter(Complaint.assigned_department.isnot(None))
    if department:
        q = q.filter(Complaint.assigned_department.ilike(f"%{department}%"))
    complaints = q.order_by(Complaint.created_at.desc()).all()
    return {
        "total": len(complaints),
        "complaints": [_to_summary(c) for c in complaints],
    }


@workflow_router.get("/escalated", summary="List all escalated complaints")
async def get_escalated_complaints(db: Session = Depends(get_db)):
    """Returns all complaints where escalation_status = 1."""
    complaints = (
        db.query(Complaint)
        .filter(Complaint.escalation_status == 1)
        .order_by(Complaint.escalated_at.desc())
        .all()
    )
    return {
        "total": len(complaints),
        "complaints": [_to_summary(c) for c in complaints],
    }


@workflow_router.get("/sla", summary="List complaints with SLA info")
async def get_sla_complaints(
    status: Optional[str] = Query(None, description="Filter: breached | warning | within"),
    db: Session = Depends(get_db),
):
    """Returns complaints with computed SLA status. Refreshes sla_status from DB."""
    complaints = db.query(Complaint).order_by(Complaint.sla_deadline.asc()).all()

    # Refresh SLA statuses and filter
    result = []
    updated_any = False
    for c in complaints:
        if c.sla_deadline and c.severity:
            fresh = refresh_sla_status(c)
            if fresh != c.sla_status:
                c.sla_status = fresh
                c.updated_at = datetime.now()
                updated_any = True

        # Apply filter
        if status:
            if status.lower() == "breached" and c.sla_status != "SLA Breached":
                continue
            elif status.lower() == "warning" and c.sla_status != "SLA Warning":
                continue
            elif status.lower() == "within" and c.sla_status != "Within SLA":
                continue

        result.append({
            "complaint_id": c.complaint_id,
            "passenger_name": c.passenger_name,
            "severity": c.severity,
            "sla_deadline": c.sla_deadline.isoformat() if c.sla_deadline else None,
            "sla_status": c.sla_status,
            "complaint_status": c.complaint_status,
            "assigned_department": c.assigned_department,
        })

    if updated_any:
        db.commit()

    return {"total": len(result), "complaints": result}


# ══════════════════════════════════════════════════════════════════════
# Action POST endpoints  (/{id}/...)
# ══════════════════════════════════════════════════════════════════════

@workflow_router.post("/{complaint_id}/assign", summary="Assign complaint to department")
async def assign_complaint(
    complaint_id: str,
    body: AssignRequest,
    db: Session = Depends(get_db),
):
    """Manually assign or re-assign a complaint to a department and team."""
    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(404, f"Complaint '{complaint_id}' not found")

    now = datetime.now()
    complaint.assigned_department = body.department
    complaint.assigned_team = body.team
    complaint.assigned_at = now
    complaint.complaint_status = "Assigned"
    complaint.updated_at = now
    _add_notification(complaint, {
        "type": "dept_new",
        "audience": "department",
        "message": f"Complaint {complaint_id} reassigned to {body.team} ({body.department}).",
        "created_at": now.isoformat(),
        "status": "unread",
    })
    db.commit()
    return {"message": "Assigned successfully", "department": body.department, "team": body.team}


@workflow_router.post("/{complaint_id}/escalate", summary="Escalate a complaint")
async def escalate_complaint(
    complaint_id: str,
    body: EscalateRequest,
    db: Session = Depends(get_db),
):
    """Manually escalate a complaint to the specified escalation level."""
    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(404, f"Complaint '{complaint_id}' not found")

    now = datetime.now()
    complaint.escalation_status = 1
    complaint.escalation_level = body.escalation_level
    complaint.escalated_at = now
    complaint.updated_at = now
    _add_notification(complaint, {
        "type": "admin_critical",
        "audience": "admin",
        "message": f"Complaint {complaint_id} escalated to {body.escalation_level}.",
        "created_at": now.isoformat(),
        "status": "unread",
    })
    db.commit()
    return {"message": "Escalated successfully", "escalation_level": body.escalation_level}


@workflow_router.post("/{complaint_id}/resolve", summary="Resolve a complaint")
async def resolve_complaint(
    complaint_id: str,
    body: ResolveRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
):
    """Mark a complaint as resolved with resolution notes."""
    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(404, f"Complaint '{complaint_id}' not found")

    now = datetime.now()
    created = complaint.created_at or now
    delta = now - created
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    resolution_time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"

    complaint.resolution_notes = body.resolution_notes
    complaint.resolved_by = current_user.get("sub", "admin")
    complaint.resolved_at = now
    complaint.resolution_time = resolution_time_str
    complaint.complaint_status = "Resolved"
    complaint.updated_at = now
    _add_notification(complaint, {
        "type": "passenger_resolved",
        "audience": "passenger",
        "message": f"Your complaint {complaint_id} has been resolved. Resolution time: {resolution_time_str}.",
        "created_at": now.isoformat(),
        "status": "unread",
    })
    db.commit()
    return {
        "message": "Complaint resolved",
        "complaint_id": complaint_id,
        "resolved_by": complaint.resolved_by,
        "resolution_time": resolution_time_str,
    }


@workflow_router.post("/{complaint_id}/status", summary="Update complaint workflow status")
async def update_status(
    complaint_id: str,
    body: StatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update the workflow status of a complaint."""
    VALID_STATUSES = [
        "Submitted", "AI Analysis Completed", "Assigned",
        "In Progress", "Resolved", "Closed"
    ]
    if body.complaint_status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")

    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(404, f"Complaint '{complaint_id}' not found")

    complaint.complaint_status = body.complaint_status
    complaint.updated_at = datetime.now()
    if body.complaint_status == "Closed":
        complaint.resolved_at = complaint.resolved_at or datetime.now()
    db.commit()
    return {"message": "Status updated", "complaint_status": body.complaint_status}


# ══════════════════════════════════════════════════════════════════════
# Department Dashboard
# ══════════════════════════════════════════════════════════════════════

@dept_router.get("/dashboard", summary="Department-level complaint statistics")
async def get_department_dashboard(
    department: Optional[str] = Query(None, description="Filter to a specific department"),
    db: Session = Depends(get_db),
):
    """
    Returns per-department complaint breakdown:
    total, open, escalated, SLA breached, resolved.
    """
    complaints = db.query(Complaint).all()

    dept_map: dict[str, dict] = {}
    for c in complaints:
        dept = c.assigned_department or "Unassigned"
        if department and dept.lower() != department.lower():
            continue
        if dept not in dept_map:
            dept_map[dept] = {"total": 0, "open": 0, "escalated": 0, "sla_breached": 0, "resolved": 0}
        dept_map[dept]["total"] += 1
        if c.complaint_status in ("Submitted", "AI Analysis Completed", "Assigned", "In Progress"):
            dept_map[dept]["open"] += 1
        if c.escalation_status:
            dept_map[dept]["escalated"] += 1
        if c.sla_status == "SLA Breached":
            dept_map[dept]["sla_breached"] += 1
        if c.complaint_status in ("Resolved", "Closed"):
            dept_map[dept]["resolved"] += 1

    departments = [
        {"department": dept, **stats}
        for dept, stats in sorted(dept_map.items(), key=lambda x: -x[1]["total"])
    ]
    return {"total_departments": len(departments), "departments": departments}


# ── Helper functions ──────────────────────────────────────────────────

def _to_summary(c: Complaint) -> dict:
    return {
        "complaint_id": c.complaint_id,
        "passenger_name": c.passenger_name,
        "category": c.category,
        "severity": c.severity,
        "priority_level": c.priority_level,
        "assigned_department": c.assigned_department,
        "assigned_team": c.assigned_team,
        "sla_status": c.sla_status,
        "sla_deadline": c.sla_deadline.isoformat() if c.sla_deadline else None,
        "complaint_status": c.complaint_status,
        "escalation_status": bool(c.escalation_status),
        "escalation_level": c.escalation_level,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _add_notification(complaint: Complaint, notif: dict) -> None:
    """Append a notification to the complaint's JSON notification list."""
    existing = []
    if complaint.notifications:
        try:
            existing = json.loads(complaint.notifications)
        except Exception:
            existing = []
    existing.append(notif)
    complaint.notifications = json.dumps(existing, ensure_ascii=False)
