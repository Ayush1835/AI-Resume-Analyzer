import os
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional

from backend.app.database.connection import get_db
from backend.app.models.models import User, Resume, Analysis, JobDescription
from backend.app.services.auth_service import (
    get_current_user,
    get_current_admin,
    decode_access_token,
    get_token_from_request
)

router = APIRouter(tags=["Views"])

# Get template directory path
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Helper to check if a user is logged in, without raising redirect exceptions."""
    token = get_token_from_request(request)
    if not token:
        return None
    token_data = decode_access_token(token)
    if not token_data:
        return None
    return db.query(User).filter(User.id == token_data.user_id).first()

@router.get("/", response_class=HTMLResponse)
def index_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Serve the landing index page or redirect authenticated users to the dashboard."""
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "login.html")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Serve login page."""
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "login.html")

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Serve registration page."""
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "register.html")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve statistical data and serve dashboard view."""
    # User-specific statistics
    user_resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    user_analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).all()
    
    total_resumes = len(user_resumes)
    total_analyses = len(user_analyses)
    
    # Averages
    avg_ats = 0.0
    avg_sim = 0.0
    if total_analyses > 0:
        avg_ats = db.query(func.avg(Analysis.ats_score)).filter(Analysis.user_id == current_user.id).scalar() or 0.0
        avg_sim = db.query(func.avg(Analysis.semantic_similarity_score)).filter(Analysis.user_id == current_user.id).scalar() or 0.0
        
    avg_ats = round(float(avg_ats), 1)
    avg_sim = round(float(avg_sim), 1)
    
    # List of recent analysis runs for the table
    recent_analyses = []
    # Join with Resume and JobDescription to extract titles
    query_runs = (
        db.query(Analysis, Resume, JobDescription)
        .join(Resume, Analysis.resume_id == Resume.id)
        .join(JobDescription, Analysis.job_description_id == JobDescription.id)
        .filter(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(5)
        .all()
    )
    
    for analysis, resume, jd in query_runs:
        recent_analyses.append({
            "id": analysis.id,
            "resume_name": resume.filename,
            "jd_title": jd.title or "Job Description",
            "ats_score": analysis.ats_score,
            "similarity_score": analysis.semantic_similarity_score,
            "created_at": analysis.created_at.strftime("%Y-%m-%d %H:%M")
        })
        
    # Compile skill frequencies for Chart.js
    skill_frequencies: Dict[str, int] = {}
    for run in user_analyses:
        suggestions = run.suggestions_json or {}
        matched_skills = suggestions.get("matched_skills", [])
        for skill in matched_skills:
            skill_frequencies[skill] = skill_frequencies.get(skill, 0) + 1
            
    # Sort and take top 10 skills for chart
    sorted_skills = sorted(skill_frequencies.items(), key=lambda x: x[1], reverse=True)[:10]
    skill_labels = [item[0] for item in sorted_skills]
    skill_counts = [item[1] for item in sorted_skills]
    
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": current_user,
            "total_resumes": total_resumes,
            "total_analyses": total_analyses,
            "avg_ats_score": avg_ats,
            "avg_similarity_score": avg_sim,
            "recent_analyses": recent_analyses,
            "skill_labels": skill_labels,
            "skill_counts": skill_counts
        }
    )

@router.get("/analyze", response_class=HTMLResponse)
def analyze_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve user resumes list and serve resume parser workspace."""
    user_resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.uploaded_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "analyze.html",
        {
            "user": current_user,
            "resumes": user_resumes
        }
    )

@router.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    current_admin: User = Depends(get_current_admin)
):
    """Serve administrative view."""
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "user": current_admin
        }
    )
