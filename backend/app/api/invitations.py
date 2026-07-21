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
from app.models import User, Interview, Invitation, InvitationStatus, InterviewStatus, TeamMembership, TeamRole, UserRole
from app.schemas import InvitationCreate, InvitationResponse, InvitationEmailPreview, InvitationPreviewRequest, InvitationVerificationResponse
from app.api.auth import get_current_user
from app.config import settings
from app.services.audit_service import create_audit_log
from app.services.email_service import render_invitation_email, send_invitation_email

router = APIRouter()

INVITATION_MANAGER_ROLES = {TeamRole.OWNER, TeamRole.ADMIN, TeamRole.RECRUITER}


def generate_unique_token() -> str:
    """Generate a unique invitation token"""
    return str(uuid.uuid4())


def get_interview_or_404(interview_id: int, db: Session) -> Interview:
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return interview


def require_interview_membership(interview: Interview, user: User, db: Session) -> TeamMembership:
    if user.role == UserRole.ADMIN:
        return None

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
    return membership


def require_invitation_manager(interview: Interview, user: User, db: Session) -> None:
    membership = require_interview_membership(interview, user, db)
    if membership and membership.role not in INVITATION_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient organization permissions")


@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: InvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an invitation for a candidate"""
    interview = get_interview_or_404(invitation_data.interview_id, db)
    require_invitation_manager(interview, current_user, db)
    
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
    sent_at = datetime.utcnow()
    
    invitation = Invitation(
        interview_id=invitation_data.interview_id,
        candidate_email=invitation_data.candidate_email,
        candidate_name=invitation_data.candidate_name,
        unique_token=token,
        status=InvitationStatus.SENT,
        sent_at=sent_at,
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
        expires_at=expires_at,
        custom_message=invitation_data.custom_message,
    )
    
    return invitation


@router.post("/bulk", response_model=List[InvitationResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_invitations(
    invitations: List[InvitationCreate],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create multiple invitations at once"""
    
    if not invitations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No invitations provided")

    if len(invitations) > settings.MAX_BULK_INVITATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bulk invitations cannot exceed {settings.MAX_BULK_INVITATIONS} candidates",
        )
    
    interview_id = invitations[0].interview_id
    if any(invitation.interview_id != interview_id for invitation in invitations):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All bulk invitations must target the same interview")

    interview = get_interview_or_404(interview_id, db)
    require_invitation_manager(interview, current_user, db)
    
    if interview.status != InterviewStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview must be active")
    
    created_invitations = []
    expires_at = datetime.utcnow() + timedelta(days=7)
    sent_at = datetime.utcnow()
    
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
            status=InvitationStatus.SENT,
            sent_at=sent_at,
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
            expires_at=expires_at,
            custom_message=inv_data.custom_message,
        )
    
    db.commit()
    
    for inv in created_invitations:
        db.refresh(inv)
    
    return created_invitations


@router.post("/preview/{interview_id}", response_model=InvitationEmailPreview)
async def preview_invitation_email(
    interview_id: int,
    preview_data: InvitationPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview the invitation email that will be sent for an interview"""
    interview = get_interview_or_404(interview_id, db)
    require_invitation_manager(interview, current_user, db)

    expires_at = datetime.utcnow() + timedelta(days=7)
    interview_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/interview/sample-token"
    subject, html_body = render_invitation_email(
        candidate_name=preview_data.candidate_name,
        interview_title=interview.title,
        interview_link=interview_link,
        expires_at=expires_at,
        custom_message=preview_data.custom_message,
    )

    return {
        "subject": subject,
        "html_body": html_body,
        "interview_link": interview_link,
        "expires_at": expires_at,
    }


@router.get("/verify/{token}", response_model=InvitationVerificationResponse)
async def verify_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify an invitation token and get interview details"""
    invitation = db.query(Invitation).filter(Invitation.unique_token == token).first()
    
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")
    
    # Check expiration
    if invitation.status == InvitationStatus.REVOKED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has been revoked")

    if invitation.expires_at and datetime.utcnow() > invitation.expires_at:
        invitation.status = InvitationStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")
    
    # Check interview status
    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    if not interview or interview.status != InterviewStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview is no longer active")
    
    return {
        "id": invitation.id,
        "interview_id": invitation.interview_id,
        "candidate_email": invitation.candidate_email,
        "candidate_name": invitation.candidate_name,
        "unique_token": invitation.unique_token,
        "status": invitation.status,
        "sent_at": invitation.sent_at,
        "expires_at": invitation.expires_at,
        "created_at": invitation.created_at,
        "interview": interview,
    }


@router.get("/{interview_id}", response_model=List[InvitationResponse])
async def list_interview_invitations(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all invitations for an interview"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_membership(interview, current_user, db)

    invitations = (
        db.query(Invitation)
        .filter(Invitation.interview_id == interview_id)
        .all()
    )

    return invitations


@router.post("/{invitation_id}/revoke", response_model=InvitationResponse)
async def revoke_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an invitation so the candidate can no longer use it"""
    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    interview = get_interview_or_404(invitation.interview_id, db)
    require_invitation_manager(interview, current_user, db)

    if invitation.status == InvitationStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revoke a completed invitation")

    invitation.status = InvitationStatus.REVOKED
    invitation.expires_at = datetime.utcnow()
    create_audit_log(
        db,
        actor=current_user,
        action="invitation.revoked",
        target_type="invitation",
        target_id=invitation.id,
        organization_id=interview.organization_id,
        details={"interview_id": interview.id, "candidate_email": invitation.candidate_email},
    )

    db.commit()
    db.refresh(invitation)

    return invitation


@router.post("/{invitation_id}/resend", status_code=status.HTTP_200_OK)
async def resend_invitation(
    invitation_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend an invitation email"""
    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    interview = get_interview_or_404(invitation.interview_id, db)
    require_invitation_manager(interview, current_user, db)
    
    if invitation.status == InvitationStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate has already completed the interview")

    if invitation.status == InvitationStatus.REVOKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot resend a revoked invitation")

    if invitation.sent_at:
        next_resend_at = invitation.sent_at + timedelta(seconds=settings.INVITATION_RESEND_COOLDOWN_SECONDS)
        now = datetime.utcnow()
        if now < next_resend_at:
            retry_after = max(1, int((next_resend_at - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Invitation was resent recently. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
    
    # Generate new token and extend expiry
    invitation.unique_token = generate_unique_token()
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)
    invitation.status = InvitationStatus.SENT
    invitation.sent_at = datetime.utcnow()
    
    db.commit()
    
    # Send email
    interview_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/interview/{invitation.unique_token}"
    
    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation.candidate_email,
        candidate_name=invitation.candidate_name,
        interview_title=interview.title,
        interview_link=interview_link,
        expires_at=invitation.expires_at,
    )
    
    return {"message": "Invitation resent successfully"}
