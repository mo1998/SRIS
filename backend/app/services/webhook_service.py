import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from typing import Dict, Optional
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Webhook, WebhookDelivery, WebhookStatus


def generate_secret() -> str:
    return hashlib.sha256(f"{time.time()}{os.urandom(16)}".encode()).hexdigest()


def sign_payload(payload: Dict, secret: str) -> str:
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def _events_contain(events_str: str, event_type: str) -> bool:
    return event_type in [e.strip() for e in events_str.split(",")]


async def deliver_webhook(
    webhook: Webhook,
    event_type: str,
    payload: Dict,
) -> WebhookDelivery:
    signature = sign_payload(payload, webhook.secret)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event_type,
        "X-Webhook-Timestamp": str(int(time.time())),
        "User-Agent": "SRIS-Webhook/1.0",
    }

    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=json.dumps(payload),
        status="pending",
        attempt=1,
    )

    db = SessionLocal()
    try:
        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        async with httpx.AsyncClient(timeout=webhook.timeout_seconds) as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers,
            )
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:5000] if response.text else None
            delivery.status = "delivered" if response.is_success else "failed"
            delivery.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(delivery)

        return delivery
    except Exception as e:
        delivery.status = "failed"
        delivery.response_body = str(e)[:5000]
        delivery.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(delivery)
        return delivery
    finally:
        db.close()


async def fire_event(
    event_type: str,
    payload: Dict,
    organization_id: Optional[int] = None,
    db: Optional[Session] = None,
):
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        webhooks = db.query(Webhook).filter(
            Webhook.status == WebhookStatus.ACTIVE,
        ).all()

        if organization_id:
            webhooks = [w for w in webhooks if w.organization_id == organization_id]

        matched = []
        for w in webhooks:
            if _events_contain(w.events, event_type):
                matched.append(w)

        for webhook in matched:
            await deliver_webhook(webhook, event_type, payload)
    finally:
        if own_session:
            db.close()


def build_event_payload(
    event_type: str,
    resource_id: int,
    resource_type: str,
    summary: Optional[Dict] = None,
) -> Dict:
    return {
        "event": event_type,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "summary": summary or {},
        "timestamp": datetime.utcnow().isoformat(),
        "app": "SRIS",
        "version": settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "1.0.0",
    }
