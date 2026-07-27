import pytest
from backend.app.services.similarity_service import (
    extract_required_experience,
    check_education_match,
    calculate_semantic_similarity,
    analyze_resume_against_jd
)

def test_experience_extraction_from_jd():
    """Test required years of experience parsing from JD text."""
    jd1 = "Looking for a Senior backend developer with 5+ years of experience in Python."
    assert extract_required_experience(jd1) == 5.0
    
    jd2 = "Must have minimum 3 years of work experience."
    assert extract_required_experience(jd2) == 3.0
    
    jd3 = "Entry level position, no experience required."
    assert extract_required_experience(jd3) == 0.0

def test_education_matching():
    """Test degree matching and leveling matrix."""
    jd_req = "Requires a Master's degree (MS) in Computer Science."
    
    # Candidate meets requirement (Master's)
    score1, msg1 = check_education_match(["Master of Science in Software engineering"], jd_req)
    assert score1 == 100
    assert "Meets" in msg1
    
    # Candidate exceeds requirement (PhD)
    score2, msg2 = check_education_match(["PhD in AI"], jd_req)
    assert score2 == 100
    assert "Meets" in msg2
    
    # Candidate falls below requirement (Bachelor's)
    score3, msg3 = check_education_match(["BS in Information Technology"], jd_req)
    assert score3 == 70
    assert "Partial" in msg3

def test_local_cosine_similarity_fallback():
    """Test similarity calculator falls back cleanly to TF-IDF cosine metrics."""
    text1 = "Python developer specializing in FastAPI and Postgres."
    text2 = "FastAPI backend engineer with database experience."
    
    score = calculate_semantic_similarity(text1, text2)
    assert 0.0 <= score <= 100.0

def test_overall_matching_logic():
    """Test aggregate ATS matcher score compiler logic and suggestions payload."""
    resume_text = "Jane Doe. Python, SQL. BS in CS. 3 years experience."
    parsed = {
        "contact": {"name": "Jane Doe", "email": "jane@doe.com", "phone": "123"},
        "skills": ["Python", "SQL"],
        "education": ["BS in CS"],
        "experience_years": 3.0,
        "has_experience_section": True,
        "has_projects_section": False,
        "has_certifications_section": False
    }
    jd_text = "Looking for a Developer with 2 years experience. Python, SQL, Docker. Degree in CS."
    
    results = analyze_resume_against_jd(resume_text, parsed, jd_text)
    
    assert "ats_score" in results
    assert 0 <= results["ats_score"] <= 100
    
    sugg = results["suggestions"]
    assert "Python" in sugg["matched_skills"]
    assert "SQL" in sugg["matched_skills"]
    assert "Docker" in sugg["missing_skills"]
    assert sugg["candidate_experience_parsed"] == 3.0
    assert sugg["required_experience_parsed"] == 2.0
    assert len(sugg["improvements"]) > 0
