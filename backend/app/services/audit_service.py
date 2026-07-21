"""Audit logging helpers for security-sensitive actions."""

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def create_audit_log(
    db: Session,
    *,
    actor: Optional[User],
    action: str,
    target_type: str,
    target_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        organization_id=organization_id,
        details=json.dumps(details, sort_keys=True) if details else None,
    )
    db.add(audit_log)
    return audit_log