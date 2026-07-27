import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.models import Resume, User
from backend.app.schemas.schemas import ResumeOut
from backend.app.services.auth_service import get_current_user
from backend.app.services.parser_service import (
    extract_text_from_pdf,
    extract_text_from_docx,
    parse_resume_text
)

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

# Constants
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def validate_file(file: UploadFile) -> str:
    """Validate file type and size, return the file extension."""
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Only PDF and DOCX files are allowed."
        )
        
    # Read file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)  # Reset stream position
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 5MB."
        )
        
    return ext

@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload, parse, and store a resume file (PDF/DOCX)."""
    ext = validate_file(file)
    
    # Generate secure, unique filename on disk
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file to disk
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(e)}"
        )
        
    # Extract text from file based on extension
    raw_text = ""
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        raw_text = extract_text_from_docx(file_path)
        
    if not raw_text.strip():
        # Clean up file if text extraction failed completely
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract readable text from the uploaded document. Please check the file formatting."
        )
        
    # Segment and parse the resume text
    parsed_json = parse_resume_text(raw_text)
    
    # Create DB model
    new_resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        extracted_text=raw_text,
        extracted_json=parsed_json
    )
    
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    return new_resume

@router.get("", response_model=List[ResumeOut])
def get_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all resumes uploaded by the current user."""
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.uploaded_at.desc()).all()

@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a resume and remove its associated file from disk."""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or access denied."
        )
        
    # Delete file from disk
    if os.path.exists(resume.file_path):
        try:
            os.remove(resume.file_path)
        except OSError as e:
            print(f"Error removing physical file: {e}")
            
    # Delete DB records (CASCADE will handle Analysis and Reports)
    db.delete(resume)
    db.commit()
    
    return {"detail": "Resume deleted successfully"}
