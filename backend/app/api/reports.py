"""
Report generation routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import datetime

from app.database import get_db
from app.models import User, Interview, CandidateResponse, TeamMembership, UserRole
from app.schemas import InterviewReport, CandidateReport, EvaluationRunAudit
from app.api.auth import get_current_user, require_role, UserRole
from app.services.evaluation_service import generate_employer_report, generate_candidate_report, generate_candidate_evaluation_audit

router = APIRouter()


def require_interview_membership(interview: Interview, user: User, db: Session) -> None:
    if user.role == UserRole.ADMIN:
        return

    membership = (
        db.query(TeamMembership)
        .filter(
            TeamMembership.user_id == user.id,
            TeamMembership.organization_id == interview.organization_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_candidate_report_access(response: CandidateResponse, user: User, db: Session) -> None:
    if user.email == response.candidate_email:
        return

    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_interview_membership(interview, user, db)


@router.get("/interview/{interview_id}", response_model=InterviewReport)
async def get_interview_report(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ranked candidate report for an interview (employer view)"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_interview_membership(interview, current_user, db)
    
    report = generate_employer_report(interview_id, db)
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not available")
    
    return report


@router.get("/candidate/{response_id}", response_model=CandidateReport)
async def get_candidate_report(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed report for a specific candidate response"""
    
    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    
    require_candidate_report_access(response, current_user, db)
    
    report = generate_candidate_report(response_id, db)
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not available")
    
    return report


@router.get("/candidate/{response_id}/evaluations", response_model=List[EvaluationRunAudit])
async def get_candidate_evaluation_audit(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get persisted evaluation run history and per-answer evidence for a response."""

    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()

    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_candidate_report_access(response, current_user, db)

    return generate_candidate_evaluation_audit(response_id, db)


@router.get("/interview/{interview_id}/pdf")
async def download_interview_report_pdf(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download interview report as PDF"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_interview_membership(interview, current_user, db)
    
    from app.services.report_service import generate_interview_pdf
    
    pdf_path = await generate_interview_pdf(interview_id, db)
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate PDF")
    
    return FileResponse(
        path=pdf_path,
        filename=f"interview_{interview_id}_report.pdf",
        media_type="application/pdf"
    )


@router.get("/candidate/{response_id}/pdf")
async def download_candidate_report_pdf(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download candidate report as PDF"""
    
    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    
    require_candidate_report_access(response, current_user, db)
    
    from app.services.report_service import generate_candidate_pdf
    
    pdf_path = await generate_candidate_pdf(response_id, db)
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate PDF")
    
    return FileResponse(
        path=pdf_path,
        filename=f"candidate_{response_id}_report.pdf",
        media_type="application/pdf"
    )


@router.get("/my-results", response_model=List[CandidateReport])
async def get_my_interview_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all interview results for current employee"""
    
    if current_user.role.value != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only for employees")
    
    responses = (
        db.query(CandidateResponse)
        .filter(
            CandidateResponse.candidate_email == current_user.email,
            CandidateResponse.status == "completed"
        )
        .all()
    )
    
    reports = []
    for response in responses:
        report = generate_candidate_report(response.id, db)
        if report:
            reports.append(report)
    
    return reports
