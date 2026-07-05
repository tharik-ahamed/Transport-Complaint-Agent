from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    # ── Phase 1 fields (unchanged) ──────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id = Column(String(20), unique=True, index=True, nullable=False)
    passenger_name = Column(String(100), nullable=False)
    mobile_number = Column(String(15), nullable=False)
    email = Column(String(100), nullable=False)
    bus_number = Column(String(20), nullable=False)
    route_number = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    complaint_description = Column(Text, nullable=False)
    incident_location = Column(String(200), nullable=False)
    incident_datetime = Column(DateTime, nullable=False)
    voice_file_path = Column(String(500), nullable=True)
    image_file_path = Column(String(500), nullable=True)
    status = Column(String(20), default="Pending", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Phase 2 AI analysis fields ───────────────────────────────────
    detected_language = Column(String(30), nullable=True)
    translated_text = Column(Text, nullable=True)
    extracted_bus_number = Column(String(50), nullable=True)
    extracted_route_number = Column(String(50), nullable=True)
    extracted_location = Column(String(200), nullable=True)
    extracted_entities = Column(Text, nullable=True)   # JSON string
    extracted_keywords = Column(Text, nullable=True)   # JSON string
    ai_summary = Column(Text, nullable=True)

    # ── Phase 3 Decision Making fields ────────────────────────────────
    sentiment = Column(String(30), nullable=True)
    sentiment_score = Column(Text, nullable=True)      # Stores score/confidence
    ai_categories = Column(Text, nullable=True)        # JSON string list
    severity = Column(String(30), nullable=True)
    severity_score = Column(Text, nullable=True)       # Numeric level
    priority_level = Column(String(10), nullable=True)  # P1, P2, P3, P4
    incident_id = Column(String(50), nullable=True)
    duplicate_count = Column(Integer, default=1, nullable=False)
    duplicate_detected = Column(Integer, default=0, nullable=False) # Store boolean as 0/1 in SQLite
    recommended_action = Column(Text, nullable=True)

    # ── Phase 4 Routing & Workflow fields ─────────────────────────────
    assigned_department = Column(String(100), nullable=True)
    assigned_team = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    escalation_status = Column(Integer, default=0, nullable=False)   # 0/1 boolean
    escalation_level = Column(String(100), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    sla_status = Column(String(30), nullable=True)                    # Within SLA / SLA Warning / SLA Breached
    complaint_status = Column(String(50), default="Submitted", nullable=False)
    updated_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_time = Column(String(50), nullable=True)              # e.g. "2h 30m"
    notifications = Column(Text, nullable=True)                      # JSON array
