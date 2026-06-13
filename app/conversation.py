import re

from .clarification import is_clarification_response
from .fallback import _extract_route_pair


def format_conversation_history(
    history: list[dict[str, str]] | None,
    max_turns: int = 4,
) -> str:
    if not history:
        return ""

    recent = history[-max_turns * 2 :]
    lines: list[str] = []
    for turn in recent:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")

    if not lines:
        return ""

    return "Previous conversation:\n" + "\n".join(lines)


def build_contextual_query(query: str, history: list[dict[str, str]] | None) -> str:
    context = format_conversation_history(history)
    if not context:
        return query
    return f"{context}\n\nCurrent question: {query}"


def _is_in_clarification_thread(history: list[dict[str, str]] | None) -> bool:
    if not history:
        return False
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            return is_clarification_response(turn.get("content", ""))
    return False


def _collect_clarification_user_messages(
    history: list[dict[str, str]] | None,
    current_query: str,
) -> list[str]:
    """Gather all user messages in an ongoing clarification thread."""
    if not history:
        return [current_query]

    user_messages: list[str] = []
    for turn in reversed(history):
        role = turn.get("role", "")
        content = turn.get("content", "").strip()
        if not content:
            continue

        if role == "assistant":
            if is_clarification_response(content):
                continue
            break

        if role == "user":
            user_messages.insert(0, content)

    user_messages.append(current_query)
    return user_messages


def merge_clarification_query(prior_user_query: str, follow_up: str) -> str:
    """Combine an earlier vague question with the user's clarifying follow-up."""
    follow_up = follow_up.strip()
    if not follow_up:
        return prior_user_query

    flight_no = _extract_follow_up_flight_number(follow_up)
    if flight_no and len(follow_up.split()) <= 3:
        return f"What is the status and schedule of flight {flight_no}?"

    route_query = _normalize_route_follow_up(follow_up)
    if route_query:
        return route_query

    lowered_follow_up = follow_up.lower()
    if "from " in lowered_follow_up or " to " in lowered_follow_up:
        return follow_up

    if _looks_like_route_fragment(follow_up):
        base = prior_user_query.rstrip("?.!")
        city_match = re.search(r"\b(?:for|at|in)\s+([a-zA-Z]+)\b", base.lower())
        if city_match and " to " not in base.lower() and "from " not in base.lower():
            city = city_match.group(1).title()
            return f"Flights from {city} to {follow_up}"
        if " to " not in base.lower():
            return f"{base} to {follow_up}"
        return f"{base} — {follow_up}"

    return f"{prior_user_query.rstrip('?.!')} — {follow_up}"


def _normalize_route_follow_up(follow_up: str) -> str | None:
    lowered = follow_up.lower().strip()
    match = re.search(r"\broute\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\b", lowered)
    if match:
        origin = match.group(1).title()
        destination = match.group(2).title()
        return f"Flights from {origin} to {destination}"

    origin, destination = _extract_route_pair(follow_up)
    if origin and destination:
        return follow_up

    return None


def _extract_follow_up_flight_number(text: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,3}\d{1,4})\b", text.upper())
    return match.group(1) if match else None


def _looks_like_route_fragment(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned or len(cleaned.split()) > 4:
        return False
    if re.search(r"\d{4}-\d{2}-\d{2}", cleaned):
        return False
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z\s\-']+", cleaned))


def resolve_effective_query(
    query: str,
    history: list[dict[str, str]] | None,
) -> tuple[str, bool]:
    """Build the query used for routing and lookup, merging clarification follow-ups when needed."""
    if not _is_in_clarification_thread(history):
        return query, False

    user_messages = _collect_clarification_user_messages(history, query)
    effective = user_messages[0]
    for follow_up in user_messages[1:]:
        effective = merge_clarification_query(effective, follow_up)

    return effective, True
