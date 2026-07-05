from pydantic import BaseModel, EmailStr, validator, field_validator
from typing import Optional, Any
from datetime import datetime
import re
import json


VALID_CATEGORIES = [
    "Bus Delay",
    "Driver Misconduct",
    "Conductor Misconduct",
    "Stop Skipping",
    "Overcrowding",
    "Maintenance Issue",
    "Ticket Issue",
    "Safety Issue",
    "Cleanliness Issue",
    "Other",
]


# ── Phase 1 schemas (unchanged) ──────────────────────────────────────

class ComplaintCreate(BaseModel):
    passenger_name: str
    mobile_number: str
    email: EmailStr
    bus_number: str
    route_number: str
    category: str
    complaint_description: str
    incident_location: str
    incident_datetime: datetime

    @validator("passenger_name")
    def name_must_not_be_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Passenger name cannot be empty")
        if len(v) < 2:
            raise ValueError("Passenger name must be at least 2 characters")
        return v

    @validator("mobile_number")
    def validate_mobile(cls, v):
        v = v.strip()
        if not re.match(r"^\+?[0-9]{7,15}$", v):
            raise ValueError("Invalid mobile number format")
        return v

    @validator("bus_number")
    def bus_number_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Bus number cannot be empty")
        return v

    @validator("route_number")
    def route_number_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Route number cannot be empty")
        return v

    @validator("category")
    def category_must_be_valid(cls, v):
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(VALID_CATEGORIES)}")
        return v

    @validator("complaint_description")
    def description_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Complaint description cannot be empty")
        if len(v) < 10:
            raise ValueError("Complaint description must be at least 10 characters")
        return v

    @validator("incident_location")
    def location_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Incident location cannot be empty")
        return v


class ComplaintResponse(BaseModel):
    id: int
    complaint_id: str
    passenger_name: str
    mobile_number: str
    email: str
    bus_number: str
    route_number: str
    category: str
    complaint_description: str
    incident_location: str
    incident_datetime: datetime
    voice_file_path: Optional[str]
    image_file_path: Optional[str]
    status: str
    created_at: datetime
    # Phase 2 AI fields — stored as JSON strings in DB, returned as parsed objects
    detected_language: Optional[str] = None
    translated_text: Optional[str] = None
    extracted_bus_number: Optional[str] = None
    extracted_route_number: Optional[str] = None
    extracted_location: Optional[str] = None
    extracted_entities: Optional[Any] = None   # Warning 5 fix: Any (parsed from JSON)
    extracted_keywords: Optional[Any] = None   # Warning 5 fix: Any (parsed from JSON)
    ai_summary: Optional[str] = None

    # Phase 3 Decision Making fields
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    ai_categories: Optional[Any] = None        # parsed from JSON array
    severity: Optional[str] = None
    severity_score: Optional[float] = None
    priority_level: Optional[str] = None
    incident_id: Optional[str] = None
    duplicate_count: Optional[int] = 1
    duplicate_detected: Optional[bool] = False
    recommended_action: Optional[str] = None

    # Phase 4 Routing & Workflow fields
    assigned_department: Optional[str] = None
    assigned_team: Optional[str] = None
    assigned_at: Optional[datetime] = None
    escalation_status: Optional[bool] = False
    escalation_level: Optional[str] = None
    escalated_at: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    sla_status: Optional[str] = None
    complaint_status: Optional[str] = "Submitted"
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_time: Optional[str] = None
    notifications: Optional[Any] = None        # parsed from JSON array

    # ── JSON string deserializers ──────────────────────────────────────
    @field_validator("extracted_keywords", "extracted_entities", "ai_categories", "notifications", mode="before")
    @classmethod
    def parse_json_string_fields(cls, v: Any) -> Any:
        """Convert JSON strings stored in SQLite to Python objects."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return v
        return v

    @field_validator("duplicate_detected", "escalation_status", mode="before")
    @classmethod
    def coerce_boolean(cls, v: Any) -> bool:
        if isinstance(v, int):
            return bool(v)
        return v

    class Config:
        from_attributes = True


class ComplaintIntelligenceResponse(BaseModel):
    sentiment: Optional[str] = None
    categories: list[str] = []
    severity: Optional[str] = None
    priority: Optional[str] = None
    duplicates: dict = {}
    recommendation: Optional[str] = None



class ComplaintListResponse(BaseModel):
    total: int
    complaints: list[ComplaintResponse]


class SubmissionSuccess(BaseModel):
    complaint_id: str
    message: str
    ai_analysis: Optional[dict] = None


# ── Phase 2 AI schemas ───────────────────────────────────────────────

class AIAnalysisResult(BaseModel):
    complaint_id: str
    detected_language: Optional[str] = None
    translated_text: Optional[str] = None
    extracted_bus_number: Optional[str] = None
    extracted_route_number: Optional[str] = None
    extracted_location: Optional[str] = None
    extracted_entities: Optional[Any] = None   # parsed JSON
    extracted_keywords: Optional[Any] = None   # parsed JSON
    ai_summary: Optional[str] = None
    ai_mode: str = "fallback"  # "gemini" or "fallback"

    @classmethod
    def from_complaint(cls, complaint, ai_mode: str = "fallback") -> "AIAnalysisResult":
        entities = None
        keywords = None
        if complaint.extracted_entities:
            try:
                entities = json.loads(complaint.extracted_entities)
            except Exception:
                entities = complaint.extracted_entities
        if complaint.extracted_keywords:
            try:
                keywords = json.loads(complaint.extracted_keywords)
            except Exception:
                keywords = complaint.extracted_keywords
        return cls(
            complaint_id=complaint.complaint_id,
            detected_language=complaint.detected_language,
            translated_text=complaint.translated_text,
            extracted_bus_number=complaint.extracted_bus_number,
            extracted_route_number=complaint.extracted_route_number,
            extracted_location=complaint.extracted_location,
            extracted_entities=entities,
            extracted_keywords=keywords,
            ai_summary=complaint.ai_summary,
            ai_mode=ai_mode,
        )


class AnalyzeRequest(BaseModel):
    complaint_id: str


# ── Phase 4 Request / Response Schemas ───────────────────────────────

class AssignRequest(BaseModel):
    department: str
    team: str


class EscalateRequest(BaseModel):
    escalation_level: str


class ResolveRequest(BaseModel):
    resolution_notes: str


class StatusUpdateRequest(BaseModel):
    complaint_status: str   # Submitted | AI Analysis Completed | Assigned | In Progress | Resolved | Closed


class DeptDashboardResponse(BaseModel):
    department: str
    total: int
    open: int
    escalated: int
    sla_breached: int
    resolved: int


class AssignedComplaintSummary(BaseModel):
    complaint_id: str
    passenger_name: str
    category: str
    severity: Optional[str] = None
    priority_level: Optional[str] = None
    assigned_department: Optional[str] = None
    assigned_team: Optional[str] = None
    sla_status: Optional[str] = None
    complaint_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

