import streamlit as st
import os
import sys
import tempfile
import uuid
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Ensure root directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.parser_service import (
    extract_text_from_pdf,
    extract_text_from_docx,
    parse_resume_text
)
from backend.app.services.similarity_service import analyze_resume_against_jd
from backend.app.services.ai_service import get_ai_feedback
from backend.app.services.pdf_service import generate_pdf_report

# Page Config
st.set_page_config(
    page_title="AI Resume Analyzer & ATS Scorer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Configuration
st.sidebar.title("⚙️ AI Configuration")
st.sidebar.markdown("Configure settings and LLM credentials.")

# API Key input
user_gemini_key = st.sidebar.text_input("Gemini API Key (Optional)", type="password", help="Enter your Gemini API key to unlock advanced AI rewrites and career roadmaps.")
if user_gemini_key:
    os.environ["GEMINI_API_KEY"] = user_gemini_key

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip**: If no API key is provided, the app uses built-in NLP rules and local Sentence Transformers (`all-MiniLM-L6-v2`) to calculate ATS scores!")

# App Title & Header
st.title("📝 AI Resume Analyzer & ATS Optimization Engine")
st.markdown("Analyze your resume against job descriptions, calculate ATS match scores, identify missing skills, and generate downloadable audit reports.")

st.markdown("---")

# Layout Columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Upload Resume")
    uploaded_resume = st.file_uploader("Choose your resume (PDF or DOCX)", type=["pdf", "docx"])

with col2:
    st.subheader("2. Target Job Description")
    jd_input_method = st.radio("Provide Job Description via:", ["Paste Text", "Upload Document (PDF/DOCX)"])
    
    jd_text = ""
    if jd_input_method == "Paste Text":
        jd_text = st.text_area("Paste Job Requirements", height=180, placeholder="Paste the job description details here...")
    else:
        uploaded_jd_file = st.file_uploader("Choose Job Description File", type=["pdf", "docx"])
        if uploaded_jd_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_jd_file.name)[1]) as tmp_jd:
                tmp_jd.write(uploaded_jd_file.getvalue())
                tmp_jd_path = tmp_jd.name
            
            ext = os.path.splitext(uploaded_jd_file.name)[1].lower()
            if ext == ".pdf":
                jd_text = extract_text_from_pdf(tmp_jd_path)
            elif ext == ".docx":
                jd_text = extract_text_from_docx(tmp_jd_path)
            
            if os.path.exists(tmp_jd_path):
                os.remove(tmp_jd_path)

# Run Button
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 Evaluate Resume & Job Match", type="primary", use_container_width=True):
    if not uploaded_resume:
        st.error("Please upload a resume (PDF or DOCX) to proceed.")
    elif not jd_text or not jd_text.strip():
        st.error("Please provide a target job description (text paste or document upload).")
    else:
        with st.spinner("Parsing resume, calculating semantic similarity, and compiling AI analysis..."):
            # Save uploaded resume to temp file
            ext = os.path.splitext(uploaded_resume.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_res:
                tmp_res.write(uploaded_resume.getvalue())
                tmp_res_path = tmp_res.name

            try:
                # Extract text
                if ext == ".pdf":
                    resume_text = extract_text_from_pdf(tmp_res_path)
                elif ext == ".docx":
                    resume_text = extract_text_from_docx(tmp_res_path)
                else:
                    resume_text = ""

                if not resume_text.strip():
                    st.error("Could not extract readable text from the uploaded resume. Please check formatting.")
                else:
                    # 1. Parse Resume
                    parsed_resume = parse_resume_text(resume_text)
                    
                    # 2. Run ATS Matching Engine
                    analysis_results = analyze_resume_against_jd(resume_text, parsed_resume, jd_text)
                    
                    # 3. Fetch AI Feedback
                    ai_feedback = get_ai_feedback(resume_text, parsed_resume, jd_text, analysis_results)
                    
                    st.success("Analysis Complete!")
                    st.markdown("---")
                    
                    # --- RESULTS SECTION ---
                    st.header("📊 ATS Audit Scorecard")
                    
                    # Metrics Row
                    ats_score = analysis_results["ats_score"]
                    m1, m2, m3, m4, m5, m6 = st.columns(6)
                    m1.metric("Overall ATS Score", f"{ats_score}/100")
                    m2.metric("Keyword Density", f"{analysis_results['keyword_match_score']}%")
                    m3.metric("Skills Alignment", f"{analysis_results['skills_match_score']}%")
                    m4.metric("Experience Match", f"{analysis_results['experience_match_score']}%")
                    m5.metric("Education Match", f"{analysis_results['education_match_score']}%")
                    m6.metric("Semantic Match", f"{analysis_results['semantic_similarity_score']}%")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Score Breakdown Chart
                    st.subheader("📈 Score Breakdown")
                    categories = ["Keyword Density", "Skills Match", "Experience Match", "Education Match", "Semantic Match"]
                    scores_list = [
                        analysis_results['keyword_match_score'],
                        analysis_results['skills_match_score'],
                        analysis_results['experience_match_score'],
                        analysis_results['education_match_score'],
                        analysis_results['semantic_similarity_score']
                    ]
                    
                    fig, ax = plt.subplots(figsize=(8, 3))
                    bars = ax.barh(categories, scores_list, color='#4f46e5', height=0.55)
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.spines['bottom'].set_visible(False)
                    ax.spines['left'].set_color('#cccccc')
                    ax.xaxis.set_visible(False)
                    for bar in bars:
                        w = bar.get_width()
                        ax.text(w + 2, bar.get_y() + bar.get_height()/2, f'{int(w)}%', ha='left', va='center', fontweight='bold', color='#333333')
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    st.markdown("---")
                    
                    # Matched vs Missing Skills
                    s_col1, s_col2 = st.columns(2)
                    suggestions = analysis_results.get("suggestions", {})
                    matched = suggestions.get("matched_skills", [])
                    missing = suggestions.get("missing_skills", [])
                    
                    with s_col1:
                        st.subheader("✔ Matched Skills")
                        if matched:
                            for sk in matched:
                                st.success(f"✔ {sk}")
                        else:
                            st.info("No specific hard skill overlaps detected.")
                            
                    with s_col2:
                        st.subheader("✘ Missing Skills")
                        if missing:
                            for sk in missing:
                                st.error(f"✘ {sk}")
                        else:
                            st.success("No critical skill gaps identified!")

                    st.markdown("---")
                    
                    # AI Insights & Feedback
                    st.header("🤖 AI Insights & Strategic Guidance")
                    
                    st.subheader("Professional Alignment Summary")
                    st.write(ai_feedback.get("summary", "N/A"))
                    
                    fb_col1, fb_col2 = st.columns(2)
                    with fb_col1:
                        st.subheader("💪 Core Strengths")
                        for strg in ai_feedback.get("strengths", []):
                            st.markdown(f"- **{strg}**")
                    with fb_col2:
                        st.subheader("⚠️ Identified Gaps")
                        for weak in ai_feedback.get("weaknesses", []):
                            st.markdown(f"- **{weak}**")
                            
                    st.subheader("📌 Actionable Improvements")
                    for imp in suggestions.get("improvements", []):
                        st.info(f"• {imp}")
                        
                    st.subheader("✍️ Bullet Point Rewrite Examples")
                    rewrites = ai_feedback.get("rewrites", {})
                    if rewrites:
                        for k, v in rewrites.items():
                            orig = v.get("original") if isinstance(v, dict) else k
                            impr = v.get("improved") if isinstance(v, dict) else v
                            st.markdown(f"❌ **Original**: `{orig}`")
                            st.markdown(f"✔ **AI Improved**: `{impr}`")
                            st.markdown("---")
                    else:
                        st.write("No specific bullet rewrites required.")
                        
                    st.subheader("🎯 Career & Interview Roadmap")
                    st.write(ai_feedback.get("career_advice", "N/A"))

                    st.markdown("---")
                    
                    # Generate Downloadable Report
                    st.header("📥 Download Audit PDF Report")
                    
                    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "app", "reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    report_path = os.path.join(reports_dir, f"report_{uuid.uuid4().hex[:8]}.pdf")
                    
                    scores_dict = {
                        "ats_score": ats_score,
                        "keyword_match_score": analysis_results["keyword_match_score"],
                        "skills_match_score": analysis_results["skills_match_score"],
                        "experience_match_score": analysis_results["experience_match_score"],
                        "education_match_score": analysis_results["education_match_score"],
                        "semantic_similarity_score": analysis_results["semantic_similarity_score"]
                    }
                    
                    generate_pdf_report(
                        output_pdf_path=report_path,
                        applicant_name=parsed_resume.get("contact", {}).get("name", "Applicant"),
                        contact_info=parsed_resume.get("contact", {}),
                        scores=scores_dict,
                        suggestions=suggestions,
                        ai_feedback=ai_feedback
                    )
                    
                    if os.path.exists(report_path):
                        with open(report_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            
                        st.download_button(
                            label="📄 Download PDF Audit Report",
                            data=pdf_bytes,
                            file_name=f"ATS_Report_{parsed_resume.get('contact', {}).get('name', 'Applicant').replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )
                        
                        # Cleanup report file after buffer reading
                        try:
                            os.remove(report_path)
                        except:
                            pass

            finally:
                if os.path.exists(tmp_res_path):
                    os.remove(tmp_res_path)
