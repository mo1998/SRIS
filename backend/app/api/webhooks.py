from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Webhook, WebhookDelivery, WebhookStatus, User, UserRole
from app.schemas import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookSecretResponse,
    WebhookDeliveryResponse,
)
from app.api.auth import get_current_user
from app.services.webhook_service import generate_secret, fire_event, build_event_payload

router = APIRouter()


def get_organization_id(current_user: User, db: Session) -> int:
    if current_user.role == UserRole.ADMIN:
        return None
    from app.models import TeamMembership
    membership = db.query(TeamMembership).filter(
        TeamMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User has no organization")
    return membership.organization_id


@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Webhook)
    if current_user.role != UserRole.ADMIN:
        org_id = get_organization_id(current_user, db)
        query = query.filter(Webhook.organization_id == org_id)

    return query.all()


@router.post("/", response_model=WebhookSecretResponse, status_code=201)
async def create_webhook(
    data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    org_id = get_organization_id(current_user, db)
    if org_id is None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="User has no organization")

    secret = generate_secret()
    webhook = Webhook(
        organization_id=org_id if current_user.role != UserRole.ADMIN else 0,
        url=data.url,
        secret=secret,
        events=",".join(e.value for e in data.events),
        description=data.description,
        status=WebhookStatus.ACTIVE,
        retry_count=data.retry_count,
        timeout_seconds=data.timeout_seconds,
        created_by=current_user.id,
    )
    if current_user.role == UserRole.ADMIN and org_id:
        webhook.organization_id = org_id

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookSecretResponse(
        id=webhook.id,
        url=webhook.url,
        secret=secret,
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if current_user.role != UserRole.ADMIN and webhook.organization_id != get_organization_id(current_user, db):
        raise HTTPException(status_code=403, detail="Access denied")

    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if current_user.role != UserRole.ADMIN and webhook.organization_id != get_organization_id(current_user, db):
        raise HTTPException(status_code=403, detail="Access denied")

    if data.url is not None:
        webhook.url = data.url
    if data.events is not None:
        webhook.events = ",".join(e.value for e in data.events)
    if data.description is not None:
        webhook.description = data.description
    if data.status is not None:
        webhook.status = WebhookStatus(data.status)
    if data.retry_count is not None:
        webhook.retry_count = data.retry_count
    if data.timeout_seconds is not None:
        webhook.timeout_seconds = data.timeout_seconds

    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if current_user.role != UserRole.ADMIN and webhook.organization_id != get_organization_id(current_user, db):
        raise HTTPException(status_code=403, detail="Access denied")

    db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == webhook_id).delete()
    db.delete(webhook)
    db.commit()


@router.post("/{webhook_id}/test", status_code=200)
async def test_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if current_user.role != UserRole.ADMIN and webhook.organization_id != get_organization_id(current_user, db):
        raise HTTPException(status_code=403, detail="Access denied")

    payload = build_event_payload("test", webhook_id, "webhook", {"message": "Test webhook delivery from SRIS"})
    delivery = await fire_event("test", payload, webhook.organization_id, db)

    return {"status": delivery.status, "response_status": delivery.response_status}


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if current_user.role != UserRole.ADMIN and webhook.organization_id != get_organization_id(current_user, db):
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(WebhookDelivery.created_at.desc()).limit(50).all()
