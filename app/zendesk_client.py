import httpx
from .config import ZENDESK_BASE_URL, ZENDESK_ACCESS_TOKEN, ZENDESK_SUBDOMAIN

session = httpx.Client(
    base_url=ZENDESK_BASE_URL,
    headers={
        "Authorization": f"Bearer {ZENDESK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    },
    timeout=30.0,
)


def get_ticket(ticket_id: int) -> dict:
    resp = session.get(f"/tickets/{ticket_id}.json")
    resp.raise_for_status()
    return resp.json()["ticket"]


def get_ticket_comments(ticket_id: int) -> list[dict]:
    resp = session.get(
        f"/tickets/{ticket_id}/comments.json",
        params={"sort_order": "desc", "per_page": 100},
    )
    resp.raise_for_status()
    return resp.json().get("comments", [])


def update_ticket(ticket_id: int, update_payload: dict) -> dict:
    resp = session.put(f"/tickets/{ticket_id}.json", json={"ticket": update_payload})
    resp.raise_for_status()
    return resp.json().get("ticket", {})