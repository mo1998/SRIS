"""
Data request routes for GDPR compliance - export and delete workflows
"""

import json
import os
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User, CandidateResponse, QuestionAnswer, EvaluationRun, EvaluationScore,
    DataExportRequest, DataRequestType, DataRequestStatus, TeamMembership, UserRole, Interview,
)
from app.schemas import DataExportRequestCreate, DataExportRequestProcess, DataExportRequestResponse
from app.api.auth import get_current_user
from app.services.audit_service import create_audit_log

router = APIRouter()
EXPORT_EXPIRY_DAYS = 7


def require_admin_or_employer(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.EMPLOYER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("/", response_model=DataExportRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_data_request(
    request_data: DataExportRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request data export or deletion for the current user's data."""
    if request_data.request_type.value == "delete":
        existing = (
            db.query(DataExportRequest)
            .filter(
                DataExportRequest.requester_email == current_user.email,
                DataExportRequest.request_type == DataRequestType.DELETE,
                DataExportRequest.status.in_([DataRequestStatus.PENDING, DataRequestStatus.PROCESSING]),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A pending delete request already exists for this account",
            )

    data_request = DataExportRequest(
        requester_email=current_user.email,
        request_type=DataRequestType(request_data.request_type.value),
        status=DataRequestStatus.PENDING,
    )
    db.add(data_request)
    db.commit()
    db.refresh(data_request)

    create_audit_log(
        db,
        actor=current_user,
        action=f"data_request.{request_data.request_type.value}_requested",
        target_type="data_export_request",
        target_id=data_request.id,
        details={"requester_email": current_user.email, "request_type": request_data.request_type.value},
    )

    return data_request


@router.get("/", response_model=List[DataExportRequestResponse])
async def list_data_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List data requests. Admins see all; employers see their organization's candidates."""
    require_admin_or_employer(current_user)

    if current_user.role == UserRole.ADMIN:
        return db.query(DataExportRequest).order_by(DataExportRequest.created_at.desc()).all()

    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == current_user.id)
        .first()
    )
    if not membership:
        return db.query(DataExportRequest).filter(
            DataExportRequest.requester_email == current_user.email,
        ).order_by(DataExportRequest.created_at.desc()).all()

    interviews = db.query(Interview).filter(Interview.organization_id == membership.organization_id).all()
    interview_ids = [i.id for i in interviews]
    candidate_emails = set()
    if interview_ids:
        candidate_emails.update(
            r[0] for r in db.query(CandidateResponse.candidate_email)
            .filter(CandidateResponse.interview_id.in_(interview_ids))
            .distinct().all()
        )
    candidate_emails.add(current_user.email)

    return (
        db.query(DataExportRequest)
        .filter(DataExportRequest.requester_email.in_(list(candidate_emails)))
        .order_by(DataExportRequest.created_at.desc())
        .all()
    )


@router.get("/{request_id}/download")
async def download_export(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download exported data for a completed export request."""
    data_request = db.query(DataExportRequest).filter(DataExportRequest.id == request_id).first()
    if not data_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if current_user.email != data_request.requester_email:
        require_admin_or_employer(current_user)

    if data_request.status != DataRequestStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Export not yet completed")

    if not data_request.file_path or not os.path.exists(data_request.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")

    return FileResponse(
        path=data_request.file_path,
        filename=f"export_{data_request.id}.json",
        media_type="application/json",
    )


@router.patch("/{request_id}", response_model=DataExportRequestResponse)
async def process_data_request(
    request_id: int,
    process_data: DataExportRequestProcess,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Process a data request (approve/reject). Admin or org owner only."""
    data_request = db.query(DataExportRequest).filter(DataExportRequest.id == request_id).first()
    if not data_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    require_admin_or_employer(current_user)

    new_status = DataRequestStatus(process_data.status.value)

    if new_status == DataRequestStatus.COMPLETED:
        if data_request.request_type == DataRequestType.EXPORT:
            file_path = generate_export_file(data_request, db)
            data_request.file_path = file_path
            data_request.expires_at = datetime.utcnow() + timedelta(days=EXPORT_EXPIRY_DAYS)
        elif data_request.request_type == DataRequestType.DELETE:
            delete_candidate_data(data_request, db)

    data_request.status = new_status
    data_request.processed_by = current_user.id
    data_request.processed_at = datetime.utcnow()
    data_request.details = json.dumps({"notes": process_data.notes}) if process_data.notes else data_request.details

    create_audit_log(
        db,
        actor=current_user,
        action=f"data_request.{data_request.request_type.value}_{new_status.value}",
        target_type="data_export_request",
        target_id=data_request.id,
        details={
            "requester_email": data_request.requester_email,
            "request_type": data_request.request_type.value,
            "new_status": new_status.value,
            "notes": process_data.notes,
        },
    )

    db.commit()
    db.refresh(data_request)
    return data_request


def generate_export_file(data_request: DataExportRequest, db: Session) -> str:
    """Generate a JSON export of all candidate data for the requester."""
    email = data_request.requester_email

    responses = db.query(CandidateResponse).filter(CandidateResponse.candidate_email == email).all()

    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "requester_email": email,
        "request_id": data_request.id,
        "responses": [],
    }

    for response in responses:
        interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
        answers = db.query(QuestionAnswer).filter(QuestionAnswer.response_id == response.id).all()
        evaluation_runs = db.query(EvaluationRun).filter(EvaluationRun.response_id == response.id).all()

        answer_list = []
        for answer in answers:
            question = answer.question
            scores = db.query(EvaluationScore).filter(EvaluationScore.question_answer_id == answer.id).all()
            answer_list.append({
                "question_id": answer.question_id,
                "question_text": question.question_text if question else None,
                "answer_text": answer.answer_text,
                "transcript": answer.transcript,
                "score": answer.score,
                "feedback": answer.feedback,
                "time_taken_seconds": answer.time_taken_seconds,
                "audio_file_path": answer.audio_file_path,
                "evaluation_scores": [
                    {
                        "score": s.score,
                        "feedback_en": s.feedback_en,
                        "feedback_ar": s.feedback_ar,
                    }
                    for s in scores
                ],
            })

        export_data["responses"].append({
            "interview_id": response.interview_id,
            "interview_title": interview.title if interview else "Unknown",
            "status": response.status,
            "total_score": response.total_score,
            "passed": response.passed,
            "started_at": response.started_at.isoformat() if response.started_at else None,
            "completed_at": response.completed_at.isoformat() if response.completed_at else None,
            "answers": answer_list,
            "evaluation_runs": [
                {
                    "provider": run.provider,
                    "provider_version": run.provider_version,
                    "model_name": run.model_name,
                    "status": run.status,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                }
                for run in evaluation_runs
            ],
        })

    os.makedirs("uploads/exports", exist_ok=True)
    file_path = f"uploads/exports/export_{data_request.id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    return file_path


def delete_candidate_data(data_request: DataExportRequest, db: Session) -> None:
    """Anonymize candidate data for a delete request."""
    email = data_request.requester_email

    responses = db.query(CandidateResponse).filter(CandidateResponse.candidate_email == email).all()
    for response in responses:
        for answer in response.question_answers:
            if answer.audio_file_path and os.path.exists(answer.audio_file_path):
                os.remove(answer.audio_file_path)
            answer.answer_text = "[Deleted per data request]"
            answer.audio_file_path = None
            answer.transcript = None

        response.candidate_name = "[Deleted]"
        response.candidate_email = f"deleted-{response.id}@anonymized.sris"
        response.emotion_timeline = None
        response.dominant_emotion = None
        response.confidence_score = None
        response.voice_quality_score = None
        response.background_quality_score = None
        response.face_visibility_score = None
        response.lighting_score = None
        response.total_score = None
        response.passed = None
