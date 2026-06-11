import re


def _has_flight_number(query: str) -> bool:
    return bool(re.search(r"\b[A-Z]{2,3}\d{1,4}\b", query.upper()))


def _has_route(query: str) -> bool:
    lowered = query.lower()
    return "from " in lowered and " to " in lowered


def _has_date(query: str) -> bool:
    return bool(
        re.search(r"\d{4}-\d{2}-\d{2}", query)
        or re.search(r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", query, re.I)
    )


def needs_flight_clarification(query: str, category: str) -> str | None:
    """Return a polite clarifying question when a flight lookup lacks key details."""
    if category != "Need SQL":
        return None

    if _has_flight_number(query) or _has_route(query):
        return None

    lowered = query.lower()
    vague_patterns = [
        "my flight",
        "flight status",
        "is it delayed",
        "is my flight",
        "check my flight",
        "when does it depart",
        "what gate",
        "seat availability",
        "available seats",
    ]
    if not any(pattern in lowered for pattern in vague_patterns):
        return None

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
