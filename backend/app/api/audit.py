"""Audit log visibility routes."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, TeamMembership, TeamRole, User, UserRole
from app.schemas import AuditLogResponse

router = APIRouter()


def get_primary_admin_membership(user: User, db: Session) -> TeamMembership:
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id, TeamMembership.role.in_([TeamRole.OWNER, TeamRole.ADMIN]))
        .order_by(TeamMembership.created_at.asc())
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient audit log permissions")
    return membership


def serialize_audit_log(audit_log: AuditLog) -> AuditLogResponse:
    details = None
    if audit_log.details:
        details = json.loads(audit_log.details)

    return AuditLogResponse(
        id=audit_log.id,
        actor_user_id=audit_log.actor_user_id,
        action=audit_log.action,
        target_type=audit_log.target_type,
        target_id=audit_log.target_id,
        organization_id=audit_log.organization_id,
        details=details,
        created_at=audit_log.created_at,
    )


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit logs for system admins or organization owners/admins."""
    query = db.query(AuditLog)

    if current_user.role == UserRole.ADMIN:
        if organization_id is not None:
            query = query.filter(AuditLog.organization_id == organization_id)
    else:
        membership = get_primary_admin_membership(current_user, db)
        if organization_id is not None and organization_id != membership.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        query = query.filter(AuditLog.organization_id == membership.organization_id)

    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if target_id is not None:
        query = query.filter(AuditLog.target_id == target_id)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)

    audit_logs = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(skip).limit(limit).all()
    return [serialize_audit_log(audit_log) for audit_log in audit_logs]