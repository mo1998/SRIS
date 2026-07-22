"""
Transcript review and management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User, CandidateResponse, QuestionAnswer, TeamMembership, TeamRole, UserRole
from app.schemas import TranscriptUpdate
from app.api.auth import get_current_user

router = APIRouter()


def require_transcript_management(response: CandidateResponse, user: User, db: Session) -> None:
    interview = response.interview
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

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
    if not membership or membership.role not in {TeamRole.OWNER, TeamRole.ADMIN, TeamRole.RECRUITER, TeamRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.put("/{response_id}/answers/{question_id}/transcript", response_model=dict)
async def update_answer_transcript(
    response_id: int,
    question_id: int,
    transcript_data: TranscriptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update/review the transcript for a specific answer."""
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_transcript_management(candidate_response, current_user, db)

    answer = (
        db.query(QuestionAnswer)
        .filter(
            QuestionAnswer.response_id == response_id,
            QuestionAnswer.question_id == question_id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    answer.transcript = transcript_data.transcript
    answer.transcript_updated_at = datetime.utcnow()
    db.commit()

    return {
        "response_id": response_id,
        "question_id": question_id,
        "transcript": answer.transcript,
        "updated_at": answer.transcript_updated_at,
    }


@router.get("/{response_id}/answers/{question_id}/transcript", response_model=dict)
async def get_answer_transcript(
    response_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the transcript for a specific answer."""
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    interview = candidate_response.interview
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if current_user.email != candidate_response.candidate_email:
        require_transcript_management(candidate_response, current_user, db)

    answer = (
        db.query(QuestionAnswer)
        .filter(
            QuestionAnswer.response_id == response_id,
            QuestionAnswer.question_id == question_id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    return {
        "response_id": response_id,
        "question_id": question_id,
        "transcript": answer.transcript,
        "updated_at": answer.transcript_updated_at,
    }
