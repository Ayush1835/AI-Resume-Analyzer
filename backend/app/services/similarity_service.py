import re
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from backend.app.services.parser_service import parse_skills, parse_resume_text
except ModuleNotFoundError:
    from app.services.parser_service import parse_skills, parse_resume_text

# Lazy load Sentence Transformers to prevent crash if model files can't be fetched
_model = None

def get_sentence_transformer_model():
    """Lazily load the SentenceTransformer model safely."""
    global _model
    if _model is not None:
        return _model
    
    try:
        from sentence_transformers import SentenceTransformer
        # Use a small, fast model
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        return _model
    except Exception as e:
        print(f"Warning: Could not load SentenceTransformer model ({e}). Falling back to TF-IDF.")
        return None

def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts using Sentence Transformers or TF-IDF fallback."""
    if not text1.strip() or not text2.strip():
        return 0.0

    # On cloud platforms (like Render), use ultra-fast TF-IDF to stay well within 512MB RAM cap
    if "RENDER" in os.environ or "PORT" in os.environ:
        try:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([text1, text2])
            sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return round(float(sim) * 100.0, 1)
        except Exception:
            return 50.0

    model = get_sentence_transformer_model()
    if model is not None:
        try:
            embeddings = model.encode([text1, text2])
            # Cosine similarity between the two embeddings
            emb1 = embeddings[0].reshape(1, -1)
            emb2 = embeddings[1].reshape(1, -1)
            sim = cosine_similarity(emb1, emb2)[0][0]
            # Map cosine range [-1, 1] or [0, 1] to [0, 100]
            score = max(0.0, float(sim) * 100.0)
            return round(score, 1)
        except Exception as e:
            print(f"Error during semantic embedding calculation: {e}. Falling back to TF-IDF.")
            
    # Fallback: TF-IDF Cosine Similarity
    try:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([text1, text2])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(sim) * 100.0, 1)
    except Exception as e:
        print(f"Error during TF-IDF calculation: {e}")
        return 50.0 # Standard fallback default

def extract_required_experience(jd_text: str) -> float:
    """Parse the JD to extract required years of experience."""
    # Matches patterns like "3+ years", "5 years of experience", "minimum 2 years", "at least 10 years"
    pattern = r'(?:(\d+)\s*\+?\s*years?|years?\s*(?:of)?\s*experience\s*[^0-9]*(\d+))'
    matches = re.findall(pattern, jd_text, re.IGNORECASE)
    
    years = []
    for match in matches:
        val1, val2 = match
        if val1:
            years.append(int(val1))
        if val2:
            years.append(int(val2))
            
    if years:
        return float(max(years))
    return 0.0 # Default if no experience is explicitly mentioned

def check_education_match(candidate_edu: List[str], jd_text: str) -> Tuple[int, str]:
    """Calculate education match score based on candidate degrees and JD requirements."""
    jd_text_lower = jd_text.lower()
    
    # Define degree levels
    degree_hierarchy = {"phd": 4, "doctorate": 4, "master": 3, "ms": 3, "mba": 3, "mtech": 3, "bachelor": 2, "bs": 2, "btech": 2, "associate": 1}
    
    # Determine JD required level
    jd_req_level = 0
    jd_req_name = "None"
    for degree_name, level in degree_hierarchy.items():
        # Match as word boundary (e.g. \bms\b)
        if re.search(rf"\b{degree_name}\b", jd_text_lower):
            if level > jd_req_level:
                jd_req_level = level
                jd_req_name = degree_name.upper()
                
    # Determine Candidate level
    cand_level = 0
    candidate_edu_str = " ".join(candidate_edu).lower()
    for degree_name, level in degree_hierarchy.items():
        if re.search(rf"\b{degree_name}\b", candidate_edu_str):
            if level > cand_level:
                cand_level = level
                
    # If no requirements, candidate gets full credit
    if jd_req_level == 0:
        return 100, "No specific degree required"
        
    # Candidate meets or exceeds requirements
    if cand_level >= jd_req_level:
        return 100, f"Meets requirement ({jd_req_name})"
    elif cand_level == 0:
        return 40, f"No degree found (Requires {jd_req_name})"
    else:
        # Candidate has some degree but lower than required
        return 70, f"Partial Match (Requires {jd_req_name})"

def analyze_resume_against_jd(resume_text: str, parsed_resume: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
    """Perform matching and score compilation between resume and JD."""
    # 1. Semantic Similarity
    semantic_score = calculate_semantic_similarity(resume_text, jd_text)
    
    # 2. Keyword matching score via TF-IDF cosine similarity
    keyword_score = 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([resume_text, jd_text])
        keyword_score = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]) * 100.0
    except:
        keyword_score = semantic_score # Fallback to semantic score
    keyword_score = round(keyword_score, 1)

    # 3. Skills Match
    jd_skills = parse_skills(jd_text)
    cand_skills = parsed_resume.get("skills", [])
    
    matched_skills = []
    missing_skills = []
    
    if jd_skills:
        for skill in jd_skills:
            if any(skill.lower() == c_skill.lower() for c_skill in cand_skills):
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)
        skills_match_percent = (len(matched_skills) / len(jd_skills)) * 100.0
    else:
        # If JD has no parseable skills, score is based on candidate having general skills
        skills_match_percent = min(100.0, len(cand_skills) * 8.0)
        
    skills_score = round(skills_match_percent, 1)

    # 4. Experience Match
    required_exp = extract_required_experience(jd_text)
    cand_exp = parsed_resume.get("experience_years", 0.0)
    
    if required_exp > 0:
        if cand_exp >= required_exp:
            exp_score = 100.0
        else:
            # Partial score
            exp_score = (cand_exp / required_exp) * 100.0
    else:
        # If JD doesn't mention experience, award full points if candidate has any, else base points
        exp_score = 100.0 if cand_exp > 0 else 70.0
    exp_score = round(exp_score, 1)

    # 5. Education Match
    edu_score, edu_msg = check_education_match(parsed_resume.get("education", []), jd_text)
    
    # 6. Resume Completeness (Sections structure)
    completeness_pts = 0
    contact = parsed_resume.get("contact", {})
    if contact.get("email"): completeness_pts += 10
    if contact.get("phone"): completeness_pts += 10
    if contact.get("name") and contact.get("name") != "Applicant Name": completeness_pts += 10
    
    if parsed_resume.get("has_experience_section"): completeness_pts += 25
    if parsed_resume.get("skills"): completeness_pts += 25
    if parsed_resume.get("has_projects_section"): completeness_pts += 10
    if parsed_resume.get("has_certifications_section"): completeness_pts += 10
    
    completeness_score = float(completeness_pts)

    # 7. Formatting & Suggestions Rules
    formatting_suggestions = []
    formatting_score = 100
    
    # Rule 1: Text length
    words_count = len(resume_text.split())
    if words_count < 200:
        formatting_suggestions.append("The resume is very short. Expand on your descriptions.")
        formatting_score -= 20
    elif words_count > 1500:
        formatting_suggestions.append("The resume is quite long. Try to keep it within 1-2 pages (under 1000 words).")
        formatting_score -= 10
        
    # Rule 2: Contact info missing
    if not contact.get("phone") or not contact.get("email"):
        formatting_suggestions.append("Ensure your email and phone number are clearly visible in the header.")
        formatting_score -= 15
        
    # Rule 3: Action verbs check
    action_verbs = ["led", "developed", "managed", "designed", "implemented", "created", "increased", "optimized", "built"]
    verbs_found = [v for v in action_verbs if re.search(rf"\b{v}\b", resume_text.lower())]
    if len(verbs_found) < 3:
        formatting_suggestions.append("Use strong action verbs to start your bullet points (e.g., 'Optimized performance', 'Led a team').")
        formatting_score -= 15
        
    # Rule 4: Metrics / Quantifying experience
    # Check if there are percentages or numbers that indicate quantified results
    has_metrics = re.search(r'\b\d+%\b|\$\d+|\b\d+\s*(?:million|percent|users|servers|records)\b', resume_text)
    if not has_metrics:
        formatting_suggestions.append("Quantify your achievements. Use percentages, dollar values, or user counts (e.g., 'Reduced loading time by 30%').")
        formatting_score -= 20

    formatting_score = max(30, formatting_score)
    
    # 8. Aggregate final score (Weights)
    # Skills: 30%, Experience: 20%, Keywords: 20%, Education: 10%, Completeness: 10%, Formatting: 10%
    final_score = (
        (skills_score * 0.30) +
        (exp_score * 0.20) +
        (keyword_score * 0.20) +
        (edu_score * 0.10) +
        (completeness_score * 0.10) +
        (formatting_score * 0.10)
    )
    final_score = int(round(final_score))
    
    # Compile Improvements Suggestions list
    improvements = []
    if missing_skills:
        # Recommend top missing skills to add
        rec_skills = ", ".join(missing_skills[:5])
        improvements.append(f"Consider adding or acquiring the following key skills mentioned in the job description: {rec_skills}.")
    if exp_score < 80 and required_exp > 0:
        improvements.append(f"The job requires about {int(required_exp)} years of experience. Highlight transferrable experiences or relevant coursework to bridge the gap.")
    if not parsed_resume.get("has_projects_section"):
        improvements.append("Add a 'Projects' section to showcase personal or academic applications of your skills.")
    if not parsed_resume.get("has_certifications_section"):
        improvements.append("Include relevant technical certifications to validate your skills.")
        
    # Add formatting suggestions
    improvements.extend(formatting_suggestions)
    if not improvements:
        improvements.append("Your resume matches the structural layout perfectly. Enhance formatting details further if applying to executive roles.")

    return {
        "ats_score": final_score,
        "keyword_match_score": int(round(keyword_score)),
        "skills_match_score": int(round(skills_score)),
        "experience_match_score": int(round(exp_score)),
        "education_match_score": int(round(edu_score)),
        "semantic_similarity_score": int(round(semantic_score)),
        "suggestions": {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "formatting_score": formatting_score,
            "education_status": edu_msg,
            "required_experience_parsed": required_exp,
            "candidate_experience_parsed": cand_exp,
            "improvements": improvements
        }
    }
