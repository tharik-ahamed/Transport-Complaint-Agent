from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app import routes
from app import ai_routes
from app import auth_routes            # JWT auth routes
from app import analytics_routes       # Phase 3 analytics
from app import phase4_routes          # Phase 4 workflow
from app import predictive_routes      # Phase 5 predictive
from app import executive_routes       # Phase 6 executive
from app.migration import run_migration, run_phase5_migration
import os

# Run Phase 2 database migration (safe to run on every startup)
run_migration()

# Create DB tables (for fresh installs)
# Run DB migrations on startup
run_migration()
run_phase5_migration()

# Import Phase 5 models so SQLAlchemy creates their tables too
import app.predictive_models  # noqa: F401, E402
Base.metadata.create_all(bind=engine)

# Create uploads directory
os.makedirs("uploads/voice", exist_ok=True)
os.makedirs("uploads/images", exist_ok=True)

app = FastAPI(
    title="Transport Complaint Agent API",
    description="AI-powered complaint management system — Phases 1 to 6",
    version="6.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://transport-complaint-agent.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads as static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
# IMPORTANT: phase4 workflow_router registered BEFORE routes.router so static
# paths (/assigned, /escalated, /sla) are matched before /{complaint_id}
app.include_router(phase4_routes.workflow_router)   # Phase 4 static complaint paths
app.include_router(routes.router)                   # Phase 1 complaint routes (parameterized)
app.include_router(ai_routes.router)                # Phase 2+3 AI routes
app.include_router(auth_routes.router)              # JWT auth routes
app.include_router(analytics_routes.router)         # Phase 3+4 analytics
app.include_router(phase4_routes.dept_router)       # Phase 4 department dashboard
app.include_router(predictive_routes.router)        # Phase 5 predictive analytics
app.include_router(executive_routes.router)         # Phase 6 executive intelligence



@app.get("/")
async def root():
    from app.config import AI_ENABLED
    return {
        "message": "Transport Complaint Agent API",
        "version": "6.0.0",
        "phase": "Phases 1 to 6 (Core + AI + Decisions + Workflows + Predictive + Executive)",
        "ai_enabled": AI_ENABLED,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    from app.config import AI_ENABLED
    return {"status": "healthy", "ai_enabled": AI_ENABLED}
