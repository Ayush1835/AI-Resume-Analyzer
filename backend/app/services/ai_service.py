import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Check for API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_fallback_feedback(parsed_resume: Dict[str, Any], analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate high-quality rule-based fallback feedback if no LLM API keys are configured."""
    contact = parsed_resume.get("contact", {})
    name = contact.get("name", "Candidate")
    skills = parsed_resume.get("skills", [])
    exp_years = parsed_resume.get("experience_years", 0.0)
    
    suggestions = analysis_data.get("suggestions", {})
    matched_skills = suggestions.get("matched_skills", [])
    missing_skills = suggestions.get("missing_skills", [])
    edu_status = suggestions.get("education_status", "Reviewed")
    
    # 1. Professional Summary
    skills_str = ", ".join(skills[:5]) if skills else "various industry technologies"
    exp_text = f"with {exp_years} years of experience" if exp_years > 0 else "starting their professional journey"
    summary = (
        f"A results-oriented technology professional {exp_text}, demonstrating a solid foundation in {skills_str}. "
        f"Exhibits key competencies in system alignment, with focus on matching required capabilities like "
        f"{', '.join(matched_skills[:3]) if matched_skills else 'software engineering best practices'}."
    )
    
    # 2. Strengths
    strengths = []
    if matched_skills:
        strengths.append(f"Demonstrated technical alignment in core competencies: {', '.join(matched_skills[:4])}.")
    if exp_years > 3:
        strengths.append(f"Strong professional history with over {int(exp_years)} years of hands-on experience.")
    else:
        strengths.append("Quick learning capability demonstrated through diverse project implementations.")
    if "Meets" in edu_status:
        strengths.append(f"Educational qualifications align with the requested background: {edu_status}.")
    else:
        strengths.append("Strong portfolio of practical skills and implementations offsetting degree-specific criteria.")
        
    # 3. Weaknesses
    weaknesses = []
    if missing_skills:
        weaknesses.append(f"Missing core technical skills highlighted in the job requirements: {', '.join(missing_skills[:4])}.")
    else:
        weaknesses.append("No critical hard-skill gaps found, but continuous upskilling is encouraged.")
    if exp_years < suggestions.get("required_experience_parsed", 0.0):
        req_exp = suggestions.get("required_experience_parsed")
        weaknesses.append(f"Work history duration ({exp_years} years) falls below the requested standard ({int(req_exp)} years).")
    if not parsed_resume.get("has_projects_section"):
        weaknesses.append("Lack of an independent 'Projects' section leaves technical capabilities unvalidated outside work experience.")

    # 4. Rewrite Suggestions
    rewrites = {
        "work_experience_1": {
            "original": "Responsible for maintaining databases and helping build web applications.",
            "improved": f"Spearheaded database schema optimization and engineered dynamic web app components using {skills[0] if skills else 'Python'}, reducing latency by 15% and increasing uptime."
        },
        "projects_1": {
            "original": "Worked on a python project that analyzed data.",
            "improved": f"Architected a custom data analytics pipeline in Python utilizing {skills[1] if len(skills) > 1 else 'pandas'}, processing over 10,000 records to extract actionable business metrics."
        }
    }

    # 5. Missing Keywords
    missing_keywords = missing_skills[:6]
    if not missing_keywords:
        missing_keywords = ["Agile Methodologies", "CI/CD Pipelines", "System Architecture"]

    # 6. Career Advice
    career_advice = (
        f"Focus on bridging the skills gap by taking online training or building mini-projects in {', '.join(missing_skills[:3]) if missing_skills else 'cloud technologies'}. "
        "When rewriting your resume, make sure to replace descriptive tasks with quantifiable accomplishments, "
        "emphasizing the business value and metric improvements you brought to your team."
    )

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "rewrites": rewrites,
        "missing_keywords": missing_keywords,
        "career_advice": career_advice,
        "is_ai_generated": False
    }

def get_ai_feedback(resume_text: str, parsed_resume: Dict[str, Any], jd_text: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate LLM-based feedback from Gemini or OpenAI. Fallback to rule-based analysis if keys are missing."""
    
    # Check if Gemini key is available
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Setup prompt
            prompt = construct_ai_prompt(resume_text, parsed_resume, jd_text, analysis_data)
            
            # Request LLM
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            feedback = json.loads(response.text.strip())
            feedback["is_ai_generated"] = True
            return feedback
        except Exception as e:
            print(f"Gemini API execution failed: {e}. Attempting OpenAI or fallback...")
            
    # Check if OpenAI key is available
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            prompt = construct_ai_prompt(resume_text, parsed_resume, jd_text, analysis_data)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior technical recruiter and professional resume consultant. Your response must be in valid JSON format matching the schema requested."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            feedback = json.loads(response.choices[0].message.content.strip())
            feedback["is_ai_generated"] = True
            return feedback
        except Exception as e:
            print(f"OpenAI API execution failed: {e}. Falling back to rule-based analytics...")

    # Fall back to local rule-based system
    return generate_fallback_feedback(parsed_resume, analysis_data)

def construct_ai_prompt(resume_text: str, parsed_resume: Dict[str, Any], jd_text: str, analysis_data: Dict[str, Any]) -> str:
    """Generate the engineering prompt for LLMs."""
    # Truncate text inputs to prevent token overflows (limit to ~4000 characters)
    r_text_trunc = resume_text[:4000]
    j_text_trunc = jd_text[:4000]
    
    prompt = f"""
Analyze the candidate's resume text against the job description.
Provide structured feedback. You must return EXACTLY a JSON object with this structure:
{{
  "summary": "A concise professional summary of the candidate's alignment with the role (3-4 sentences)",
  "strengths": [
    "strength 1: with context of how it relates to the job requirements",
    "strength 2",
    "strength 3"
  ],
  "weaknesses": [
    "weakness 1: identify gaps in skills, experience, or education",
    "weakness 2",
    "weakness 3"
  ],
  "rewrites": {{
    "original_bullet_1": "improved bullet point 1 using strong action verbs, technical terms, and quantified metrics",
    "original_bullet_2": "improved bullet point 2"
  }},
  "missing_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "career_advice": "Detailed actionable career roadmap advice to help this candidate secure this or a similar job role."
}}

Resume Details:
- Candidate Name: {parsed_resume.get("contact", {}).get("name", "Applicant")}
- Extracted Skills: {parsed_resume.get("skills", [])}
- Extracted Experience: {parsed_resume.get("experience_years", 0)} years
- Extracted Education: {parsed_resume.get("education", [])}

Resume Raw Text:
---
{r_text_trunc}
---

Job Description:
---
{j_text_trunc}
---

ATS Pre-Analysis Data:
- ATS Score: {analysis_data.get("ats_score")}/100
- Keyword Match Score: {analysis_data.get("keyword_match_score")}/100
- Skills Match Score: {analysis_data.get("skills_match_score")}/100
- Semantic Similarity Score: {analysis_data.get("semantic_similarity_score")}/100
- Matched Skills: {analysis_data.get("suggestions", {}).get("matched_skills", [])}
- Missing Skills: {analysis_data.get("suggestions", {}).get("missing_skills", [])}

Ensure the output is valid JSON, strictly conforms to the requested keys, and does not contain markdown code block wrapping.
"""
    return prompt
