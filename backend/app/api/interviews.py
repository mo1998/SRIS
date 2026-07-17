"""
Interview management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import User, Interview, InterviewQuestion, InterviewStatus
from app.schemas import InterviewCreate, InterviewResponse, QuestionResponse
from app.api.auth import get_current_user, require_role, UserRole

router = APIRouter()


@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Create a new interview with questions"""
    
    interview = Interview(
        title=interview_data.title,
        description=interview_data.description,
        employer_id=current_user.id,
        duration_minutes=interview_data.duration_minutes,
        max_attempts=interview_data.max_attempts,
        pass_score=interview_data.pass_score
    )
    
    db.add(interview)
    db.flush()  # Get interview ID
    
    # Add questions
    for idx, q_data in enumerate(interview_data.questions):
        question = InterviewQuestion(
            interview_id=interview.id,
            question_text=q_data.question_text,
            expected_answer=q_data.expected_answer,
            question_type=q_data.question_type,
            options=q_data.options,
            weight=q_data.weight,
            order_index=q_data.order_index if q_data.order_index else idx
        )
        db.add(question)
    
    db.commit()
    db.refresh(interview)
    
    return interview


@router.get("/", response_model=List[InterviewResponse])
async def list_employer_interviews(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """List all interviews for current employer"""
    interviews = (
        db.query(Interview)
        .filter(Interview.employer_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return interviews


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview details"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    # Check permissions
    if current_user.role.value == "employer" and interview.employer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return interview


@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: int,
    title: str = None,
    description: str = None,
    duration_minutes: int = None,
    max_attempts: int = None,
    pass_score: float = None,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Update interview details"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    if interview.status != InterviewStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only update draft interviews")
    
    if title:
        interview.title = title
    if description is not None:
        interview.description = description
    if duration_minutes:
        interview.duration_minutes = duration_minutes
    if max_attempts:
        interview.max_attempts = max_attempts
    if pass_score:
        interview.pass_score = pass_score
    
    db.commit()
    db.refresh(interview)
    
    return interview


@router.post("/{interview_id}/activate", response_model=InterviewResponse)
async def activate_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Activate interview (make it available for candidates)"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    if interview.status != InterviewStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview must be in draft status")
    
    interview.status = InterviewStatus.ACTIVE
    db.commit()
    db.refresh(interview)
    
    return interview


@router.post("/{interview_id}/complete", response_model=InterviewResponse)
async def complete_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Complete interview (no more candidates can join)"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    interview.status = InterviewStatus.COMPLETED
    db.commit()
    db.refresh(interview)
    
    return interview


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Delete an interview"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    db.delete(interview)
    db.commit()


# Question management
@router.post("/{interview_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    interview_id: int,
    question_data: QuestionResponse,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Add a question to an interview"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    if interview.status != InterviewStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only add questions to draft interviews")
    
    question = InterviewQuestion(
        interview_id=interview_id,
        question_text=question_data.question_text,
        expected_answer=question_data.expected_answer,
        question_type=question_data.question_type,
        options=question_data.options,
        weight=question_data.weight,
        order_index=question_data.order_index
    )
    
    db.add(question)
    db.commit()
    db.refresh(question)
    
    return question


@router.get("/{interview_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all questions for an interview"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.order_index)
        .all()
    )
    
    return questions
