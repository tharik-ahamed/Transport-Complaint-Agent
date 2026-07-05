import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ── AI config ─────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
AI_ENABLED: bool = bool(GEMINI_API_KEY)
GEMINI_MODEL: str = "gemini-1.5-flash"

# ── JWT auth config ────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "transport-complaint-jwt-secret-change-in-production-please"
)
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

# Admin credentials (override in .env for production)
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
