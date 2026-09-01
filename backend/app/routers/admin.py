from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from backend.app.database.connection import get_db
    from backend.app.models.models import User, Resume, Analysis
    from backend.app.schemas.schemas import UserOut, ResumeOut
    from backend.app.services.auth_service import get_current_admin
except ModuleNotFoundError:
    from app.database.connection import get_db
    from app.models.models import User, Resume, Analysis
    from app.schemas.schemas import UserOut, ResumeOut
    from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])

@router.get("/stats", response_model=Dict[str, Any])
def get_admin_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Compile global system statistics for the admin dashboard."""
    total_users = db.query(User).count()
    total_resumes = db.query(Resume).count()
    total_analyses = db.query(Analysis).count()
    
    # Calculate average ATS score across all users
    avg_ats = db.query(func.avg(Analysis.ats_score)).scalar() or 0.0
    avg_ats = round(float(avg_ats), 1)
    
    # Calculate average semantic similarity
    avg_sim = db.query(func.avg(Analysis.semantic_similarity_score)).scalar() or 0.0
    avg_sim = round(float(avg_sim), 1)
    
    return {
        "total_users": total_users,
        "total_resumes": total_resumes,
        "total_analyses": total_analyses,
        "avg_ats_score": avg_ats,
        "avg_similarity_score": avg_sim
    }

@router.get("/users", response_model=List[UserOut])
def list_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retrieve lists of all registered users."""
    return db.query(User).order_by(User.created_at.desc()).all()

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a user account. cascade deletes their resumes and reports. Prevents self-deletion."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-deletion is forbidden. You cannot delete your own administrative account."
        )
        
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    # Query all resumes of this user to clean up disk files
    resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
    for resume in resumes:
        if os.path.exists(resume.file_path):
            try:
                os.remove(resume.file_path)
            except OSError as e:
                print(f"Error removing resume file during user cleanup: {e}")
                
    # Also clean up report files
    analyses = db.query(Analysis).filter(Analysis.user_id == user_id).all()
    for analysis in analyses:
        for report in analysis.reports:
            if os.path.exists(report.report_path):
                try:
                    os.remove(report.report_path)
                except OSError as e:
                    print(f"Error removing report file during user cleanup: {e}")

    db.delete(user_to_delete)
    db.commit()
    return {"detail": f"User '{user_to_delete.email}' deleted successfully"}

@router.get("/resumes")
def list_all_resumes(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retrieve listing of all resumes uploaded across the platform (Admin-only)."""
    resumes = db.query(Resume).order_by(Resume.uploaded_at.desc()).all()
    
    results = []
    for r in resumes:
        # Fetch user email for representation
        owner = db.query(User).filter(User.id == r.user_id).first()
        results.append({
            "id": r.id,
            "filename": r.filename,
            "uploaded_at": r.uploaded_at,
            "user_id": r.user_id,
            "owner_email": owner.email if owner else "Unknown",
            "skills": r.extracted_json.get("skills", []) if r.extracted_json else []
        })
    return results
