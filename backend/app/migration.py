"""
Database migration script for Phase 2.
Adds AI analysis columns to the existing complaints table.
Safe to run multiple times — skips already-existing columns.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "complaints.db")
DB_PATH = os.path.normpath(DB_PATH)

PHASE2_COLUMNS = [
    ("detected_language",    "VARCHAR(30)"),
    ("translated_text",      "TEXT"),
    ("extracted_bus_number", "VARCHAR(50)"),
    ("extracted_route_number","VARCHAR(50)"),
    ("extracted_location",   "VARCHAR(200)"),
    ("extracted_entities",   "TEXT"),
    ("extracted_keywords",   "TEXT"),
    ("ai_summary",           "TEXT"),
    # Phase 3 columns
    ("sentiment",            "VARCHAR(30)"),
    ("sentiment_score",      "VARCHAR(30)"),
    ("ai_categories",        "TEXT"),
    ("severity",             "VARCHAR(30)"),
    ("severity_score",       "VARCHAR(30)"),
    ("priority_level",       "VARCHAR(10)"),
    ("incident_id",          "VARCHAR(50)"),
    ("duplicate_count",      "INTEGER DEFAULT 1"),
    ("duplicate_detected",   "INTEGER DEFAULT 0"),
    ("recommended_action",   "TEXT"),
    # Phase 4 columns
    ("assigned_department",  "VARCHAR(100)"),
    ("assigned_team",        "VARCHAR(100)"),
    ("assigned_at",          "DATETIME"),
    ("escalation_status",    "INTEGER DEFAULT 0"),
    ("escalation_level",     "VARCHAR(100)"),
    ("escalated_at",         "DATETIME"),
    ("sla_deadline",         "DATETIME"),
    ("sla_status",           "VARCHAR(30)"),
    ("complaint_status",     "VARCHAR(50) DEFAULT 'Submitted'"),
    ("updated_at",           "DATETIME"),
    ("resolved_at",          "DATETIME"),
    ("resolution_notes",     "TEXT"),
    ("resolved_by",          "VARCHAR(100)"),
    ("resolution_time",      "VARCHAR(50)"),
    ("notifications",        "TEXT"),
]




def run_migration():
    if not os.path.exists(DB_PATH):
        # DB doesn't exist yet — SQLAlchemy will create it fresh with all columns
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(complaints)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    added = []
    for col_name, col_type in PHASE2_COLUMNS:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE complaints ADD COLUMN {col_name} {col_type}")
            added.append(col_name)

    conn.commit()
    conn.close()

    if added:
        print(f"[Migration] Added Phase 2 columns: {', '.join(added)}")
    else:
        print("[Migration] All Phase 2 columns already present.")



if __name__ == "__main__":
    run_migration()


# ── Phase 5: Create new analytics tables ──────────────────────────────

PHASE5_TABLES = {
    "complaint_trends": """
        CREATE TABLE IF NOT EXISTS complaint_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trend_type VARCHAR(50) NOT NULL,
            subject VARCHAR(200),
            trend_description TEXT NOT NULL,
            trend_score REAL DEFAULT 0.0,
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "route_risks": """
        CREATE TABLE IF NOT EXISTS route_risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_number VARCHAR(20) NOT NULL,
            risk_score REAL DEFAULT 0.0,
            risk_level VARCHAR(20),
            route_risk_score REAL DEFAULT 0.0,
            route_risk_level VARCHAR(20),
            complaint_count INTEGER DEFAULT 0,
            safety_count INTEGER DEFAULT 0,
            severe_count INTEGER DEFAULT 0,
            top_categories_json TEXT,
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "driver_risks": """
        CREATE TABLE IF NOT EXISTS driver_risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_identifier VARCHAR(100) NOT NULL,
            risk_score REAL DEFAULT 0.0,
            risk_level VARCHAR(20),
            driver_risk_score REAL DEFAULT 0.0,
            driver_risk_level VARCHAR(20),
            complaint_count INTEGER DEFAULT 0,
            misconduct_count INTEGER DEFAULT 0,
            safety_count INTEGER DEFAULT 0,
            recommendation TEXT,
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "bus_risks": """
        CREATE TABLE IF NOT EXISTS bus_risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number VARCHAR(20) NOT NULL,
            maintenance_risk VARCHAR(20),
            risk_score REAL DEFAULT 0.0,
            complaint_count INTEGER DEFAULT 0,
            maintenance_count INTEGER DEFAULT 0,
            overcrowding_count INTEGER DEFAULT 0,
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "complaint_forecasts": """
        CREATE TABLE IF NOT EXISTS complaint_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forecast_type VARCHAR(30) NOT NULL,
            period_label VARCHAR(50),
            predicted_count REAL DEFAULT 0.0,
            confidence VARCHAR(20),
            trend_direction VARCHAR(20),
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "preventive_recommendations": """
        CREATE TABLE IF NOT EXISTS preventive_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rec_type VARCHAR(30) NOT NULL,
            subject VARCHAR(200),
            recommendation TEXT NOT NULL,
            preventive_recommendation TEXT,
            priority VARCHAR(20),
            recommendation_priority VARCHAR(20),
            status VARCHAR(20) DEFAULT 'Active',
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "smart_alerts": """
        CREATE TABLE IF NOT EXISTS smart_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type VARCHAR(50) NOT NULL,
            subject VARCHAR(200),
            message TEXT NOT NULL,
            risk_level VARCHAR(20),
            status VARCHAR(20) DEFAULT 'unread',
            metadata_json TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
}


def run_phase5_migration():
    """Create Phase 5 analytics tables if they don't exist."""
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created = []
    for table_name, ddl in PHASE5_TABLES.items():
        cursor.execute(ddl)
        created.append(table_name)
    conn.commit()
    conn.close()
    print(f"[Migration] Phase 5 tables ensured: {', '.join(created)}")

