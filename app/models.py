from pydantic import BaseModel, Field
from typing import Literal


class TriageResult(BaseModel):
    priority: Literal["urgent", "high", "normal", "low"]
    category: Literal[
        "account_access",
        "billing",
        "bug_or_outage",
        "feature_request",
        "security_or_privacy",
        "sales_or_partnership",
        "general_support",
        "other",
    ]
    confidence: int = Field(ge=0, le=100)
    summary: str
    reason: str
    needs_human_review: bool


class WebhookPayload(BaseModel):
    event_type: str
    ticket_id: int
    ticket_updated_at: str
    requester_id: int
    channel: str
    status: str