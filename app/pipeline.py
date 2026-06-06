import re
from dataclasses import dataclass

from .chains import (
    build_input_classifier_chain,
    build_input_guardrail_chain,
    build_output_guardrail_chain,
    build_rag_chain,
    build_sql_generation_chain,
    get_sql_agent,
    has_llm_credentials,
)
from .fallback import run_rag_fallback, run_sql_fallback
from .fallback import summarize_sql_results
from .query_validation import get_invalid_query_message, get_unsupported_field_message, is_raw_sql_query
from .sql_executor import execute_sql_query

_INPUT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+prompt",
    r"reveal\s+(the\s+)?(system|hidden|secret)",
    r"override\s+instructions",
    r"jailbreak",
]
_HARMFUL_PATTERNS = [
    r"\bbomb\b",
    r"bypass\s+(airport\s+)?security",
    r"how\s+can\s+i\s+hack",
]
_SENSITIVE_DATA_PATTERNS = [
    r"customer\s+records",
    r"export\s+(the\s+)?(complete\s+)?(flight\s+)?database",
    r"show\s+me\s+all\s+customer",
    r"dump\s+(the\s+)?database",
]

_SQL_KEYWORDS = [
    "flight",
    "status",
    "delayed",
    "delay",
    "cancelled",
    "canceled",
    "gate",
    "terminal",
    "seat",
    "aircraft",
    "departure",
    "arrival",
    "fare",
    "available",
    "route",
    "from ",
    " to ",
]
_POLICY_KEYWORDS = [
    "baggage",
    "bag ",
    "luggage",
    "refund",
    "cancel policy",
    "cancellation policy",
    "reschedule",
    "wheelchair",
    "pet",
    "power bank",
    "prohibited",
    "assistance",
    "document",
    "musical instrument",
    "policy",
    "allowance",
]
_OUT_OF_CONTEXT_KEYWORDS = [
    "capital of",
    "world cup",
    "football world cup",
    "cricket world cup",
    "generative ai",
    "explain ai",
]


@dataclass
class QueryResult:
    response: str
    category: str | None = None
    input_guardrail: str | None = None
    output_guardrail: str | None = None
    generated_sql: str | None = None


def _rule_based_input_guardrail(query: str) -> str | None:
    lowered = query.lower()
    for pattern in _INPUT_INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return "UNSAFE: Prompt injection attempt to reveal system instructions."
    for pattern in _HARMFUL_PATTERNS:
        if re.search(pattern, lowered):
            return "UNSAFE: Request for harmful or illegal activity."
    for pattern in _SENSITIVE_DATA_PATTERNS:
        if re.search(pattern, lowered):
            return "UNSAFE: Request for sensitive or private data."
    return None


def _rule_based_classifier(query: str) -> str:
    lowered = query.lower()
    if any(term in lowered for term in _OUT_OF_CONTEXT_KEYWORDS):
        return "Out of Context"
    if any(term in lowered for term in _POLICY_KEYWORDS):
        return "Non SQL"
    if any(term in lowered for term in _SQL_KEYWORDS) or re.search(r"\b[A-Z]{2,3}\d{1,4}\b", query.upper()):
        return "Need SQL"
    return "Out of Context"


def _normalize_category(category: str) -> str:
    cleaned = category.strip()
    if "Need SQL" in cleaned:
        return "Need SQL"
    if "Non SQL" in cleaned:
        return "Non SQL"
    if "Out of Context" in cleaned:
        return "Out of Context"
    return _rule_based_classifier(cleaned)


def _normalize_guardrail_result(result: str) -> str:
    cleaned = result.strip()
    if cleaned.upper().startswith("UNSAFE"):
        return cleaned if ":" in cleaned else "UNSAFE: flagged content"
    return "SAFE"


def _handle_raw_sql(user_input: str) -> tuple[str, str | None]:
    results = execute_sql_query(user_input)
    if isinstance(results, str):
        return results.replace("Error executing query: ", ""), user_input
    return summarize_sql_results(user_input, results), user_input


def run_flight_query_agent(user_input: str) -> tuple[str, str | None]:
    unsupported = get_unsupported_field_message(user_input)
    if unsupported:
        return unsupported, None

    if is_raw_sql_query(user_input):
        return _handle_raw_sql(user_input)

    sql_generation_chain = build_sql_generation_chain()
    sql_query = sql_generation_chain.invoke({"query": user_input}).strip()
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

    preview = execute_sql_query(sql_query)
    if isinstance(preview, str) and preview.startswith("Error executing query:"):
        return preview.replace("Error executing query: ", ""), sql_query

    agent = get_sql_agent()
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"User Question: {user_input}. "
                        f"SQL query to use: {sql_query}"
                    ),
                }
            ]
        }
    )
    return result["messages"][-1].content, sql_query


def process_user_query(query: str) -> QueryResult:
    invalid_message = get_invalid_query_message(query)
    if invalid_message:
        return QueryResult(
            response=invalid_message,
            category="Unsupported",
            input_guardrail="SAFE",
            output_guardrail="SAFE",
        )

    rule_input_flag = _rule_based_input_guardrail(query)
    if rule_input_flag:
        return QueryResult(
            response=f"Your query was flagged: {rule_input_flag}",
            input_guardrail=rule_input_flag,
        )

    if has_llm_credentials():
        input_guardrail_chain = build_input_guardrail_chain()
        input_check = _normalize_guardrail_result(
            input_guardrail_chain.invoke({"query": query})
        )
    else:
        input_check = "SAFE"

    if input_check.startswith("UNSAFE"):
        return QueryResult(
            response=f"Your query was flagged: {input_check}",
            input_guardrail=input_check,
        )

    if has_llm_credentials():
        input_classifier_chain = build_input_classifier_chain()
        category = _normalize_category(input_classifier_chain.invoke({"query": query}))
    else:
        category = _rule_based_classifier(query)

    generated_sql = None
    raw_response = ""

    if category == "Need SQL":
        if has_llm_credentials():
            raw_response, generated_sql = run_flight_query_agent(query)
        else:
            raw_response, generated_sql = run_sql_fallback(query)
    elif category == "Non SQL":
        if has_llm_credentials():
            rag_chain = build_rag_chain()
            raw_response = rag_chain.invoke(query)
        else:
            raw_response = run_rag_fallback(query)
    else:
        raw_response = (
            "I am designed to assist with airline-related queries. "
            "Please ask me something about flights, policies, or services."
        )

    if has_llm_credentials():
        output_guardrail_chain = build_output_guardrail_chain()
        output_check = _normalize_guardrail_result(
            output_guardrail_chain.invoke({"response": raw_response})
        )
    else:
        output_check = "SAFE"

    if output_check.startswith("UNSAFE"):
        return QueryResult(
            response=f"Response flagged by output guardrail: {output_check}",
            category=category,
            input_guardrail=input_check,
            output_guardrail=output_check,
            generated_sql=generated_sql,
        )

    return QueryResult(
        response=raw_response,
        category=category,
        input_guardrail=input_check,
        output_guardrail=output_check,
        generated_sql=generated_sql,
    )
