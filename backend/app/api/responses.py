"""
Candidate response routes - submitting answers, quality checks
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import uuid

from app.database import get_db
from app.config import settings
from app.models import User, Interview, InterviewQuestion, InterviewStatus, Invitation, InvitationStatus, CandidateResponse, QuestionAnswer, TeamMembership, TeamRole, UserRole
from app.schemas import CandidateResponseCreate, CandidateResponseSummary, QuestionAnswerSchema, QualityCheckResult
from app.api.auth import get_current_user, require_role

router = APIRouter()

RESPONSE_MANAGER_ROLES = {TeamRole.OWNER, TeamRole.ADMIN, TeamRole.RECRUITER}


def validate_audio_filename(filename: str) -> str:
    extension = os.path.splitext(filename or "")[1].lower()
    if extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio file type",
        )
    return extension


def validate_audio_size(content: bytes) -> None:
    if len(content) > settings.MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds maximum size",
        )


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


def require_response_access(response: CandidateResponse, user: User, db: Session) -> None:
    if user.email == response.candidate_email:
        return

    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_interview_membership(interview, user, db)


def require_response_management(response: CandidateResponse, user: User, db: Session) -> None:
    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
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
    if not membership or membership.role not in RESPONSE_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient response management permissions")


def delete_answer_audio_files(response: CandidateResponse) -> None:
    for answer in response.question_answers:
        if answer.audio_file_path and os.path.exists(answer.audio_file_path):
            os.remove(answer.audio_file_path)


@router.post("/", response_model=CandidateResponseSummary, status_code=status.HTTP_201_CREATED)
async def start_interview_response(
    response_data: CandidateResponseCreate,
    db: Session = Depends(get_db)
):
    """Start a new interview response (called when candidate begins interview)"""
    
    # Verify interview exists and is active
    interview = db.query(Interview).filter(
        Interview.id == response_data.interview_id,
        Interview.status == InterviewStatus.ACTIVE
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found or not active")
    
    # Verify invitation if token provided
    invitation_id = None
    if response_data.invitation_token:
        invitation = db.query(Invitation).filter(
            Invitation.unique_token == response_data.invitation_token,
            Invitation.interview_id == response_data.interview_id
        ).first()
        
        if not invitation:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invitation token")
        
        if invitation.status == InvitationStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation has already been used")

        if invitation.status == InvitationStatus.REVOKED:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has been revoked")
        
        if invitation.expires_at and datetime.utcnow() > invitation.expires_at:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")
        
        invitation_id = invitation.id
        invitation.status = InvitationStatus.ACCEPTED
    
    # Check if candidate already has a response
    existing_response = db.query(CandidateResponse).filter(
        CandidateResponse.interview_id == response_data.interview_id,
        CandidateResponse.candidate_email == response_data.candidate_email
    ).first()
    
    if existing_response and existing_response.status == "completed":
        # Check max attempts
        if existing_response.interview.max_attempts and \
           db.query(CandidateResponse).filter(
               CandidateResponse.interview_id == response_data.interview_id,
               CandidateResponse.candidate_email == response_data.candidate_email,
               CandidateResponse.status == "completed"
           ).count() >= existing_response.interview.max_attempts:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum attempts reached")
    
    # Create response
    candidate_response = CandidateResponse(
        interview_id=response_data.interview_id,
        candidate_email=response_data.candidate_email,
        candidate_name=response_data.candidate_name,
        invitation_id=invitation_id,
        status="in_progress",
        started_at=datetime.utcnow()
    )
    
    db.add(candidate_response)
    db.commit()
    db.refresh(candidate_response)
    
    return candidate_response


@router.post("/{response_id}/answer", response_model=QuestionAnswerSchema)
async def submit_answer(
    response_id: int,
    question_id: int,
    answer_text: str,
    audio_file: Optional[UploadFile] = File(None),
    time_taken_seconds: int = None,
    db: Session = Depends(get_db)
):
    """Submit an answer to a question"""
    
    # Verify response exists and is in progress
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    
    if candidate_response.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Response is not in progress")
    
    # Verify question belongs to interview
    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == question_id,
        InterviewQuestion.interview_id == candidate_response.interview_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    
    # Save audio file if provided
    audio_path = None
    if audio_file:
        validate_audio_filename(audio_file.filename)
        content = await audio_file.read()
        validate_audio_size(content)

        os.makedirs("uploads/interviews/audio", exist_ok=True)
        audio_filename = f"{uuid.uuid4()}_{audio_file.filename}"
        audio_path = f"uploads/interviews/audio/{audio_filename}"
        
        with open(audio_path, "wb") as f:
            f.write(content)
    
    # Create answer
    answer = QuestionAnswer(
        response_id=response_id,
        question_id=question_id,
        answer_text=answer_text,
        audio_file_path=audio_path,
        time_taken_seconds=time_taken_seconds
    )
    
    db.add(answer)
    db.commit()
    db.refresh(answer)
    
    return answer


@router.post("/{response_id}/quality", response_model=QualityCheckResult)
async def submit_quality_metrics(
    response_id: int,
    voice_quality: float,
    background_quality: float,
    face_visibility: float,
    lighting: float,
    recommendations: List[str] = [],
    db: Session = Depends(get_db)
):
    """Submit quality metrics from client-side analysis"""
    
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    
    # Update quality metrics
    candidate_response.voice_quality_score = voice_quality
    candidate_response.background_quality_score = background_quality
    candidate_response.face_visibility_score = face_visibility
    candidate_response.lighting_score = lighting
    
    db.commit()
    
    overall = (voice_quality + background_quality + face_visibility + lighting) / 4.0
    
    return QualityCheckResult(
        voice_quality=voice_quality,
        background_quality=background_quality,
        face_visibility=face_visibility,
        lighting=lighting,
        overall_score=overall,
        recommendations=recommendations
    )


@router.post("/{response_id}/emotion")
async def submit_emotion_data(
    response_id: int,
    emotion: str,
    confidence: float,
    timeline: List[dict] = None,
    db: Session = Depends(get_db)
):
    """Submit emotion detection data"""
    
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    
    # Update emotion data
    candidate_response.dominant_emotion = emotion
    candidate_response.confidence_score = confidence
    
    if timeline:
        import json
        candidate_response.emotion_timeline = json.dumps(timeline)
    
    db.commit()
    
    return {"message": "Emotion data updated"}


@router.post("/{response_id}/complete", response_model=CandidateResponseSummary)
async def complete_interview_response(
    response_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Mark interview response as complete and trigger evaluation"""
    
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    
    if candidate_response.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Response is not in progress")
    
    # Update status
    candidate_response.status = "completed"
    candidate_response.completed_at = datetime.utcnow()
    
    # Update invitation status if applicable
    if candidate_response.invitation_id:
        invitation = db.query(Invitation).filter(Invitation.id == candidate_response.invitation_id).first()
        if invitation:
            invitation.status = InvitationStatus.COMPLETED
    
    db.commit()
    db.refresh(candidate_response)
    
    from app.services.evaluation_service import create_evaluation_run, enqueue_evaluation_run

    evaluation_run = create_evaluation_run(response_id, db)
    db.commit()
    enqueue_evaluation_run(response_id, evaluation_run.id, background_tasks)
    
    return candidate_response


@router.get("/interview/{interview_id}", response_model=List[CandidateResponseSummary])
async def list_interview_responses(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all responses for an interview (employer only)"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    require_interview_membership(interview, current_user, db)
    
    responses = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.interview_id == interview_id)
        .all()
    )
    
    return responses


@router.get("/{response_id}", response_model=CandidateResponseSummary)
async def get_response_details(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed response information"""
    
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_response_access(candidate_response, current_user, db)
    
    return candidate_response


@router.delete("/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_response(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a candidate response and associated evaluation/report data."""

    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()

    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_response_management(candidate_response, current_user, db)
    delete_answer_audio_files(candidate_response)
    db.delete(candidate_response)
    db.commit()
