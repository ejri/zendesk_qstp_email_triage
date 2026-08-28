import hmac
import hashlib
import json
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import ValidationError

from .config import ZENDESK_WEBHOOK_SECRET, LOG_LEVEL
from .models import WebhookPayload
from .db import init_db, get_db, TriagedComment
from .zendesk_client import get_ticket, get_ticket_comments
from .llm_client import classify_email
from .triage_logic import apply_guardrails, build_tags, build_internal_note
from .zendesk_client import update_ticket

import redis
from .config import REDIS_URL

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


def verify_zendesk_signature(payload_body: bytes, signature: str) -> bool:
    if not ZENDESK_WEBHOOK_SECRET:
        logger.warning("ZENDESK_WEBHOOK_SECRET not set; skipping signature verification")
        return True
    expected = hmac.new(
        ZENDESK_WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_redis_client():
    if not REDIS_URL:
        return None
    return redis.from_url(REDIS_URL)


@app.post("/webhooks/zendesk/ticket-updated")
async def zendesk_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("x-zendesk-webhook-signature", "")

    if not verify_zendesk_signature(body, signature):
        logger.warning("Invalid Zendesk webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = WebhookPayload.model_validate_json(body)
    except ValidationError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    r = get_redis_client()
    if r:
        r.lpush("triage_queue", json.dumps(payload.model_dump()))
    else:
        # In-memory fallback: call worker logic directly (not ideal for prod)
        background_tasks.add_task(process_ticket, payload.ticket_id)

    return {"accepted": True, "ticket_id": payload.ticket_id}


def process_ticket(ticket_id: int):
    logger.info(f"Processing ticket {ticket_id}")
    db = next(get_db())

    try:
        ticket = get_ticket(ticket_id)
        comments = get_ticket_comments(ticket_id)

        requester_id = ticket.get("requester_id")
        if not requester_id:
            logger.info(f"No requester_id for ticket {ticket_id}; skipping")
            return

        # Find latest public requester comment
        latest_comment = None
        for c in comments:
            if c.get("public") and c.get("author_id") == requester_id:
                latest_comment = c
                break

        if not latest_comment:
            logger.info(f"No eligible requester comment for ticket {ticket_id}")
            return

        comment_id = latest_comment["id"]

        # Check if already processed
        existing = (
            db.query(TriagedComment)
            .filter(
                TriagedComment.ticket_id == ticket_id,
                TriagedComment.comment_id == comment_id,
            )
            .first()
        )
        if existing:
            logger.info(f"Ticket {ticket_id} comment {comment_id} already processed")
            return

        subject = ticket.get("subject") or "(No subject)"
        body = latest_comment.get("plain_body") or latest_comment.get("body") or ""
        if not body.strip():
            logger.info(f"Empty body for ticket {ticket_id}")
            return

        result = classify_email(subject, body)

        existing_priority = ticket.get("priority")
        existing_tags = ticket.get("tags") or []

        result = apply_guardrails(result, existing_priority, existing_tags)
        new_tags = build_tags(result, existing_tags)
        note_body = build_internal_note(result)

        update_payload = {
            "priority": result.priority,
            "tags": new_tags,
            "safe_update": True,
            "updated_stamp": ticket.get("updated_at"),
            "comment": {
                "public": False,
                "body": note_body,
            },
        }

        update_ticket(ticket_id, update_payload)

        triaged = TriagedComment(
            ticket_id=ticket_id,
            comment_id=comment_id,
            classification=result.model_dump(),
            model_name="openrouter:" + "google/gemma-4",
            prompt_version="v1",
            zendesk_update_status="success",
        )
        db.add(triaged)
        db.commit()

        logger.info(
            f"Triaged ticket {ticket_id}: priority={result.priority}, category={result.category}"
        )

    except Exception as e:
        logger.exception(f"Error processing ticket {ticket_id}: {e}")
        db.rollback()