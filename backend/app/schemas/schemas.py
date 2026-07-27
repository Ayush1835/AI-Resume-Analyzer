from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- TOKEN SCHEMAS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    is_admin: bool = False

# --- RESUME SCHEMAS ---
class ResumeOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    extracted_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# --- JOB DESCRIPTION SCHEMAS ---
class JobDescriptionCreate(BaseModel):
    title: Optional[str] = "Job Description"
    text_content: str = Field(..., min_length=10, description="Job description text is too short")

class JobDescriptionOut(BaseModel):
    id: int
    title: Optional[str]
    text_content: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- ANALYSIS SCHEMAS ---
class AnalysisCreate(BaseModel):
    resume_id: int
    job_description_id: Optional[int] = None
    job_description_text: Optional[str] = None

class AnalysisOut(BaseModel):
    id: int
    user_id: int
    resume_id: int
    job_description_id: int
    ats_score: int
    keyword_match_score: int
    skills_match_score: int
    experience_match_score: int
    education_match_score: int
    semantic_similarity_score: int
    suggestions_json: Optional[Dict[str, Any]] = None
    ai_feedback_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- REPORT SCHEMAS ---
class ReportOut(BaseModel):
    id: int
    analysis_id: int
    report_path: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- DASHBOARD & ANALYTICS SCHEMAS ---
class RecentAnalysis(BaseModel):
    id: int
    resume_name: str
    jd_title: str
    ats_score: int
    similarity_score: int
    created_at: datetime

class DashboardStats(BaseModel):
    total_users: Optional[int] = None  # Only visible to admin
    total_resumes: int
    total_analyses: int
    avg_ats_score: float
    avg_similarity_score: float
    recent_analyses: List[RecentAnalysis]
    skill_distribution: Dict[str, int]  # Frequency count of matched skills
