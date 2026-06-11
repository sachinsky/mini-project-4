import re

from langchain_core.documents import Document

_SECTION_HINTS = {
    "baggage": ["baggage", "bag", "luggage", "carry-on", "checked", "cabin"],
    "booking": ["book", "payment", "hold", "name correction", "gst"],
    "cancellation": ["cancel", "refund", "reschedule", "change", "no-show"],
    "assistance": ["wheelchair", "pet", "assistance", "special", "infant"],
    "delay": ["delay", "on-time", "late", "departure time"],
    "documents": ["document", "id", "aadhaar", "passport", "visa"],
    "addons": ["meal", "lounge", "priority", "add-on", "extra baggage"],
}

_SECTION_TITLES = {
    "baggage": ["baggage policy"],
    "booking": ["booking & payments", "company & service overview"],
    "cancellation": ["changes, cancellations & refunds"],
    "assistance": ["special assistance", "wheelchair"],
    "delay": ["on-time performance & delays", "delays"],
    "documents": ["travel documents & id"],
    "addons": ["add-ons & services"],
}


def clean_policy_text(text: str) -> str:
    """Normalize PDF text: remove hidden chars and improve readability."""
    text = text.replace("\u200b", "").replace("\uf0b7", "-")
    text = re.sub(r"\s*●\s*", "\n- ", text)
    text = re.sub(r"(?<=[.!?])\s+(?=[A-Z])", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _matched_topics(query: str) -> list[str]:
    lowered_query = query.lower()
    topics = []
    for topic, keywords in _SECTION_HINTS.items():
        if any(keyword in lowered_query for keyword in keywords):
            topics.append(topic)
    return topics


def _score_chunk_for_query(chunk: str, query: str) -> int:
    lowered_chunk = chunk.lower()
    tokens = [t for t in re.findall(r"[a-zA-Z]+", query.lower()) if len(t) > 2]
    score = sum(1 for token in tokens if token in lowered_chunk)

    for topic in _matched_topics(query):
        for keyword in _SECTION_HINTS[topic]:
            if keyword in lowered_chunk:
                score += 3
        for title in _SECTION_TITLES.get(topic, []):
            if re.search(rf"(?:\d+\.\s*)?{re.escape(title)}\b", lowered_chunk):
                score += 20
    return score


def _split_policy_sections(text: str) -> list[str]:
    cleaned = clean_policy_text(text)
    parts = re.split(r"(?=\d+\.\s+[A-Z])", cleaned)
    sections = [part.strip() for part in parts if part.strip()]
    return sections or [cleaned]


def _section_key(section: str) -> str:
    match = re.match(r"\d+\.\s*(.+)", section.strip(), re.IGNORECASE)
    if match:
        return match.group(1).split("\n")[0].strip().lower()
    return section[:80].strip().lower()


def format_policy_context(docs: list[Document], query: str = "", max_chunks: int = 1) -> str:
    """Pick the most relevant policy section(s) across retrieved documents."""
    if not docs:
        return ""

    all_sections: list[str] = []
    seen: set[str] = set()
    for doc in docs:
        for section in _split_policy_sections(doc.page_content):
            key = _section_key(section)
            if key in seen:
                continue
            seen.add(key)
            all_sections.append(section)

    ranked = sorted(all_sections, key=lambda s: _score_chunk_for_query(s, query), reverse=True)
    if not ranked:
        return ""
    return "\n\n".join(ranked[:max_chunks])


def build_policy_answer(docs: list[Document], query: str) -> str:
    """Build a user-friendly fallback answer without an LLM."""
    context = format_policy_context(docs, query=query, max_chunks=1)
    if not context:
        return "I don't have enough policy information to answer that question."

    return (
        "Here is the relevant information from our airline policy:\n\n"
        f"{context}"
    )
