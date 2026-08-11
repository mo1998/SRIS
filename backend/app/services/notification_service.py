"""
In-app notification service - creates and reads user notifications.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Notification, User


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: Optional[str] = None,
    notification_type: str = "general",
    link: Optional[str] = None,
) -> Notification:
    """Create a notification for a user and commit immediately."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        link=link,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def create_notification_for_members(
    db: Session,
    user_ids: List[int],
    title: str,
    message: Optional[str] = None,
    notification_type: str = "general",
    link: Optional[str] = None,
) -> int:
    """Create the same notification for multiple users. Returns count created."""
    created = 0
    for user_id in user_ids:
        db.add(Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            link=link,
        ))
        created += 1
    db.commit()
    return created


def list_notifications(db: Session, user_id: int, limit: int = 20) -> List[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )


def unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .count()
    )


def mark_notification_read(db: Session, user_id: int, notification_id: int) -> Optional[Notification]:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notification:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> int:
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return count
