import os
import sys

# Guarantee parent path is in sys.path BEFORE any backend imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import logging
from fastapi import FastAPI, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

try:
    from backend.app.database.connection import engine, Base, SessionLocal
    from backend.app.models.models import User
    from backend.app.services.auth_service import hash_password, HTMLUnauthorizedException
    from backend.app.routers import auth, resume, analysis, admin, views
except ModuleNotFoundError:
    from app.database.connection import engine, Base, SessionLocal
    from app.models.models import User
    from app.services.auth_service import hash_password, HTMLUnauthorizedException
    from app.routers import auth, resume, analysis, admin, views

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Resume_Analyzer")

# Define Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")
STATIC_DIR = os.path.join(APP_DIR, "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
REPORTS_DIR = os.path.join(APP_DIR, "reports")
TEMP_DIR = os.path.join(APP_DIR, "temp")

# Ensure all application directories exist
for folder in [STATIC_DIR, TEMPLATES_DIR, UPLOAD_DIR, REPORTS_DIR, TEMP_DIR]:
    os.makedirs(folder, exist_ok=True)
    
# Subfolders for static
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)

# Initialize Database tables
Base.metadata.create_all(bind=engine)

# Seed Admin User if none exists
def seed_admin_user():
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.is_admin == True).first()
        if not admin_exists:
            logger.info("No admin user found. Seeding default admin account...")
            default_admin = User(
                email="admin@resumeanalyzer.com",
                hashed_password=hash_password("AdminPass123!"),
                full_name="System Administrator",
                is_admin=True
            )
            db.add(default_admin)
            db.commit()
            logger.info("Admin user seeded successfully. Email: admin@resumeanalyzer.com, Password: AdminPass123!")
    except Exception as e:
        logger.error(f"Error seeding admin user: {e}")
    finally:
        db.close()

seed_admin_user()

# Create FastAPI App
app = FastAPI(
    title="AI Resume Analyzer API",
    description="Backend API for parsing resumes, mapping skills, and compiling scoring audits.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handler to catch Unauthorized redirects on Jinja templates
@app.exception_handler(HTMLUnauthorizedException)
async def html_unauthorized_exception_handler(request: Request, exc: HTMLUnauthorizedException):
    """Intercept auth failure exceptions in views, clear cookie, and redirect to login."""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(analysis.router)
app.include_router(admin.router)
app.include_router(views.router)

@app.on_event("startup")
async def startup_event():
    logger.info("AI Resume Analyzer has initialized successfully.")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AI Resume Analyzer"}
