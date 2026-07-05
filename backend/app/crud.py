import os
import uuid
import shutil
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Complaint
from app.schemas import ComplaintCreate

UPLOAD_DIR = "uploads"
VOICE_DIR = os.path.join(UPLOAD_DIR, "voice")
IMAGE_DIR = os.path.join(UPLOAD_DIR, "images")

os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


def generate_complaint_id(db: Session) -> str:
    """
    Legacy helper — kept for backward compatibility.
    Warning 4 fix: complaint creation now uses DB auto-increment instead.
    """
    year = datetime.now().year
    count = db.query(Complaint).filter(
        Complaint.complaint_id.like(f"CMP-{year}-%")
    ).count()
    sequence = count + 1
    return f"CMP-{year}-{sequence:04d}"


def create_complaint(
    db: Session,
    complaint_data: ComplaintCreate,
    voice_file=None,
    image_file=None,
) -> Complaint:
    """
    Create a new complaint record.

    Warning 4 fix — concurrency-safe ID generation:
    A temporary UUID-based complaint_id is inserted first, then replaced
    with the deterministic CMP-YYYY-NNNN format derived from the DB's
    auto-incremented primary key.  Because the primary key is assigned
    atomically by SQLite's auto-increment, two concurrent requests can
    never receive the same sequence number, eliminating the COUNT-based
    race condition.
    """
    # Unique temporary ID — safe even under concurrent inserts
    temp_id = f"TMP-{uuid.uuid4().hex[:16].upper()}"

    voice_path = None
    if voice_file:
        ext = os.path.splitext(voice_file.filename)[1]
        filename = f"{temp_id}_voice{ext}"
        file_path = os.path.join(VOICE_DIR, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(voice_file.file, f)
        voice_path = file_path

    image_path = None
    if image_file:
        ext = os.path.splitext(image_file.filename)[1]
        filename = f"{temp_id}_image{ext}"
        file_path = os.path.join(IMAGE_DIR, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        image_path = file_path

    db_complaint = Complaint(
        complaint_id=temp_id,  # Temporary — replaced below after flush
        passenger_name=complaint_data.passenger_name,
        mobile_number=complaint_data.mobile_number,
        email=complaint_data.email,
        bus_number=complaint_data.bus_number,
        route_number=complaint_data.route_number,
        category=complaint_data.category,
        complaint_description=complaint_data.complaint_description,
        incident_location=complaint_data.incident_location,
        incident_datetime=complaint_data.incident_datetime,
        voice_file_path=voice_path,
        image_file_path=image_path,
        status="Pending",
        created_at=datetime.now(),
    )
    db.add(db_complaint)

    # flush() writes the row and populates the auto-incremented PK
    # without committing the transaction — no other connection can read
    # this row yet, so concurrent requests each get a distinct id.
    db.flush()

    # Derive a stable, sequential complaint_id from the guaranteed-unique PK
    year = datetime.now().year
    final_id = f"CMP-{year}-{db_complaint.id:04d}"
    db_complaint.complaint_id = final_id

    # Rename uploaded files from temp_id to final_id for clarity
    if db_complaint.voice_file_path and temp_id in db_complaint.voice_file_path:
        new_voice = db_complaint.voice_file_path.replace(temp_id, final_id)
        os.rename(db_complaint.voice_file_path, new_voice)
        db_complaint.voice_file_path = new_voice

    if db_complaint.image_file_path and temp_id in db_complaint.image_file_path:
        new_image = db_complaint.image_file_path.replace(temp_id, final_id)
        os.rename(db_complaint.image_file_path, new_image)
        db_complaint.image_file_path = new_image

    db.commit()
    db.refresh(db_complaint)
    return db_complaint


def get_all_complaints(db: Session) -> list[Complaint]:
    return db.query(Complaint).order_by(Complaint.created_at.desc()).all()


def get_complaint_by_id(db: Session, complaint_id: str) -> Complaint | None:
    return db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()


# ── Phase 2 & 3: AI analysis update ──────────────────────────────────

def update_complaint_analysis(db: Session, complaint_id: str, analysis: dict) -> Complaint | None:
    """
    Store AI analysis results (both Phase 2 and Phase 3) into an existing complaint record.
    Only updates AI/decision-making columns — all original passenger input fields remain unchanged.
    """
    complaint = get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None

    # Phase 2
    complaint.detected_language = analysis.get("detected_language")
    complaint.translated_text = analysis.get("translated_text")
    complaint.extracted_bus_number = analysis.get("extracted_bus_number")
    complaint.extracted_route_number = analysis.get("extracted_route_number")
    complaint.extracted_location = analysis.get("extracted_location")
    complaint.extracted_entities = analysis.get("extracted_entities")
    complaint.extracted_keywords = analysis.get("extracted_keywords")
    complaint.ai_summary = analysis.get("ai_summary")

    # Phase 3
    complaint.sentiment = analysis.get("sentiment")
    # Cast score/floats to string/float as defined in models
    complaint.sentiment_score = str(analysis.get("sentiment_score")) if analysis.get("sentiment_score") is not None else None
    complaint.ai_categories = analysis.get("ai_categories")
    complaint.severity = analysis.get("severity")
    complaint.severity_score = str(analysis.get("severity_score")) if analysis.get("severity_score") is not None else None
    complaint.priority_level = analysis.get("priority_level")
    complaint.recommended_action = analysis.get("recommended_action")

    db.commit()
    db.refresh(complaint)
    
    # Process duplicates after AI classification has finished
    process_duplicates_and_incident(db, complaint)
    
    return complaint


def process_duplicates_and_incident(db: Session, complaint: Complaint) -> None:
    """
    Checks the database for recent duplicate complaints about the same incident
    (same bus_number or route_number on the same calendar day with same category).
    If found, groups them under a shared incident_id like INC-XXXX.
    """
    bus_num = complaint.bus_number.strip()
    route_num = complaint.route_number.strip()
    
    from sqlalchemy import or_, and_, func

    # Look for duplicate candidates:
    # 1. Different complaint record
    # 2. Same bus number or same route number (non-empty)
    # 3. Incident datetime within 24 hours
    # 4. Same category
    candidates = db.query(Complaint).filter(
        Complaint.id != complaint.id,
        or_(
            and_(Complaint.bus_number == bus_num, bus_num != ""),
            and_(Complaint.route_number == route_num, route_num != "")
        ),
        func.abs(func.julianday(Complaint.incident_datetime) - func.julianday(complaint.incident_datetime)) <= 1.0,
        Complaint.category == complaint.category
    ).order_by(Complaint.id.asc()).all()

    if candidates:
        # Group them under the oldest complaint's sequence suffix
        oldest = candidates[0]
        suffix = oldest.complaint_id.split("-")[-1]
        incident_id = f"INC-{suffix}"
        
        new_count = len(candidates) + 1

        # Update all past group members
        for c in candidates:
            c.incident_id = incident_id
            c.duplicate_detected = 1
            c.duplicate_count = new_count

        # Update current complaint
        complaint.incident_id = incident_id
        complaint.duplicate_detected = 1
        complaint.duplicate_count = new_count
    else:
        # No duplicates — new master incident
        suffix = complaint.complaint_id.split("-")[-1]
        complaint.incident_id = f"INC-{suffix}"
        complaint.duplicate_detected = 0
        complaint.duplicate_count = 1

    db.commit()

