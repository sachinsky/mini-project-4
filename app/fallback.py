import re
from datetime import datetime

from .city_codes import is_route_skip_word, resolve_city
from .query_validation import NO_CRITERIA_MESSAGE, get_unsupported_field_message
from .sql_executor import execute_sql_query


def _extract_flight_number(query: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,3}\d{1,4})\b", query.upper())
    return match.group(1) if match else None


def _resolve_place(place: str) -> str | None:
    return resolve_city(place)


def _extract_route_pair(query: str) -> tuple[str | None, str | None]:
    lowered = query.lower()

    match = re.search(r"from\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)", lowered)
    if match:
        origin, dest = _resolve_place(match.group(1)), _resolve_place(match.group(2))
        if origin and dest:
            return origin, dest

    match = re.search(r"to\s+([a-zA-Z]+)\s+from\s+([a-zA-Z]+)", lowered)
    if match:
        origin, dest = _resolve_place(match.group(2)), _resolve_place(match.group(1))
        if origin and dest:
            return origin, dest

    match = re.search(r"\broute\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\b", lowered)
    if match:
        origin, dest = _resolve_place(match.group(1)), _resolve_place(match.group(2))
        if origin and dest:
            return origin, dest

    for match in re.finditer(r"\b([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\b", lowered):
        word1, word2 = match.group(1), match.group(2)
        if is_route_skip_word(word1) or is_route_skip_word(word2):
            continue
        origin, dest = _resolve_place(word1), _resolve_place(word2)
        if origin and dest:
            return origin, dest

    return None, None


def _extract_airport_code(query: str, direction: str) -> str | None:
    origin, destination = _extract_route_pair(query)
    if direction == "origin" and origin:
        return origin
    if direction == "destination" and destination:
        return destination

    lowered = query.lower()
    if direction == "origin":
        match = re.search(r"from\s+([a-zA-Z]+)", lowered)
        if not match and re.search(r"\b(next|upcoming|earliest)\s+flight\b", lowered):
            match = re.search(r"\b(?:for|at|in)\s+([a-zA-Z]+)\b", lowered)
    else:
        match = re.search(r"to\s+([a-zA-Z]+)", lowered)
    if not match:
        return None
    return _resolve_place(match.group(1))


def _is_next_flight_query(query: str) -> bool:
    return bool(re.search(r"\b(next|upcoming|earliest)\s+flight\b", query, re.IGNORECASE))


def has_sufficient_sql_criteria(query: str) -> bool:
    """Return True when the query has enough detail to run a focused flight lookup."""
    if _extract_flight_number(query):
        return True

    origin, destination = _extract_route_pair(query)
    origin = origin or _extract_airport_code(query, "origin")
    destination = destination or _extract_airport_code(query, "destination")
    date = _extract_date(query)

    if origin and destination:
        return True
    if origin and date:
        return True
    if destination and date:
        return True
    if _is_next_flight_query(query) and (origin or destination):
        return True
    if origin or destination:
        return True

    return False


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
        if _is_next_flight_query(query):
            return (
                f"SELECT * FROM flights WHERE {where} "
                "AND (departure_date > CURRENT_DATE OR "
                "(departure_date = CURRENT_DATE AND departure_time > CURRENT_TIME)) "
                "ORDER BY departure_date ASC, departure_time ASC LIMIT 1;"
            )
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
    from .chains import get_rag_retriever
    from .rag_utils import build_policy_answer

    retriever = get_rag_retriever()
    docs = retriever.invoke(query)
    return build_policy_answer(docs, query)
