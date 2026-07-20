"""
PDF report generation service
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from xml.sax.saxutils import escape
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models import Interview, CandidateResponse, QuestionAnswer, InterviewQuestion, EvaluationRun, EvaluationScore


async def generate_interview_pdf(interview_id: int, db: Session) -> str:
    """Generate PDF report for an interview with all candidates"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        return ""
    
    responses = (
        db.query(CandidateResponse)
        .filter(
            CandidateResponse.interview_id == interview_id,
            CandidateResponse.status == "completed"
        )
        .order_by(CandidateResponse.total_score.desc())
        .all()
    )
    
    # Create PDF
    os.makedirs("uploads/reports", exist_ok=True)
    filename = f"uploads/reports/interview_{interview_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=HexColor('#2c3e50'),
        spaceAfter=10
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=HexColor('#34495e'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    # Title
    elements.append(Paragraph("Smart Remote Interview System", title_style))
    elements.append(Paragraph("Interview Report", heading_style))
    elements.append(Spacer(1, 20))
    
    # Interview details
    details_data = [
        ['Interview Title:', interview.title],
        ['Status:', interview.status.value],
        ['Duration:', f'{interview.duration_minutes} minutes'],
        ['Pass Score:', f'{interview.pass_score}%'],
        ['Total Candidates:', str(len(responses))],
        ['Generated:', datetime.utcnow().strftime('%B %d, %Y %I:%M %p')]
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 4*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2c3e50')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 30))
    
    # Statistics
    if responses:
        avg_score = sum(r.total_score or 0.0 for r in responses) / len(responses)
        pass_count = sum(1 for r in responses if r.passed)
        pass_rate = (pass_count / len(responses)) * 100
    else:
        avg_score = 0
        pass_count = 0
        pass_rate = 0
    
    elements.append(Paragraph("Summary Statistics", heading_style))
    
    stats_data = [
        ['Average Score:', f'{avg_score:.1f}%'],
        ['Pass Rate:', f'{pass_rate:.1f}%'],
        ['Passed Candidates:', f'{pass_count}/{len(responses)}']
    ]
    
    stats_table = Table(stats_data, colWidths=[2*inch, 4*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 30))
    
    # Candidate Rankings
    elements.append(Paragraph("Candidate Rankings", heading_style))
    
    # Table header
    ranking_data = [['Rank', 'Name', 'Email', 'Score', 'Status', 'Evaluation Agent']]
    
    for idx, response in enumerate(responses, 1):
        evaluation_run = get_latest_completed_evaluation_run(response.id, db)
        evaluation_agent = 'N/A'
        if evaluation_run:
            evaluation_agent = f'{evaluation_run.provider or "N/A"} / {evaluation_run.model_name or "N/A"}'

        ranking_data.append([
            str(idx),
            response.candidate_name,
            response.candidate_email,
            f'{response.total_score or 0:.1f}%',
            'PASSED' if response.passed else 'FAILED',
            evaluation_agent
        ])
    
    ranking_table = Table(ranking_data, colWidths=[0.5*inch, 1.2*inch, 1.8*inch, 0.8*inch, 0.8*inch, 1.9*inch])
    ranking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f8f9fa')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (5, -1), 'CENTER'),
    ]))
    
    elements.append(ranking_table)
    elements.append(Spacer(1, 20))
    
    # Quality metrics
    elements.append(Paragraph("Quality Metrics Summary", heading_style))
    
    if responses:
        avg_voice = sum(r.voice_quality_score or 0 for r in responses) / len(responses)
        avg_background = sum(r.background_quality_score or 0 for r in responses) / len(responses)
        avg_face = sum(r.face_visibility_score or 0 for r in responses) / len(responses)
        avg_lighting = sum(r.lighting_score or 0 for r in responses) / len(responses)
        
        quality_data = [
            ['Average Voice Quality:', f'{avg_voice:.1f}%'],
            ['Average Background Quality:', f'{avg_background:.1f}%'],
            ['Average Face Visibility:', f'{avg_face:.1f}%'],
            ['Average Lighting:', f'{avg_lighting:.1f}%']
        ]
        
        quality_table = Table(quality_data, colWidths=[2*inch, 4*inch])
        quality_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
        ]))
        
        elements.append(quality_table)
    
    doc.build(elements)
    
    return filename


async def generate_candidate_pdf(response_id: int, db: Session) -> str:
    """Generate PDF report for a specific candidate"""
    
    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not response:
        return ""
    
    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    answers = db.query(QuestionAnswer).filter(QuestionAnswer.response_id == response_id).all()
    evaluation_run = get_latest_completed_evaluation_run(response_id, db)
    scores_by_answer_id = get_evaluation_scores_by_answer_id(evaluation_run.id, db) if evaluation_run else {}
    
    # Create PDF
    os.makedirs("uploads/reports", exist_ok=True)
    filename = f"uploads/reports/candidate_{response_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    doc = SimpleDocTemplate(filename, pagesize=letter, pageCompression=0)
    styles = getSampleStyleSheet()
    elements = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=HexColor('#2c3e50'),
        spaceAfter=10
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=HexColor('#34495e'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    # Title
    elements.append(Paragraph("Smart Remote Interview System", title_style))
    elements.append(Paragraph("Candidate Performance Report", heading_style))
    elements.append(Spacer(1, 20))
    
    # Candidate details
    details_data = [
        ['Candidate Name:', response.candidate_name],
        ['Candidate Email:', response.candidate_email],
        ['Interview:', interview.title if interview else 'N/A'],
        ['Completed:', (response.completed_at or datetime.utcnow()).strftime('%B %d, %Y %I:%M %p')]
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 4*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2c3e50')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 30))
    
    # Overall Results
    elements.append(Paragraph("Overall Results", heading_style))
    
    result_color = '#27ae60' if response.passed else '#e74c3c'
    result_text = 'PASSED' if response.passed else 'FAILED'
    
    results_data = [
        ['Total Score:', f'{response.total_score or 0:.1f}%'],
        ['Result:', result_text],
        ['Confidence Score:', f'{response.confidence_score or 50:.1f}%'],
        ['Dominant Emotion:', (response.dominant_emotion or 'neutral').title()]
    ]
    
    results_table = Table(results_data, colWidths=[2*inch, 4*inch])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
        ('TEXTCOLOR', (1, 1), (1, 1), HexColor(result_color)),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
    ]))
    
    elements.append(results_table)
    elements.append(Spacer(1, 20))

    if evaluation_run:
        elements.append(Paragraph("Evaluation Agent", heading_style))

        evaluation_data = [
            ['Provider:', evaluation_run.provider or 'N/A'],
            ['Model:', evaluation_run.model_name or 'N/A'],
            ['Status:', evaluation_run.status or 'N/A'],
            ['Completed:', (evaluation_run.completed_at or datetime.utcnow()).strftime('%B %d, %Y %I:%M %p')]
        ]

        evaluation_table = Table(evaluation_data, colWidths=[2*inch, 4*inch])
        evaluation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
        ]))

        elements.append(evaluation_table)
        elements.append(Spacer(1, 20))
    
    # Quality Metrics
    elements.append(Paragraph("Environment Quality Metrics", heading_style))
    
    quality_data = [
        ['Voice Quality:', f'{response.voice_quality_score or 0:.1f}%'],
        ['Background Quality:', f'{response.background_quality_score or 0:.1f}%'],
        ['Face Visibility:', f'{response.face_visibility_score or 0:.1f}%'],
        ['Lighting:', f'{response.lighting_score or 0:.1f}%']
    ]
    
    quality_table = Table(quality_data, colWidths=[2*inch, 4*inch])
    quality_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
    ]))
    
    elements.append(quality_table)
    elements.append(Spacer(1, 30))
    
    # Question-by-Question Breakdown
    elements.append(Paragraph("Question-by-Question Breakdown", heading_style))
    
    for idx, answer in enumerate(answers, 1):
        question = db.query(InterviewQuestion).filter(InterviewQuestion.id == answer.question_id).first()
        evaluation_score = scores_by_answer_id.get(answer.id)
        
        if question:
            elements.append(Paragraph(f"Question {idx}: {question.question_text}", 
                                     ParagraphStyle('Q', parent=styles['Heading3'], fontSize=12, spaceBefore=15)))
            
            answer_data = [
                ['Your Answer:', as_pdf_paragraph(answer.answer_text or 'No answer provided', styles)],
                ['Score:', f'{answer.score or 0:.1f}%'],
                ['Feedback:', as_pdf_paragraph(evaluation_score.feedback_en or answer.feedback or '', styles) if evaluation_score else as_pdf_paragraph(answer.feedback or '', styles)]
            ]

            if evaluation_score and evaluation_score.feedback_ar:
                answer_data.append(['Arabic Feedback:', as_pdf_paragraph(evaluation_score.feedback_ar, styles)])

            if evaluation_score:
                evidence_lines = format_evaluation_evidence(evaluation_score.evidence_json)
                if evidence_lines:
                    answer_data.append(['Evaluation Evidence:', as_pdf_paragraph('<br/>'.join(evidence_lines), styles, already_escaped=True)])
            
            answer_table = Table(answer_data, colWidths=[1.5*inch, 4.5*inch])
            answer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(answer_table)
            elements.append(Spacer(1, 15))
    
    # Feedback section
    elements.append(Paragraph("Overall Feedback", heading_style))
    
    feedback_text = "Thank you for completing the interview. Your performance has been evaluated across multiple dimensions including answer quality, communication clarity, and professional presentation. The employer will review your results and contact you if you move forward in the selection process."
    
    elements.append(Paragraph(feedback_text, ParagraphStyle('Feedback', parent=styles['Normal'], fontSize=10, spaceBefore=10)))
    
    doc.build(elements)
    
    return filename


def get_latest_completed_evaluation_run(response_id: int, db: Session) -> Optional[EvaluationRun]:
    return (
        db.query(EvaluationRun)
        .filter(EvaluationRun.response_id == response_id, EvaluationRun.status == "completed")
        .order_by(EvaluationRun.completed_at.desc(), EvaluationRun.id.desc())
        .first()
    )


def get_evaluation_scores_by_answer_id(evaluation_run_id: int, db: Session) -> Dict[int, EvaluationScore]:
    scores = db.query(EvaluationScore).filter(EvaluationScore.evaluation_run_id == evaluation_run_id).all()
    return {score.question_answer_id: score for score in scores}


def format_evaluation_evidence(evidence_json: str) -> List[str]:
    if not evidence_json:
        return []

    try:
        evidence = json.loads(evidence_json)
    except json.JSONDecodeError:
        return [escape(evidence_json)]

    lines = []
    matched = evidence.get("matched_criteria") or evidence.get("matched_keywords") or []
    missing = evidence.get("missing_criteria") or evidence.get("missing_keywords") or []

    if matched:
        lines.append(f"<b>Matched:</b> {escape(', '.join(str(item) for item in matched))}")
    if missing:
        lines.append(f"<b>Missing:</b> {escape(', '.join(str(item) for item in missing))}")
    if evidence.get("evidence"):
        lines.append(f"<b>Evidence:</b> {escape(str(evidence['evidence']))}")
    if evidence.get("provider_fallback_from"):
        lines.append(f"<b>Fallback:</b> {escape(str(evidence['provider_fallback_from']))}")

    return lines


def as_pdf_paragraph(value: str, styles, already_escaped: bool = False) -> Paragraph:
    text = value if already_escaped else escape(value)
    return Paragraph(text, ParagraphStyle('CellBody', parent=styles['Normal'], fontSize=9, leading=11))
