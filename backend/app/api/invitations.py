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
from app.models import User, Interview, Invitation, InvitationStatus, InterviewStatus, TeamMembership, TeamRole, UserRole, CandidateResponse
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
    expires_at = datetime.utcnow() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
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
    create_audit_log(
        db,
        actor=current_user,
        action="invitation.created",
        target_type="invitation",
        organization_id=interview.organization_id,
        details={"interview_id": interview.id, "candidate_email": invitation.candidate_email},
    )
    db.commit()
    db.refresh(invitation)
    
    # Send email in background
    interview_link = f"{settings.FRONTEND_URL}/interview/{token}"
    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation_data.candidate_email,
        candidate_name=invitation_data.candidate_name,
        interview_title=interview.title,
        interview_link=interview_link,
        expires_at=expires_at,
        custom_message=invitation_data.custom_message,
    )

    from app.services.webhook_service import fire_event, build_event_payload
    try:
        payload = build_event_payload(
            "invitation.sent",
            invitation.id,
            "invitation",
            {
                "interview_id": interview.id,
                "candidate_email": invitation.candidate_email,
                "candidate_name": invitation.candidate_name,
            },
        )
        await fire_event("invitation.sent", payload, interview.organization_id)
    except Exception as exc:
        print(f"Webhook fire failed: {exc}")

    from app.services.notification_service import create_notification
    try:
        create_notification(
            db,
            interview.employer_id,
            "Interview invitation sent",
            f"Invitation sent to {invitation.candidate_name} for \"{interview.title}\".",
            notification_type="invitation_sent",
            link=f"/interviews/{interview.id}",
        )
    except Exception as exc:
        print(f"Notification creation failed: {exc}")

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
    expires_at = datetime.utcnow() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
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
        interview_link = f"{settings.FRONTEND_URL}/interview/{token}"
        background_tasks.add_task(
            send_invitation_email,
            to_email=inv_data.candidate_email,
            candidate_name=inv_data.candidate_name,
            interview_title=interview.title,
            interview_link=interview_link,
            expires_at=expires_at,
            custom_message=inv_data.custom_message,
        )
    
    create_audit_log(
        db,
        actor=current_user,
        action="invitation.bulk_created",
        target_type="interview",
        target_id=interview.id,
        organization_id=interview.organization_id,
        details={"created_count": len(created_invitations)},
    )
    db.commit()
    
    for inv in created_invitations:
        db.refresh(inv)
    
    from app.services.webhook_service import fire_event, build_event_payload
    try:
        for inv in created_invitations:
            payload = build_event_payload(
                "invitation.sent",
                inv.id,
                "invitation",
                {
                    "interview_id": interview.id,
                    "candidate_email": inv.candidate_email,
                    "candidate_name": inv.candidate_name,
                },
            )
            await fire_event("invitation.sent", payload, interview.organization_id)
    except Exception as exc:
        print(f"Webhook fire failed: {exc}")
    
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

    expires_at = datetime.utcnow() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
    interview_link = f"{settings.FRONTEND_URL}/interview/sample-token"
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


@router.get("/{token}/results")
async def get_candidate_results(
    token: str,
    db: Session = Depends(get_db)
):
    """Public token-based endpoint for candidates to view their own results
    (score, feedback, transcript) without needing an account."""
    invitation = db.query(Invitation).filter(Invitation.unique_token == token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")

    response = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.invitation_id == invitation.id)
        .order_by(CandidateResponse.id.desc())
        .first()
    )
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No interview response found for this invitation")

    from app.services.evaluation_service import generate_candidate_report

    report = generate_candidate_report(response.id, db)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not available yet")

    # Strip internal/employer-only fields
    report.pop("evidence", None)
    for answer in report.get("answers", []):
        answer.pop("video_file_path", None)
        answer.pop("audio_file_path", None)
    return report


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


@router.delete("/{invitation_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_completed_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a completed invitation and delete the candidate's response.

    Hard-deletes the linked candidate responses (answers, evaluation runs,
    integrity events and uploaded media) together with the invitation. Only
    invitations with status ``completed`` can be cancelled.
    """
    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    interview = get_interview_or_404(invitation.interview_id, db)
    require_invitation_manager(interview, current_user, db)

    if invitation.status != InvitationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed invitations can be cancelled",
        )

    from app.api.responses import delete_answer_media_files

    responses = db.query(CandidateResponse).filter(CandidateResponse.invitation_id == invitation.id).all()
    for response in responses:
        delete_answer_media_files(response)
        db.delete(response)

    create_audit_log(
        db,
        actor=current_user,
        action="invitation.cancelled",
        target_type="invitation",
        target_id=invitation.id,
        organization_id=interview.organization_id,
        details={"interview_id": interview.id, "candidate_email": invitation.candidate_email},
    )

    db.delete(invitation)
    db.commit()


@router.delete("/{interview_id}/cancel-all", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_all_completed_invitations(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel every completed invitation for an interview.

    Deletes each completed invitation together with its candidate response,
    answers, evaluation runs, integrity events and uploaded media.
    """
    interview = get_interview_or_404(interview_id, db)
    require_invitation_manager(interview, current_user, db)

    invitations = db.query(Invitation).filter(
        Invitation.interview_id == interview_id,
        Invitation.status == InvitationStatus.COMPLETED,
    ).all()

    if not invitations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No completed invitations to cancel",
        )

    from app.api.responses import delete_answer_media_files

    for invitation in invitations:
        responses = db.query(CandidateResponse).filter(CandidateResponse.invitation_id == invitation.id).all()
        for response in responses:
            delete_answer_media_files(response)
            db.delete(response)

    create_audit_log(
        db,
        actor=current_user,
        action="invitation.cancelled_all",
        target_type="interview",
        target_id=interview_id,
        organization_id=interview.organization_id,
        details={"interview_id": interview_id, "cancelled_count": len(invitations)},
    )

    for invitation in invitations:
        db.delete(invitation)
    db.commit()


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
    invitation.expires_at = datetime.utcnow() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
    invitation.status = InvitationStatus.SENT
    invitation.sent_at = datetime.utcnow()
    create_audit_log(
        db,
        actor=current_user,
        action="invitation.resent",
        target_type="invitation",
        target_id=invitation.id,
        organization_id=interview.organization_id,
        details={"interview_id": interview.id, "candidate_email": invitation.candidate_email},
    )
    
    db.commit()
    
    # Send email
    interview_link = f"{settings.FRONTEND_URL}/interview/{invitation.unique_token}"
    
    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation.candidate_email,
        candidate_name=invitation.candidate_name,
        interview_title=interview.title,
        interview_link=interview_link,
        expires_at=invitation.expires_at,
    )
    
    return {"message": "Invitation resent successfully"}
