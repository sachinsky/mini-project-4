import re

FLIGHTS_COLUMNS = {
    "id",
    "flight_no",
    "airline_code",
    "airline_name",
    "origin",
    "destination",
    "departure_date",
    "departure_time",
    "arrival_date",
    "arrival_time",
    "status",
    "delay_minutes",
    "delay_reason",
    "terminal",
    "gate",
    "aircraft_type",
    "seats_total",
    "seats_booked",
    "fare_inr",
}

_UNSUPPORTED_FIELD_PATTERNS = [
    (r"\bpnr\b", "PNR / booking reference"),
    (r"\bpassenger\s*(name|id|record|details?)\b", "passenger records"),
    (r"\bbooking\s*(id|reference|number|details?)\b", "booking details"),
    (r"\bticket\s*(number|id|details?)\b", "ticket numbers"),
    (r"\bcustomer\s*(id|name|record|details?)\b", "customer records"),
    (r"\bemail\b", "email addresses"),
    (r"\bphone\s*number\b", "phone numbers"),
]

_SQL_KEYWORDS = {
    "select", "from", "where", "and", "or", "not", "null", "is", "in", "like",
    "ilike", "between", "order", "by", "asc", "desc", "limit", "offset", "as",
    "distinct", "count", "sum", "avg", "min", "max", "lower", "upper", "true", "false",
    "flights", "on", "join", "inner", "left", "right", "group", "having",
}

PNR_NOT_SUPPORTED_MESSAGE = (
    "Sorry, I cannot look up bookings by PNR or booking reference. "
    "This support system only answers questions about flight schedules and status.\n\n"
    "Please ask in plain English, for example:\n"
    "• What is the status of flight SG528?\n"
    "• Are there flights from Delhi to Mumbai on 2026-11-11?\n"
    "• What gate and terminal is assigned to flight AI695?\n\n"
    "Do not type SQL queries — just describe what you need in everyday language."
)

UNSUPPORTED_FLIGHT_LOOKUP_MESSAGE = (
    "Sorry, I cannot access passenger, booking, or ticket information. "
    "I can only help with flight schedule data such as flight number, route, date, "
    "status, gate, terminal, seats, and fare.\n\n"
    "Please ask correctly, for example:\n"
    "• What is the status of flight SG528?\n"
    "• Show flights from Delhi to Nagpur on 2026-11-11."
)

NO_CRITERIA_MESSAGE = (
    "I couldn't understand which flight you are looking for.\n\n"
    "Please ask correctly using one of these details:\n"
    "• Flight number — e.g., What is the status of flight AI695?\n"
    "• Route — e.g., Are there flights from Delhi to Mumbai?\n"
    "• Date — e.g., List flights from Chennai to Hyderabad on 2026-11-10."
)

SQL_NOT_ALLOWED_MESSAGE = (
    "Please do not type SQL queries. Ask your question in plain English instead.\n\n"
    "Examples:\n"
    "• What is the status of flight SG528?\n"
    "• How many seats are available on flight AI101?\n"
    "• Are there flights from Delhi to Goa under Rs. 7000?"
)


def _mentions_pnr(query: str) -> bool:
    return bool(re.search(r"\bpnr\b", query, re.IGNORECASE))


def is_sql_style_query(query: str) -> bool:
    lowered = query.lower().strip()
    if re.match(r"^\s*(select|insert|update|delete|drop)\b", lowered):
        return True
    if re.search(r"\bfrom\s+flights\b", lowered):
        return True
    if re.search(r"\bselect\s+.+\s+from\s+flights\b", lowered):
        return True
    return False


def get_unsupported_field_message(query: str) -> str | None:
    if _mentions_pnr(query):
        return PNR_NOT_SUPPORTED_MESSAGE

    lowered = query.lower()
    for pattern, _label in _UNSUPPORTED_FIELD_PATTERNS:
        if re.search(pattern, lowered):
            return UNSUPPORTED_FLIGHT_LOOKUP_MESSAGE
    return None


def get_invalid_query_message(query: str) -> str | None:
    unsupported = get_unsupported_field_message(query)
    if unsupported:
        return unsupported

    if is_sql_style_query(query):
        return SQL_NOT_ALLOWED_MESSAGE

    return None


def _strip_string_literals(sql: str) -> str:
    return re.sub(r"'[^']*'", "''", sql)


def _extract_sql_identifiers(sql: str) -> set[str]:
    without_literals = _strip_string_literals(sql)
    tokens = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", without_literals)
    return {token.lower() for token in tokens}


def validate_sql_columns(sql: str) -> str | None:
    unsupported = get_unsupported_field_message(sql)
    if unsupported:
        return unsupported

    identifiers = _extract_sql_identifiers(sql)
    unknown = {
        name
        for name in identifiers
        if name not in _SQL_KEYWORDS and name not in FLIGHTS_COLUMNS
    }
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        return (
            f"The flights table does not have these fields: {unknown_list}. "
            "Available fields are flight number, route, schedule, status, gate, "
            "terminal, aircraft, seats, and fare."
        )
    return None


def is_raw_sql_query(query: str) -> bool:
    return bool(re.match(r"^\s*select\b", query, re.IGNORECASE))


def is_broad_unfiltered_query(sql: str) -> bool:
    normalized = re.sub(r"\s+", " ", sql.strip().rstrip(";").lower())
    if " where " in normalized:
        return False
    return bool(re.match(r"^select\b", normalized))
