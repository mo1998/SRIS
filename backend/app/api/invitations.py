"""
Invitation management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import uuid
import os

from app.database import get_db
from app.models import User, Interview, Invitation, InvitationStatus, InterviewStatus
from app.schemas import InvitationCreate, InvitationResponse
from app.api.auth import get_current_user, require_role, UserRole
from app.config import settings
from app.services.email_service import send_invitation_email

router = APIRouter()


def generate_unique_token() -> str:
    """Generate a unique invitation token"""
    return str(uuid.uuid4())


@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: InvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: Session = Depends(get_db)
):
    """Create an invitation for a candidate"""
    
    # Verify interview exists and belongs to employer
    interview = db.query(Interview).filter(
        Interview.id == invitation_data.interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    if interview.status != InterviewStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview must be active")
    
    # Check if invitation already exists
    existing = db.query(Invitation).filter(
        Invitation.interview_id == invitation_data.interview_id,
        Invitation.candidate_email == invitation_data.candidate_email
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate already invited")
    
    # Create invitation
    token = generate_unique_token()
    expires_at = datetime.utcnow() + timedelta(days=7)  # Valid for 7 days
    
    invitation = Invitation(
        interview_id=invitation_data.interview_id,
        candidate_email=invitation_data.candidate_email,
        candidate_name=invitation_data.candidate_name,
        unique_token=token,
        status=InvitationStatus.PENDING,
        expires_at=expires_at
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # Send email in background
    interview_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/interview/{token}"
    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation_data.candidate_email,
        candidate_name=invitation_data.candidate_name,
        interview_title=interview.title,
        interview_link=interview_link,
        expires_at=expires_at
    )
    
    return invitation


@router.post("/bulk", response_model=List[InvitationResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_invitations(
    invitations: List[InvitationCreate],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: Session = Depends(get_db)
):
    """Create multiple invitations at once"""
    
    if not invitations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No invitations provided")
    
    # Verify interview exists and belongs to employer
    interview_id = invitations[0].interview_id
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    if interview.status != InterviewStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview must be active")
    
    created_invitations = []
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    for inv_data in invitations:
        # Check if invitation already exists
        existing = db.query(Invitation).filter(
            Invitation.interview_id == interview_id,
            Invitation.candidate_email == inv_data.candidate_email
        ).first()
        
        if existing:
            continue  # Skip duplicates
        
        token = generate_unique_token()
        
        invitation = Invitation(
            interview_id=interview_id,
            candidate_email=inv_data.candidate_email,
            candidate_name=inv_data.candidate_name,
            unique_token=token,
            status=InvitationStatus.PENDING,
            expires_at=expires_at
        )
        
        db.add(invitation)
        created_invitations.append(invitation)
        
        # Send email in background
        interview_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/interview/{token}"
        background_tasks.add_task(
            send_invitation_email,
            to_email=inv_data.candidate_email,
            candidate_name=inv_data.candidate_name,
            interview_title=interview.title,
            interview_link=interview_link,
            expires_at=expires_at
        )
    
    db.commit()
    
    for inv in created_invitations:
        db.refresh(inv)
    
    return created_invitations


@router.get("/{interview_id}", response_model=List[InvitationResponse])
async def list_interview_invitations(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: Session = Depends(get_db)
):
    """List all invitations for an interview"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    invitations = (
        db.query(Invitation)
        .filter(Invitation.interview_id == interview_id)
        .all()
    )
    
    return invitations


@router.get("/verify/{token}", response_model=InvitationResponse)
async def verify_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify an invitation token and get interview details"""
    invitation = db.query(Invitation).filter(Invitation.unique_token == token).first()
    
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")
    
    # Check expiration
    if invitation.expires_at and datetime.utcnow() > invitation.expires_at:
        invitation.status = InvitationStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")
    
    # Check interview status
    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    if not interview or interview.status != InterviewStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview is no longer active")
    
    return invitation


@router.post("/{invitation_id}/resend", status_code=status.HTTP_200_OK)
async def resend_invitation(
    invitation_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: Session = Depends(get_db)
):
    """Resend an invitation email"""
    invitation = db.query(Invitation).join(Interview).filter(
        Invitation.id == invitation_id,
        Interview.employer_id == current_user.id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    
    if invitation.status == InvitationStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate has already completed the interview")
    
    # Generate new token and extend expiry
    invitation.unique_token = generate_unique_token()
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)
    invitation.status = InvitationStatus.SENT
    invitation.sent_at = datetime.utcnow()
    
    db.commit()
    
    # Send email
    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    interview_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/interview/{invitation.unique_token}"
    
    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation.candidate_email,
        candidate_name=invitation.candidate_name,
        interview_title=interview.title,
        interview_link=interview_link,
        expires_at=invitation.expires_at
    )
    
    return {"message": "Invitation resent successfully"}
