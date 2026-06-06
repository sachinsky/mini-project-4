import re

from sqlalchemy import text

from .config import settings
from .database import engine
from .query_validation import is_broad_unfiltered_query, validate_sql_columns

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)
_ILIKE_PATTERN = re.compile(
    r"(\w+)\s+ILIKE\s+'([^']*)'",
    re.IGNORECASE,
)


def _normalize_query_for_dialect(query: str) -> str:
    if not settings.database_url.startswith("sqlite"):
        return query

    def _replace_ilike(match: re.Match[str]) -> str:
        column, value = match.group(1), match.group(2)
        return f"LOWER({column}) LIKE LOWER('{value}')"

    return _ILIKE_PATTERN.sub(_replace_ilike, query)


def execute_sql_query(query: str) -> list[dict] | str:
    """Execute a read-only SQL query against the flights table."""
    cleaned = _normalize_query_for_dialect(query.strip().rstrip(";"))
    if not cleaned.upper().startswith("SELECT"):
        return "Error executing query: Only SELECT queries are allowed."

    if _FORBIDDEN_KEYWORDS.search(cleaned):
        return "Error executing query: Query contains forbidden operations."

    column_error = validate_sql_columns(cleaned)
    if column_error:
        return f"Error executing query: {column_error}"

    if is_broad_unfiltered_query(cleaned):
        return (
            "Error executing query: Query is too broad. Please filter by flight number, "
            "route, date, or status."
        )

    try:
        with engine.connect() as conn:
            result = conn.execute(text(cleaned))
            colnames = list(result.keys())
            rows = result.fetchall()
            return [dict(zip(colnames, row)) for row in rows]
    except Exception as exc:
        return f"Error executing query: {exc}"
