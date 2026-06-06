import re
from datetime import datetime

from .query_validation import NO_CRITERIA_MESSAGE, get_unsupported_field_message
from .sql_executor import execute_sql_query

_CITY_TO_CODE = {
    "delhi": "DEL",
    "mumbai": "BOM",
    "bengaluru": "BLR",
    "bangalore": "BLR",
    "chennai": "MAA",
    "hyderabad": "HYD",
    "nagpur": "NAG",
    "goa": "GOI",
}


def _extract_flight_number(query: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,3}\d{1,4})\b", query.upper())
    return match.group(1) if match else None


def _extract_airport_code(query: str, direction: str) -> str | None:
    lowered = query.lower()
    if direction == "origin":
        match = re.search(r"from\s+([a-zA-Z]+)", lowered)
    else:
        match = re.search(r"to\s+([a-zA-Z]+)", lowered)
    if not match:
        return None
    place = match.group(1).lower()
    if len(place) == 3 and place.isalpha():
        return place.upper()
    return _CITY_TO_CODE.get(place)


def _extract_date(query: str) -> str | None:
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
        r"(\d{1,2}\s+Nov\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            raw = match.group(1)
            for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


def generate_sql_fallback(query: str) -> str | None:
    unsupported = get_unsupported_field_message(query)
    if unsupported:
        return None

    flight_no = _extract_flight_number(query)
    if flight_no:
        return f"SELECT * FROM flights WHERE flight_no ILIKE '{flight_no}' LIMIT 5;"

    origin = _extract_airport_code(query, "origin")
    destination = _extract_airport_code(query, "destination")
    date = _extract_date(query)

    clauses = []
    if origin:
        clauses.append(f"origin = '{origin}'")
    if destination:
        clauses.append(f"destination = '{destination}'")
    if date:
        clauses.append(f"departure_date = '{date}'")

    if clauses:
        where = " AND ".join(clauses)
        return f"SELECT * FROM flights WHERE {where} LIMIT 10;"

    return None


def summarize_sql_results(query: str, results: list[dict] | str) -> str:
    if isinstance(results, str):
        return results

    if not results:
        return "I couldn't find any matching flight records for your query."

    lines = ["I found the following flight information:"]
    for row in results[:5]:
        flight_no = row.get("flight_no", "N/A")
        status = row.get("status", "N/A")
        origin = row.get("origin", "")
        destination = row.get("destination", "")
        dep_date = row.get("departure_date", "")
        dep_time = row.get("departure_time", "")
        delay = row.get("delay_minutes", 0)
        gate = row.get("gate", "")
        terminal = row.get("terminal", "")
        aircraft = row.get("aircraft_type", "")
        seats_total = row.get("seats_total")
        seats_booked = row.get("seats_booked")

        line = (
            f"- Flight {flight_no}: {origin} to {destination} on {dep_date} at {dep_time}. "
            f"Status: {status}."
        )
        if delay and int(delay) > 0:
            line += f" Delayed by {delay} minutes."
        if gate or terminal:
            line += f" Terminal {terminal}, Gate {gate}."
        if aircraft:
            line += f" Aircraft: {aircraft}."
        if seats_total is not None and seats_booked is not None:
            available = int(seats_total) - int(seats_booked)
            line += f" Seats available: {available}."
        lines.append(line)

    return "\n".join(lines)


def run_sql_fallback(query: str) -> tuple[str, str | None]:
    from .query_validation import is_raw_sql_query

    unsupported = get_unsupported_field_message(query)
    if unsupported:
        return unsupported, None

    if is_raw_sql_query(query):
        results = execute_sql_query(query)
        if isinstance(results, str):
            return results.replace("Error executing query: ", ""), query
        return summarize_sql_results(query, results), query

    sql_query = generate_sql_fallback(query)
    if not sql_query:
        return NO_CRITERIA_MESSAGE, None

    results = execute_sql_query(sql_query)
    if isinstance(results, str) and results.startswith("Error executing query:"):
        return results.replace("Error executing query: ", ""), sql_query
    return summarize_sql_results(query, results), sql_query


def run_rag_fallback(query: str) -> str:
    from .chains import get_vectorstore

    retriever = get_vectorstore().as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(query)
    if not docs:
        return "I don't have enough policy information to answer that question."

    context = "\n\n".join(doc.page_content for doc in docs)
    return (
        "Based on our airline policy documentation:\n\n"
        f"{context[:1800]}"
    )
