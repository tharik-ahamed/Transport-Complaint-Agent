import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ComplaintResponse,
    ComplaintListResponse,
    SubmissionSuccess,
    VALID_CATEGORIES,
)
from app import crud
from app.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/complaints", tags=["Complaints"])


# ══════════════════════════════════════════════════════════════════════
# Warning 1 fix: server-side MIME type + file size validation
# ══════════════════════════════════════════════════════════════════════

_ALLOWED_IMAGE_INFO = "JPEG, PNG, or WEBP"
_ALLOWED_VOICE_INFO = "MP3 or WAV"
_IMAGE_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
_VOICE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_upload(upload_file: UploadFile, file_type: str) -> None:
    """
    Validate an uploaded file by inspecting its magic bytes (file header)
    and enforcing a maximum file size.

    file_type: 'image' | 'voice'
    Raises HTTPException 400 on invalid type or oversized file.
    """
    if not upload_file or not upload_file.filename:
        return  # Optional file — nothing to validate

    # ── 1. Read header for MIME detection ─────────────────────────────
    header = upload_file.file.read(12)
    upload_file.file.seek(0)  # Reset so the rest of the file is readable

    if file_type == "image":
        is_jpeg = header[:3] == b"\xff\xd8\xff"
        is_png  = header[:4] == b"\x89PNG"
        is_webp = (header[:4] == b"RIFF") and (header[8:12] == b"WEBP")
        if not (is_jpeg or is_png or is_webp):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format. Allowed types: {_ALLOWED_IMAGE_INFO}",
            )
        max_bytes = _IMAGE_MAX_BYTES
        label = "image"

    elif file_type == "voice":
        # MP3: starts with ID3 tag OR sync bytes 0xFF 0xEx / 0xFF 0xFx
        is_mp3 = (
            header[:3] == b"ID3"
            or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0)
        )
        is_wav = (header[:4] == b"RIFF") and (header[8:12] == b"WAVE")
        if not (is_mp3 or is_wav):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Allowed types: {_ALLOWED_VOICE_INFO}",
            )
        max_bytes = _VOICE_MAX_BYTES
        label = "audio"

    else:
        return  # Unknown type — skip silently

    # ── 2. Check file size ─────────────────────────────────────────────
    upload_file.file.seek(0, 2)    # Seek to end
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)       # Reset to beginning

    if file_size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. Maximum {label} file size is {limit_mb} MB "
                f"(uploaded: {file_size / (1024 * 1024):.1f} MB)"
            ),
        )


# ══════════════════════════════════════════════════════════════════════
# Phase 1 routes
# ══════════════════════════════════════════════════════════════════════

@router.post("/create", response_model=SubmissionSuccess, status_code=201)
async def create_complaint(
    passenger_name: str = Form(...),
    mobile_number: str = Form(...),
    email: str = Form(...),
    bus_number: str = Form(...),
    route_number: str = Form(...),
    category: str = Form(...),
    complaint_description: str = Form(...),
    incident_location: str = Form(...),
    incident_datetime: str = Form(...),
    voice_file: Optional[UploadFile] = File(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Submit a new complaint — public endpoint (no auth required)."""
    import re
    from app.schemas import ComplaintCreate

    errors = []

    passenger_name = passenger_name.strip()
    if not passenger_name or len(passenger_name) < 2:
        errors.append("Passenger name must be at least 2 characters")

    if not re.match(r"^\+?[0-9]{7,15}$", mobile_number.strip()):
        errors.append("Invalid mobile number format")

    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_pattern, email.strip()):
        errors.append("Invalid email address")

    if not bus_number.strip():
        errors.append("Bus number cannot be empty")

    if not route_number.strip():
        errors.append("Route number cannot be empty")

    if category not in VALID_CATEGORIES:
        errors.append("Invalid category")

    description = complaint_description.strip()
    if not description or len(description) < 10:
        errors.append("Complaint description must be at least 10 characters")

    if not incident_location.strip():
        errors.append("Incident location cannot be empty")

    try:
        incident_dt = datetime.fromisoformat(incident_datetime)
    except ValueError:
        errors.append("Invalid incident date/time format")
        incident_dt = None

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    # ── Warning 1 fix: validate uploads before saving ─────────────────
    real_voice = voice_file if voice_file and voice_file.filename else None
    real_image = image_file if image_file and image_file.filename else None

    if real_voice:
        _validate_upload(real_voice, "voice")
    if real_image:
        _validate_upload(real_image, "image")

    complaint_data = ComplaintCreate(
        passenger_name=passenger_name,
        mobile_number=mobile_number.strip(),
        email=email.strip(),
        bus_number=bus_number.strip(),
        route_number=route_number.strip(),
        category=category,
        complaint_description=description,
        incident_location=incident_location.strip(),
        incident_datetime=incident_dt,
    )

    db_complaint = crud.create_complaint(
        db=db,
        complaint_data=complaint_data,
        voice_file=real_voice,
        image_file=real_image,
    )

    # ── Phase 2 + 3: Auto-trigger AI analysis ─────────────────────────
    ai_result_summary = None
    try:
        from app.ai.agent import complaint_agent
        analysis = complaint_agent.analyze(description)
        crud.update_complaint_analysis(db, db_complaint.complaint_id, analysis)

        # Update complaint_status to AI Analysis Completed
        db_complaint = crud.get_complaint_by_id(db, db_complaint.complaint_id)
        db_complaint.complaint_status = "AI Analysis Completed"
        db.commit()

        # ── Warning 5 fix: parse keywords JSON string before returning ─
        raw_keywords = analysis.get("extracted_keywords", "[]")
        try:
            parsed_keywords = json.loads(raw_keywords) if isinstance(raw_keywords, str) else raw_keywords
        except Exception:
            parsed_keywords = []

        ai_result_summary = {
            "language": analysis.get("detected_language"),
            "summary": analysis.get("ai_summary"),
            "keywords": parsed_keywords,
        }
        logger.info(f"AI analysis complete for {db_complaint.complaint_id}")
    except Exception as e:
        logger.warning(f"AI analysis skipped for {db_complaint.complaint_id}: {e}")

    # ── Phase 4: Routing, SLA, Escalation, Notifications ─────────────
    try:
        from app.workflow import apply_phase4_workflow
        db_complaint = crud.get_complaint_by_id(db, db_complaint.complaint_id)
        apply_phase4_workflow(db, db_complaint)
        logger.info(f"Phase 4 workflow complete for {db_complaint.complaint_id}")
    except Exception as e:
        logger.warning(f"Phase 4 workflow skipped for {db_complaint.complaint_id}: {e}")

    return SubmissionSuccess(
        complaint_id=db_complaint.complaint_id,
        message="Your complaint has been registered successfully.",
        ai_analysis=ai_result_summary,
    )


@router.get(
    "",
    response_model=ComplaintListResponse,
    dependencies=[Depends(verify_token)],  # Warning 2 fix: JWT required
    summary="List all complaints — requires admin JWT",
)
async def get_all_complaints(db: Session = Depends(get_db)):
    """Return all complaints ordered by submission date (newest first). Requires Bearer JWT."""
    complaints = crud.get_all_complaints(db)
    return ComplaintListResponse(total=len(complaints), complaints=complaints)


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Get a single complaint — public",
)
async def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    """Return one complaint by ID. Public — passengers can track their own complaint."""
    complaint = crud.get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint
