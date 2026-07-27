import pytest
from backend.app.services.parser_service import (
    extract_contact_info,
    parse_skills,
    parse_education,
    parse_experience_years
)

def test_extract_contact_info():
    """Test contact details extraction from text."""
    sample_text = (
        "John Doe\n"
        "Software Engineer\n"
        "Email: johndoe@gmail.com | Phone: 123-456-7890\n"
        "Education: Bachelor of Science in Computer Science"
    )
    contact = extract_contact_info(sample_text)
    assert contact["email"] == "johndoe@gmail.com"
    assert contact["phone"] == "123-456-7890"
    assert contact["name"] == "John Doe"

def test_parse_skills():
    """Test vocabluary based skills extraction."""
    sample_text = "I have experience with Python, FastAPI, Docker, and PostgreSQL database systems. Also familiar with Git."
    skills = parse_skills(sample_text)
    
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "PostgreSQL" in skills
    assert "Git" in skills
    assert "Java" not in skills

def test_parse_education():
    """Test academic degree matching."""
    sample_text = "Completed B.S. in Computer Science from Stanford University. Later finished Master of Science in Data Science."
    edu = parse_education(sample_text)
    
    # We expect degree mentions and surrounding sentences to be matched
    assert len(edu) >= 1
    assert any("B.S." in item or "Master" in item for item in edu)

def test_parse_experience_years():
    """Test date parsing and experience span calculations."""
    text1 = "Lead Developer (Jan 2018 - Dec 2020) worked on projects."
    years1 = parse_experience_years(text1)
    assert years1 == 2.9 # 35 months = ~2.9 years
    
    text2 = "Software Engineer at Google (2015-2020)."
    years2 = parse_experience_years(text2)
    assert years2 == 5.0 # 5 years
