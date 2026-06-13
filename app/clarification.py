import re

from .fallback import (
    _extract_date,
    _is_next_flight_query,
    has_sufficient_sql_criteria,
)

_CLARIFICATION_MARKERS = (
    "could you please share",
    "could you clarify",
    "to find the right flight",
    "share one of the following",
    "departing from or arriving to",
    "departing from** that city",
    "which flight you are looking for",
)


def _has_date(query: str) -> bool:
    return _extract_date(query) is not None


def _has_city_only_reference(query: str) -> bool:
    lowered = query.lower()
    if _is_next_flight_query(query):
        return False
    return bool(re.search(r"\b(?:for|at|in)\s+[a-zA-Z]+\b", lowered))


def is_clarification_response(content: str) -> bool:
    lowered = content.lower()
    return any(marker in lowered for marker in _CLARIFICATION_MARKERS)


def needs_flight_clarification(query: str, category: str) -> str | None:
    """Return a polite clarifying question when a flight lookup lacks key details."""
    if category != "Need SQL":
        return None

    if has_sufficient_sql_criteria(query):
        return None

    if _has_city_only_reference(query):
        return (
            "I'd like to help with that. Could you clarify whether you mean flights "
            "**departing from** that city or **arriving to** it?\n\n"
            "Please also share any of these if you have them:\n"
            "1. **Destination or origin city** (e.g., Delhi to Mumbai)\n"
            "2. **Travel date** (e.g., 2026-11-11)\n"
            "3. Or your **flight number** (e.g., SG528)"
        )

    details = [
        "1. Your **flight number** (e.g., SG528)",
        "2. Or your **route** (e.g., Delhi to Mumbai)",
    ]
    if not _has_date(query):
        details.append("3. Your **travel date**, if you have it")

    joined = "\n".join(details)
    return (
        "I'd be happy to help with that. To find the right flight information, "
        f"could you please share one of the following?\n\n{joined}"
    )
