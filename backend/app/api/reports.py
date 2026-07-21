"""
Report generation routes
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import datetime

from app.database import get_db
from app.models import User, Interview, CandidateResponse, TeamMembership, TeamRole, UserRole
from app.schemas import InterviewReport, CandidateReport, EmailHealth, EvaluationAnalytics, EvaluationHealth, EvaluationRunAudit
from app.api.auth import get_current_user, require_role, UserRole
from app.services.evaluation_service import generate_employer_report, generate_candidate_report, generate_candidate_evaluation_audit, generate_interview_evaluation_analytics, get_evaluation_health
from app.services.email_service import get_email_health

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


def require_candidate_evaluation_management(response: CandidateResponse, user: User, db: Session) -> None:
    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_evaluation_management_membership(interview, user, db)


def require_evaluation_management_membership(interview: Interview, user: User, db: Session) -> None:
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
    if not membership or membership.role not in {TeamRole.OWNER, TeamRole.ADMIN, TeamRole.RECRUITER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient evaluation permissions")


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


@router.get("/evaluation/health", response_model=EvaluationHealth)
async def get_evaluation_provider_health(
    current_user: User = Depends(get_current_user)
):
    """Get local evaluation provider health and fallback status."""
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return await get_evaluation_health()


@router.get("/email/health", response_model=EmailHealth)
async def get_email_configuration_health(
    current_user: User = Depends(get_current_user)
):
    """Get email configuration readiness without sending a message."""
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return get_email_health()


@router.post("/interview/{interview_id}/evaluations", response_model=List[EvaluationRunAudit])
async def reevaluate_interview_responses(
    interview_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Queue fresh evaluations for every completed response in an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_evaluation_management_membership(interview, current_user, db)

    responses = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.interview_id == interview_id, CandidateResponse.status == "completed")
        .all()
    )
    if not responses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No completed responses to re-evaluate")

    from app.services.evaluation_service import create_evaluation_run, enqueue_evaluation_run

    queued_runs = []
    for response in responses:
        if not response.question_answers:
            continue
        evaluation_run = create_evaluation_run(response.id, db)
        queued_runs.append(evaluation_run)

    if not queued_runs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No completed responses with answers to re-evaluate")

    db.commit()
    for run in queued_runs:
        enqueue_evaluation_run(run.response_id, run.id, background_tasks)

    return [generate_candidate_evaluation_audit(run.response_id, db)[0] for run in queued_runs]


@router.get("/interview/{interview_id}/evaluation-analytics", response_model=EvaluationAnalytics)
async def get_interview_evaluation_analytics(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation analytics for completed responses in an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_interview_membership(interview, current_user, db)

    return generate_interview_evaluation_analytics(interview_id, db)


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


@router.post("/candidate/{response_id}/evaluations", response_model=EvaluationRunAudit)
async def reevaluate_candidate_response(
    response_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run a fresh evaluation for a completed response and persist a new audit run."""

    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()

    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_candidate_evaluation_management(response, current_user, db)

    if response.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only completed responses can be re-evaluated")

    if not response.question_answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Response has no answers to evaluate")

    from app.services.evaluation_service import create_evaluation_run, enqueue_evaluation_run

    evaluation_run = create_evaluation_run(response_id, db)
    db.commit()
    enqueue_evaluation_run(response_id, evaluation_run.id, background_tasks)
    audit_runs = generate_candidate_evaluation_audit(response_id, db)

    return audit_runs[0]


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
