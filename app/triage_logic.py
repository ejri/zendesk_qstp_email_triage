from typing import Any
from .models import TriageResult
from .config import CONFIDENCE_HUMAN_REVIEW_THRESHOLD


PRIORITY_ORDER = {"low": 0, "normal": 1, "high": 2, "urgent": 3}


def apply_guardrails(
    result: TriageResult,
    existing_priority: str | None,
    existing_tags: list[str],
) -> TriageResult:
    # Do not lower existing higher priority
    if existing_priority:
        if PRIORITY_ORDER.get(existing_priority, 0) > PRIORITY_ORDER.get(
            result.priority, 0
        ):
            result.priority = existing_priority

    # Force human review for certain categories
    if result.category == "security_or_privacy":
        result.needs_human_review = True

    # Force human review for low confidence
    if result.confidence < CONFIDENCE_HUMAN_REVIEW_THRESHOLD:
        result.needs_human_review = True

    # Respect existing ai_do_not_triage or legal/compliance tags (caller should skip calling this if so)
    return result


def build_tags(result: TriageResult, existing_tags: list[str]) -> list[str]:
    ai_prefix_tags = {
        t
        for t in existing_tags
        if t.startswith("ai_priority_")
        or t.startswith("ai_category_")
        or t in {"ai_triaged", "ai_review"}
    }

    retained = [t for t in existing_tags if t not in ai_prefix_tags]

    new_tags = {
        "ai_triaged",
        f"ai_priority_{result.priority}",
        f"ai_category_{result.category}",
    }

    if result.needs_human_review:
        new_tags.add("ai_review")

    return sorted(set(retained) | new_tags)


def build_internal_note(result: TriageResult) -> str:
    review = "Yes" if result.needs_human_review else "No"
    return (
        "AI triage result\n"
        f"Priority: {result.priority}\n"
        f"Category: {result.category}\n"
        f"Confidence: {result.confidence}%\n"
        f"Human review needed: {review}\n\n"
        f"Summary: {result.summary}\n\n"
        f"Rationale: {result.reason}"
    )