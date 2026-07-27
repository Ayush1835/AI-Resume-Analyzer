import os
import uuid
import matplotlib
# Use Agg backend for matplotlib to avoid GUI thread errors in background tasks
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Any
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_analysis_chart(scores: Dict[str, int], output_path: str) -> str:
    """Generate a high-quality matplotlib horizontal bar chart for the PDF."""
    categories = list(scores.keys())
    values = list(scores.values())
    
    # Capitalize category labels
    categories = [cat.replace('_', ' ').title() for cat in categories]
    
    # Modern professional colors matching frontend theme (deep purples and blues)
    bar_colors = []
    for val in values:
        if val >= 75:
            bar_colors.append('#0d6efd')  # Neo blue
        elif val >= 50:
            bar_colors.append('#fd7e14')  # Warning Orange
        else:
            bar_colors.append('#dc3545')  # Error Red
            
    fig, ax = plt.subplots(figsize=(6, 2.8))
    
    # Render horizontal bars
    bars = ax.barh(categories, values, color=bar_colors, height=0.5)
    
    # Styling details
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.xaxis.set_visible(False)
    ax.tick_params(axis='y', colors='#555555', labelsize=10)
    
    # Adding data labels inside/outside bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 2, bar.get_y() + bar.get_height()/2, f'{int(width)}%', 
                ha='left', va='center', color='#333333', fontweight='bold', fontsize=9)
                
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, transparent=True)
    plt.close()
    return output_path

def generate_pdf_report(
    output_pdf_path: str,
    applicant_name: str,
    contact_info: Dict[str, str],
    scores: Dict[str, int],
    suggestions: Dict[str, Any],
    ai_feedback: Dict[str, Any]
) -> str:
    """Compile and generate the ReportLab PDF document."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    # Temporary chart path
    temp_chart_dir = os.path.dirname(output_pdf_path)
    temp_chart_path = os.path.join(temp_chart_dir, f"temp_chart_{uuid.uuid4().hex}.png")
    
    # Gather breakdown scores for chart
    breakdown_scores = {
        "Keywords": scores.get("keyword_match_score", 0),
        "Skills": scores.get("skills_match_score", 0),
        "Experience": scores.get("experience_match_score", 0),
        "Education": scores.get("education_match_score", 0),
        "Semantics": scores.get("semantic_similarity_score", 0),
    }
    
    # Generate the chart
    generate_analysis_chart(breakdown_scores, temp_chart_path)
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#212529'),
        alignment=TA_LEFT
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#6c757d'),
        alignment=TA_LEFT
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0d6efd'),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6
    )
    
    bullet_text = ParagraphStyle(
        'BulletTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#333333'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    score_badge_style = ParagraphStyle(
        'ScoreBadge',
        fontName='Helvetica-Bold',
        fontSize=36,
        leading=40,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    
    score_label_style = ParagraphStyle(
        'ScoreLabel',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    
    story = []
    
    # --- HEADER SECTION ---
    header_data = [
        [
            Paragraph(f"<b>{applicant_name}</b><br/>"
                      f"Email: {contact_info.get('email', 'N/A')}<br/>"
                      f"Phone: {contact_info.get('phone', 'N/A')}", subtitle_style),
            Paragraph("<b>AI RESUME AUDIT REPORT</b><br/>"
                      f"Date: {datetime.now().strftime('%Y-%m-%d')}<br/>"
                      "Powered by AI Resume Analyzer", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[270, 270])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#dee2e6')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # --- ATS SCORE SHOWCASE & METRIC PLOT ---
    ats_val = scores.get("ats_score", 0)
    badge_bg = '#0d6efd'  # Greenish/Blueish
    if ats_val < 50:
        badge_bg = '#dc3545'  # Red
    elif ats_val < 75:
        badge_bg = '#fd7e14'  # Orange
        
    badge_data = [
        [Paragraph(f"{ats_val}", score_badge_style)],
        [Paragraph("ATS SCORE", score_label_style)]
    ]
    badge_table = Table(badge_data, colWidths=[120])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(badge_bg)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 12),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    
    summary_txt = ai_feedback.get("summary", "No AI analysis performed.")
    summary_paragraph = Paragraph(f"<b>Professional Evaluation:</b><br/>{summary_txt}", body_text)
    
    # Layout Table combining Badge, Summary, and Chart
    layout_data = [
        [badge_table, summary_paragraph]
    ]
    layout_table = Table(layout_data, colWidths=[140, 400])
    layout_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('RIGHTPADDING', (0,0), (0,0), 15),
    ]))
    story.append(layout_table)
    story.append(Spacer(1, 15))
    
    # --- CHART AND METRICS TABLE ---
    chart_img = Image(temp_chart_path, width=280, height=130)
    chart_img.hAlign = 'LEFT'
    
    # Detail breakdown cells
    breakdown_data = [
        [Paragraph("<b>Category</b>", body_text), Paragraph("<b>Score</b>", body_text)],
        [Paragraph("Keyword Matching", body_text), Paragraph(f"{scores.get('keyword_match_score', 0)}%", body_text)],
        [Paragraph("Skills Match", body_text), Paragraph(f"{scores.get('skills_match_score', 0)}%", body_text)],
        [Paragraph("Experience Match", body_text), Paragraph(f"{scores.get('experience_match_score', 0)}%", body_text)],
        [Paragraph("Education Match", body_text), Paragraph(f"{scores.get('education_match_score', 0)}%", body_text)],
        [Paragraph("Semantic Similarity", body_text), Paragraph(f"{scores.get('semantic_similarity_score', 0)}%", body_text)]
    ]
    breakdown_table = Table(breakdown_data, colWidths=[140, 80])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    chart_layout_data = [
        [chart_img, breakdown_table]
    ]
    chart_layout = Table(chart_layout_data, colWidths=[300, 240])
    chart_layout.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (1,0), (1,0), 15),
    ]))
    story.append(chart_layout)
    story.append(Spacer(1, 15))
    
    # --- SKILLS ANALYSIS SECTION ---
    story.append(Paragraph("Skills Alignment", section_heading))
    matched_skills = suggestions.get("matched_skills", [])
    missing_skills = suggestions.get("missing_skills", [])
    
    matched_skills_p = [Paragraph(f"✔ {skill}", body_text) for skill in matched_skills]
    missing_skills_p = [Paragraph(f"✘ {skill}", body_text) for skill in missing_skills]
    
    # Format skills into table format
    skills_table_data = [
        [Paragraph("<b>Matched Skills</b>", body_text), Paragraph("<b>Missing Skills</b>", body_text)],
        [
            matched_skills_p if matched_skills_p else [Paragraph("No matched skills identified.", body_text)],
            missing_skills_p if missing_skills_p else [Paragraph("No missing skills identified.", body_text)]
        ]
    ]
    skills_table = Table(skills_table_data, colWidths=[260, 260])
    skills_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8f9fa')),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,1), (-1,-1), 6),
    ]))
    
    story.append(skills_table)
    story.append(Spacer(1, 15))
    
    # --- IMPROVEMENT RECOMMENDATIONS ---
    story.append(Paragraph("Improvement Recommendations", section_heading))
    improvements = suggestions.get("improvements", [])
    for imp in improvements:
        story.append(Paragraph(f"• {imp}", bullet_text))
    story.append(Spacer(1, 15))
    
    # --- AI FEEDBACK: STRENGTHS, WEAKNESSES & ADVICE ---
    strengths = ai_feedback.get("strengths", [])
    weaknesses = ai_feedback.get("weaknesses", [])
    advice = ai_feedback.get("career_advice", "")
    
    ai_story = []
    ai_story.append(Paragraph("AI-Generated Strategic Feedback", section_heading))
    
    if strengths:
        ai_story.append(Paragraph("<b>Core Strengths</b>", body_text))
        for strg in strengths:
            ai_story.append(Paragraph(f"✔ {strg}", bullet_text))
        ai_story.append(Spacer(1, 8))
            
    if weaknesses:
        ai_story.append(Paragraph("<b>Identified Gaps</b>", body_text))
        for weak in weaknesses:
            ai_story.append(Paragraph(f"✘ {weak}", bullet_text))
        ai_story.append(Spacer(1, 8))
            
    if advice:
        ai_story.append(Paragraph("<b>Career & Interview Roadmap</b>", body_text))
        ai_story.append(Paragraph(advice, body_text))
        
    story.append(KeepTogether(ai_story))
    
    # Build Document
    try:
        doc.build(story)
    finally:
        # Clean up temporary chart file safely
        if os.path.exists(temp_chart_path):
            try:
                os.remove(temp_chart_path)
            except OSError:
                pass
                
    return output_pdf_path
