# Transport Complaint Agent — Phase 1

An AI Multi-Agent system for collecting and managing public transport complaints.

## 🗂 Folder Structure

```
Transport Complaint Agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI entry point
│   │   ├── database.py      # SQLAlchemy engine & session
│   │   ├── models.py        # ORM models (Complaint)
│   │   ├── schemas.py       # Pydantic schemas & validation
│   │   ├── crud.py          # DB operations & ID generation
│   │   └── routes.py        # API route handlers
│   ├── uploads/             # Uploaded voice & image files
│   │   ├── voice/
│   │   └── images/
│   ├── complaints.db        # SQLite database (auto-created)
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── complaintsApi.js   # Axios API client
    │   ├── components/
    │   │   ├── Navbar.jsx         # Navigation bar
    │   │   └── SuccessModal.jsx   # Post-submission modal
    │   ├── pages/
    │   │   ├── ComplaintForm.jsx  # Complaint submission form
    │   │   └── Dashboard.jsx      # Admin dashboard
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css              # Tailwind + custom design system
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 🚀 Running the Application

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/complaints/create` | Submit a new complaint |
| GET | `/api/v1/complaints` | Get all complaints (admin) |
| GET | `/api/v1/complaints/{id}` | Get single complaint |
| GET | `/docs` | Swagger API documentation |
| GET | `/health` | Health check |

## 🗃 Database Schema

**Table: `complaints`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `complaint_id` | VARCHAR(20) | Format: CMP-2026-0001 |
| `passenger_name` | VARCHAR(100) | Full name |
| `mobile_number` | VARCHAR(15) | Phone number |
| `email` | VARCHAR(100) | Email address |
| `bus_number` | VARCHAR(20) | Bus registration number |
| `route_number` | VARCHAR(20) | Route identifier |
| `category` | VARCHAR(50) | Complaint category |
| `complaint_description` | TEXT | Detailed description |
| `incident_location` | VARCHAR(200) | Where it happened |
| `incident_datetime` | DATETIME | When it happened |
| `voice_file_path` | VARCHAR(500) | Path to audio file |
| `image_file_path` | VARCHAR(500) | Path to image file |
| `status` | VARCHAR(20) | Pending / In Progress / Resolved |
| `created_at` | DATETIME | Submission timestamp |

## ✨ Features (Phase 1)

- ✅ Responsive dark-theme UI with glassmorphism
- ✅ Multi-step complaint form with validation
- ✅ Voice & image evidence upload (drag & drop)
- ✅ Auto-generated complaint IDs (CMP-YYYY-NNNN)
- ✅ Success modal with copy-to-clipboard complaint ID
- ✅ Admin dashboard with stats and filtering
- ✅ FastAPI backend with Swagger docs
- ✅ SQLite database with SQLAlchemy ORM
