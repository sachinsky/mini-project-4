from typing import Any


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
