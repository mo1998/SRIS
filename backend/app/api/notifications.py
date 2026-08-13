"""
In-app notification routes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.events import emit_data_change
from app.schemas import NotificationResponse, NotificationsListResponse
from app.services.notification_service import (
    list_notifications,
    mark_all_read,
    mark_notification_read,
    unread_count,
)

router = APIRouter()


def serialize_notification(notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        link=notification.link,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.get("/", response_model=NotificationsListResponse)
async def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's notifications and unread count."""
    notifications = list_notifications(db, current_user.id, limit=limit)
    return NotificationsListResponse(
        notifications=[serialize_notification(n) for n in notifications],
        unread_count=unread_count(db, current_user.id),
    )


@router.get("/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the number of unread notifications for the current user."""
    return {"unread_count": unread_count(db, current_user.id)}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notification = mark_notification_read(db, current_user.id, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    emit_data_change("notification", {"notification_id": notification.id, "is_read": True})
    return serialize_notification(notification)


@router.post("/read-all")
async def mark_all_read_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all of the current user's notifications as read."""
    marked = mark_all_read(db, current_user.id)
    emit_data_change("notification", {"is_read_all": True})
    return {"marked": marked}
