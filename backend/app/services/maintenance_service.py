"""Scheduled maintenance jobs: invitation reminders and expiry sweep."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Invitation, InvitationStatus, Interview

logger = logging.getLogger("sris.maintenance")


def _interview_link(invitation: Invitation) -> str:
    return f"{settings.FRONTEND_URL}/interview/{invitation.unique_token}"


def sweep_expired_invitations(db: Session) -> int:
    """Mark sent/pending invitations whose expiry has passed as expired.

    Returns the number of invitations transitioned.
    """
    from app.services.notification_service import create_notification

    now = datetime.utcnow()
    expired = (
        db.query(Invitation)
        .filter(
            Invitation.status.in_([InvitationStatus.SENT, InvitationStatus.PENDING]),
            Invitation.expires_at.isnot(None),
            Invitation.expires_at < now,
        )
        .all()
    )
    for invitation in expired:
        invitation.status = InvitationStatus.EXPIRED
        interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
        if interview:
            try:
                create_notification(
                    db,
                    interview.employer_id,
                    "Invitation expired",
                    f"{invitation.candidate_name}'s invitation to \"{interview.title}\" expired without completion.",
                    notification_type="invitation_expired",
                    link=f"/interviews/{interview.id}",
                )
            except Exception as e:
                logger.warning("Expiry notification failed for invitation %s: %s", invitation.id, e)
    if expired:
        db.commit()
    return len(expired)


def send_invitation_reminders(db: Session) -> int:
    """Send reminder emails to candidates who have not accepted.

    Rules:
      - status is SENT
      - sent_at is not None and older than REMINDER_AFTER_HOURS
      - reminder_count < REMINDER_MAX
      - at least REMINDER_COOLDOWN_HOURS since last reminder (or sent_at)
      - invitation not expired yet
    Returns the number of reminders dispatched.
    """
    now = datetime.utcnow()
    after_hours = timedelta(hours=settings.INVITATION_REMINDER_AFTER_HOURS)
    cooldown = timedelta(hours=settings.INVITATION_REMINDER_COOLDOWN_HOURS)

    candidates = (
        db.query(Invitation)
        .filter(
            Invitation.status == InvitationStatus.SENT,
            Invitation.sent_at.isnot(None),
            Invitation.sent_at <= now - after_hours,
            Invitation.reminder_count < settings.INVITATION_REMINDER_MAX,
            Invitation.expires_at.isnot(None),
            Invitation.expires_at > now,
        )
        .all()
    )

    sent_count = 0
    for invitation in candidates:
        last_event = invitation.last_reminder_at or invitation.sent_at
        if last_event and last_event + cooldown > now:
            continue

        interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
        if not interview:
            continue

        reminder_number = invitation.reminder_count + 1
        try:
            from app.services.email_service import send_reminder_email_sync

            link = _interview_link(invitation)
            sent = send_reminder_email_sync(
                to_email=invitation.candidate_email,
                candidate_name=invitation.candidate_name,
                interview_title=interview.title,
                interview_link=link,
                expires_at=invitation.expires_at,
                reminder_number=reminder_number,
            )
            if not sent:
                continue
        except Exception as e:
            logger.error("Reminder failed for invitation %s: %s", invitation.id, e)
            continue

        invitation.last_reminder_at = now
        invitation.reminder_count = reminder_number
        sent_count += 1

        from app.services.notification_service import create_notification
        try:
            create_notification(
                db,
                interview.employer_id,
                "Reminder sent to candidate",
                f"Reminder {reminder_number} sent to {invitation.candidate_name} for \"{interview.title}\".",
                notification_type="reminder_sent",
                link=f"/interviews/{interview.id}",
            )
        except Exception as e:
            logger.warning("Reminder notification failed for invitation %s: %s", invitation.id, e)

    if sent_count:
        db.commit()
    return sent_count


def run_maintenance() -> dict:
    """Run all maintenance jobs and report counts."""
    with SessionLocal() as db:
        expired_count = sweep_expired_invitations(db)
    with SessionLocal() as db:
        reminders_count = send_invitation_reminders(db)
    return {
        "expired_invitations": expired_count,
        "reminders_sent": reminders_count,
    }
