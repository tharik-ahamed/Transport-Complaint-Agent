"""
Phase 4 Workflow Engine
=======================
Applies routing, SLA, escalation, and notification logic to a complaint
after the AI analysis pipeline (Phase 2 + 3) has completed.

Entry point:
    apply_phase4_workflow(db, complaint) -> None
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# FEATURE 1: Routing Agent
# ══════════════════════════════════════════════════════════════════════

# Priority-ordered mapping: first match wins
ROUTING_PRIORITY = [
    ("Safety Issue",          "Regional Transport Officer",       "Safety Compliance Team"),
    ("Driver Misconduct",     "Human Resources Department",       "Driver Management Team"),
    ("Conductor Misconduct",  "Human Resources Department",       "Conductor Management Team"),
    ("Maintenance Issue",     "Vehicle Maintenance Department",   "Fleet Maintenance Team"),
    ("Ticket Issue",          "Ticketing Department",             "Fare Audit Team"),
    ("Cleanliness Issue",     "Depot Management Team",            "Cleanliness Standards Team"),
    ("Stop Skipping",         "Route Monitoring Department",      "Route Monitoring Team"),
    ("Route Deviation",       "Operations Department",            "Route Monitoring Team"),
    ("Overcrowding",          "Operations Department",            "Fleet Allocation Team"),
    ("Bus Delay",             "Operations Department",            "Route Scheduling Team"),
]

DEFAULT_DEPT  = "General Administration"
DEFAULT_TEAM  = "Customer Relations Team"


def route_complaint(categories: list[str]) -> tuple[str, str]:
    """
    Returns (assigned_department, assigned_team) based on AI categories.
    Priority order is defined in ROUTING_PRIORITY above.
    """
    for cat, dept, team in ROUTING_PRIORITY:
        if cat in categories:
            return dept, team
    return DEFAULT_DEPT, DEFAULT_TEAM


# ══════════════════════════════════════════════════════════════════════
# FEATURE 3: SLA Monitoring Agent
# ══════════════════════════════════════════════════════════════════════

SLA_HOURS: dict[str, int] = {
    "Critical": 4,
    "High":     24,
    "Medium":   72,
    "Low":      168,   # 7 days
}
SLA_WARNING_PCT = 0.25  # warn when less than 25% of window remains


def compute_sla(severity: Optional[str], created_at: datetime) -> tuple[datetime, str]:
    """Returns (sla_deadline, sla_status)."""
    hours = SLA_HOURS.get(severity or "Medium", 72)
    deadline = created_at + timedelta(hours=hours)
    status = _sla_status(deadline, hours, created_at)
    return deadline, status


def _sla_status(deadline: datetime, total_hours: int, created_at: datetime) -> str:
    now = datetime.now()
    if now > deadline:
        return "SLA Breached"
    warning_cutoff = deadline - timedelta(hours=total_hours * SLA_WARNING_PCT)
    if now >= warning_cutoff:
        return "SLA Warning"
    return "Within SLA"


def refresh_sla_status(complaint) -> str:
    """Recompute SLA status for an existing complaint (call periodically)."""
    if not complaint.sla_deadline or not complaint.severity:
        return "Within SLA"
    hours = SLA_HOURS.get(complaint.severity, 72)
    created = complaint.created_at or datetime.now()
    return _sla_status(complaint.sla_deadline, hours, created)


# ══════════════════════════════════════════════════════════════════════
# FEATURE 2: Escalation Agent
# ══════════════════════════════════════════════════════════════════════

REPEAT_BUS_THRESHOLD   = 5   # complaints per bus number in 30 days
REPEAT_ROUTE_THRESHOLD = 20  # total complaints on same route


def check_escalation(db: Session, complaint) -> tuple[bool, Optional[str]]:
    """
    Evaluates escalation rules.
    Returns (should_escalate, escalation_level).
    """
    from app.models import Complaint

    # Rule 1: Critical severity → immediate
    if complaint.severity == "Critical":
        return True, "Regional Operations Manager"

    # Rule 2: Safety Issue
    categories = _parse_json(complaint.ai_categories, [complaint.category])
    if "Safety Issue" in categories:
        return True, "Regional Transport Officer"

    # Rule 3: >5 complaints against same bus_number in 30 days
    cutoff_30d = datetime.now() - timedelta(days=30)
    bus_count = (
        db.query(Complaint)
        .filter(
            Complaint.id != complaint.id,
            Complaint.bus_number == complaint.bus_number,
            Complaint.created_at >= cutoff_30d,
        )
        .count()
    )
    if bus_count >= REPEAT_BUS_THRESHOLD:
        return True, "HR Manager"

    # Rule 4: >20 complaints on same route
    route_count = (
        db.query(Complaint)
        .filter(
            Complaint.id != complaint.id,
            Complaint.route_number == complaint.route_number,
        )
        .count()
    )
    if route_count >= REPEAT_ROUTE_THRESHOLD:
        return True, "Regional Operations Manager"

    return False, None


# ══════════════════════════════════════════════════════════════════════
# FEATURE 5: Notification Generator
# ══════════════════════════════════════════════════════════════════════

def generate_notifications(complaint, escalated: bool, sla_status: str) -> list[dict]:
    """Build the initial notification set for a new complaint."""
    now = datetime.now().isoformat()
    cid = complaint.complaint_id
    notifications: list[dict] = [
        # Passenger notifications
        {
            "type": "passenger_received",
            "audience": "passenger",
            "message": f"Your complaint {cid} has been received and is being processed.",
            "created_at": now,
            "status": "unread",
        },
        {
            "type": "passenger_assigned",
            "audience": "passenger",
            "message": (
                f"Your complaint {cid} has been assigned to "
                f"{complaint.assigned_department or 'our team'} for review."
            ),
            "created_at": now,
            "status": "unread",
        },
        # Department notification
        {
            "type": "dept_new",
            "audience": "department",
            "message": (
                f"New complaint {cid} assigned to {complaint.assigned_team or 'your team'}. "
                f"Category: {complaint.category}. Severity: {complaint.severity or 'Unknown'}."
            ),
            "created_at": now,
            "status": "unread",
        },
    ]

    if escalated:
        notifications.append({
            "type": "admin_critical",
            "audience": "admin",
            "message": (
                f"ESCALATION REQUIRED: Complaint {cid} has been escalated to "
                f"{complaint.escalation_level}. Severity: {complaint.severity}."
            ),
            "created_at": now,
            "status": "unread",
        })
        notifications.append({
            "type": "dept_escalation",
            "audience": "department",
            "message": f"Complaint {cid} has been escalated to {complaint.escalation_level}.",
            "created_at": now,
            "status": "unread",
        })

    if sla_status == "SLA Breached":
        notifications.append({
            "type": "admin_sla_breach",
            "audience": "admin",
            "message": f"SLA BREACHED: Complaint {cid} exceeded its resolution deadline.",
            "created_at": now,
            "status": "unread",
        })
    elif sla_status == "SLA Warning":
        notifications.append({
            "type": "dept_sla_warning",
            "audience": "department",
            "message": f"SLA WARNING: Complaint {cid} is nearing its resolution deadline.",
            "created_at": now,
            "status": "unread",
        })

    return notifications


# ══════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def apply_phase4_workflow(db: Session, complaint) -> None:
    """
    Run all Phase 4 agents for a complaint after AI analysis is complete.
    Mutates the complaint record in-place and commits.

    Order:
        1. Routing Agent  → assigned_department / assigned_team
        2. SLA Agent      → sla_deadline / sla_status
        3. Escalation     → escalation_status / escalation_level
        4. Status Update  → complaint_status = "Assigned"
        5. Notifications  → notifications JSON
    """
    now = datetime.now()

    # 1. Routing
    categories = _parse_json(complaint.ai_categories, [complaint.category])
    dept, team = route_complaint(categories)
    complaint.assigned_department = dept
    complaint.assigned_team = team
    complaint.assigned_at = now

    # 2. SLA
    created = complaint.created_at or now
    sla_deadline, sla_status = compute_sla(complaint.severity, created)
    complaint.sla_deadline = sla_deadline
    complaint.sla_status = sla_status

    # 3. Escalation
    escalated, escalation_level = check_escalation(db, complaint)
    if escalated:
        complaint.escalation_status = 1
        complaint.escalation_level = escalation_level
        complaint.escalated_at = now

    # 4. Status
    complaint.complaint_status = "Assigned"
    complaint.updated_at = now

    # 5. Notifications
    notifs = generate_notifications(complaint, escalated, sla_status)
    complaint.notifications = json.dumps(notifs, ensure_ascii=False)

    db.commit()
    logger.info(
        f"Phase 4 workflow complete for {complaint.complaint_id}: "
        f"dept={dept}, severity={complaint.severity}, sla={sla_status}, "
        f"escalated={escalated}"
    )


# ── Helper ─────────────────────────────────────────────────────────────

def _parse_json(value: Optional[str], fallback: list) -> list:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback
