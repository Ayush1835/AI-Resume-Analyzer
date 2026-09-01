import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

try:
    from backend.app.database.connection import get_db
    from backend.app.models.models import Resume, JobDescription, Analysis, Report, User
    from backend.app.schemas.schemas import AnalysisOut
    from backend.app.services.auth_service import get_current_user
    from backend.app.services.parser_service import (
        extract_text_from_pdf,
        extract_text_from_docx
    )
    from backend.app.services.similarity_service import analyze_resume_against_jd
    from backend.app.services.ai_service import get_ai_feedback
    from backend.app.services.pdf_service import generate_pdf_report
except ModuleNotFoundError:
    from app.database.connection import get_db
    from app.models.models import Resume, JobDescription, Analysis, Report, User
    from app.schemas.schemas import AnalysisOut
    from app.services.auth_service import get_current_user
    from app.services.parser_service import (
        extract_text_from_pdf,
        extract_text_from_docx
    )
    from app.services.similarity_service import analyze_resume_against_jd
    from app.services.ai_service import get_ai_feedback
    from app.services.pdf_service import generate_pdf_report

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

# Constants
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")

# Ensure directories exist
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/analyze", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
async def analyze_resume(
    resume_id: int = Form(...),
    jd_title: Optional[str] = Form("Job Description"),
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze a previously uploaded resume against a job description (text or file upload)."""
    # 1. Fetch Resume
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or access denied."
        )

    # 2. Extract JD text
    extracted_jd_text = ""
    if jd_text and jd_text.strip():
        extracted_jd_text = jd_text.strip()
    elif jd_file:
        _, ext = os.path.splitext(jd_file.filename.lower())
        if ext not in [".pdf", ".docx"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported job description format. Only PDF and DOCX files are allowed."
            )
            
        # Write to temporary file for parsing
        temp_file_name = f"jd_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(TEMP_DIR, temp_file_name)
        try:
            with open(temp_path, "wb") as buffer:
                content = await jd_file.read()
                buffer.write(content)
                
            if ext == ".pdf":
                extracted_jd_text = extract_text_from_pdf(temp_path)
            elif ext == ".docx":
                extracted_jd_text = extract_text_from_docx(temp_path)
        finally:
            # Delete temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a job description by pasting the text or uploading a file."
        )
        
    if not extracted_jd_text or not extracted_jd_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract readable text from the job description."
        )
        
    # 3. Save Job Description to DB
    new_jd = JobDescription(
        title=jd_title or "Job Description",
        text_content=extracted_jd_text
    )
    db.add(new_jd)
    db.commit()
    db.refresh(new_jd)
    
    try:
        # 4. Perform Scoring & Skills Gap Analysis
        parsed_res_dict = resume.extracted_json if isinstance(resume.extracted_json, dict) else {}
        analysis_results = analyze_resume_against_jd(
            resume_text=resume.extracted_text or "",
            parsed_resume=parsed_res_dict,
            jd_text=extracted_jd_text
        )
        
        # 5. Fetch AI Suggestions
        ai_feedback = get_ai_feedback(
            resume_text=resume.extracted_text or "",
            parsed_resume=parsed_res_dict,
            jd_text=extracted_jd_text,
            analysis_data=analysis_results
        )
        
        # 6. Save Analysis to DB
        new_analysis = Analysis(
            user_id=current_user.id,
            resume_id=resume.id,
            job_description_id=new_jd.id,
            ats_score=analysis_results.get("ats_score", 0),
            keyword_match_score=analysis_results.get("keyword_match_score", 0),
            skills_match_score=analysis_results.get("skills_match_score", 0),
            experience_match_score=analysis_results.get("experience_match_score", 0),
            education_match_score=analysis_results.get("education_match_score", 0),
            semantic_similarity_score=analysis_results.get("semantic_similarity_score", 0),
            suggestions_json=analysis_results.get("suggestions", {}),
            ai_feedback_json=ai_feedback
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
    except Exception as e:
        logger.error(f"Analysis engine exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Analysis calculation failed: {str(e)}"
        )
    
    # 7. Generate PDF Report safely
    try:
        extracted_json = resume.extracted_json if isinstance(resume.extracted_json, dict) else {}
        contact_dict = extracted_json.get("contact", {}) if isinstance(extracted_json.get("contact"), dict) else {}
        applicant_name = contact_dict.get("name") or current_user.full_name or "Applicant"

        report_filename = f"report_{new_analysis.id}_{uuid.uuid4().hex[:8]}.pdf"
        report_path = os.path.join(REPORTS_DIR, report_filename)

        scores_dict = {
            "ats_score": new_analysis.ats_score,
            "keyword_match_score": new_analysis.keyword_match_score,
            "skills_match_score": new_analysis.skills_match_score,
            "experience_match_score": new_analysis.experience_match_score,
            "education_match_score": new_analysis.education_match_score,
            "semantic_similarity_score": new_analysis.semantic_similarity_score
        }

        generate_pdf_report(
            output_pdf_path=report_path,
            applicant_name=applicant_name,
            contact_info=contact_dict,
            scores=scores_dict,
            suggestions=new_analysis.suggestions_json,
            ai_feedback=new_analysis.ai_feedback_json
        )

        new_report = Report(
            analysis_id=new_analysis.id,
            report_path=report_path
        )
        db.add(new_report)
        db.commit()
    except Exception as e:
        logger.error(f"PDF Report generation skipped: {e}")
        
    return new_analysis

@router.get("/history", response_model=List[AnalysisOut])
def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the entire analysis history for the current user."""
    return db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.created_at.desc()).all()

@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis_details(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details for a single resume analysis run."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found or access denied."
        )
    return analysis

@router.get("/{analysis_id}/download")
def download_pdf_report(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the generated ReportLab PDF report."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found or access denied."
        )
        
    report = db.query(Report).filter(Report.analysis_id == analysis.id).first()
    if not report or not os.path.exists(report.report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report file not found on disk. Please re-run the analysis."
        )
        
    # Generate download filename
    download_name = f"ATS_Report_{analysis.id}.pdf"
    
    return FileResponse(
        path=report.report_path,
        media_type="application/pdf",
        filename=download_name
    )

@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an analysis run and remove its associated PDF report from disk."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found or access denied."
        )
        
    # Get associated report to clean up disk file
    report = db.query(Report).filter(Report.analysis_id == analysis.id).first()
    if report and os.path.exists(report.report_path):
        try:
            os.remove(report.report_path)
        except OSError as e:
            print(f"Error removing physical report file: {e}")
            
    # Delete DB records (CASCADE handles related tables)
    db.delete(analysis)
    db.commit()
    
    return {"detail": "Analysis run deleted successfully"}
