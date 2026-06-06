import re
from typing import Any

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

from sqlalchemy.orm import Session

from .config import settings
from .models import Flight


POLICY_SNIPPETS = {
    "baggage": (
        "Baggage Policy:\n"
        "- Carry-on allowance is typically one small bag plus one personal item.\n"
        "- Checked baggage allowance depends on fare class, frequent flyer status, and route.\n"
        "- Excess baggage fees apply for overweight or oversized items."
    ),
    "refund": (
        "Refund Policy:\n"
        "- Refund eligibility depends on the fare rules and the ticket type.\n"
        "- Fully refundable tickets are typically refunded to the original payment method.\n"
        "- Non-refundable tickets may receive a credit voucher instead of a cash refund."
    ),
    "cancellation": (
        "Cancellation Policy:\n"
        "- If a flight is cancelled, the airline can rebook you on the next available flight or issue a refund.\n"
        "- Fees may be waived for cancellations caused by the airline.\n"
        "- Always confirm your options through official customer support channels."
    ),
    "change": (
        "Booking Change Policy:\n"
        "- Most airlines allow date or route changes for a fee depending on the fare rules.\n"
        "- Changes are typically easier when made well before departure.\n"
        "- Some promotional fares have restricted or no change options."
    ),
    "delay": (
        "Delay and Status Policy:\n"
        "- Flight status updates are available in real time and should be confirmed before departure.\n"
        "- Minor delays are common and may not affect connecting flights.\n"
        "- For significant delays, airlines often offer rebooking or meal vouchers according to policy."
    ),
}


class CustomerSupportAgent:
    def __init__(self, db: Session):
        self.db = db

    def search_flights(self, query: str) -> list[Flight]:
        normalized = query.upper()
        flight_number = self._extract_flight_number(normalized)
        if flight_number:
            return self.db.query(Flight).filter(Flight.flight_no == flight_number).limit(5).all()

        origin = self._extract_location(normalized, "origin")
        destination = self._extract_location(normalized, "destination")

        query_base = self.db.query(Flight)
        if origin and destination:
            query_base = query_base.filter(Flight.origin == origin, Flight.destination == destination)
        elif origin:
            query_base = query_base.filter(Flight.origin == origin)
        elif destination:
            query_base = query_base.filter(Flight.destination == destination)
        else:
            query_base = query_base.filter(
                (Flight.flight_no.ilike(f"%{normalized}%"))
                | (Flight.airline_name.ilike(f"%{normalized}%"))
                | (Flight.origin.ilike(f"%{normalized}%"))
                | (Flight.destination.ilike(f"%{normalized}%"))
            )

        return query_base.limit(5).all()

    def handle_query(self, query: str) -> tuple[str, list[Flight], str | None]:
        flights = self.search_flights(query)
        policy_snippet = self._retrieve_policy_snippet(query)
        response = self._compose_response(query, flights, policy_snippet)
        return response, flights, policy_snippet

    def _compose_response(self, query: str, flights: list[Flight], policy_snippet: str | None) -> str:
        llm_answer = self._call_llm(query, flights, policy_snippet)
        if llm_answer:
            return llm_answer
        return self._fallback_answer(query, flights, policy_snippet)

    def _call_llm(self, query: str, flights: list[Flight], policy_snippet: str | None) -> str | None:
        if openai is None or settings.openai_api_key is None:
            return None

        openai.api_key = settings.openai_api_key
        system_messages = (
            "You are an airline customer support assistant. Answer questions about flight status, delays, cancellations, and baggage policy using the provided flight and policy details."
        )
        flight_payload = self._render_flight_context(flights)
        knowledge_context = policy_snippet or "No additional policy snippet available."
        user_prompt = (
            f"Customer query: {query}\n\n"
            f"Flight context:\n{flight_payload}\n\n"
            f"Policy context:\n{knowledge_context}\n"
            "If you cannot find an exact answer, provide a safe and helpful explanation."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_messages},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=350,
        )
        return response.choices[0].message.content.strip()

    def _render_flight_context(self, flights: list[Flight]) -> str:
        if not flights:
            return "No matching flights were retrieved from the database."
        rows = []
        for flight in flights:
            rows.append(
                f"{flight.flight_no} | {flight.airline_name} | {flight.origin}->{flight.destination} "
                f"depart {flight.departure_date} {flight.departure_time} arrive {flight.arrival_date} {flight.arrival_time} "
                f"status: {flight.status} delay: {flight.delay_minutes} min terminal: {flight.terminal} gate: {flight.gate}"
            )
        return "\n".join(rows)

    def _fallback_answer(self, query: str, flights: list[Flight], policy_snippet: str | None) -> str:
        if not flights:
            base = "I couldn't find a matching flight record in the system."
            if policy_snippet:
                return f"{base} Here is some airline policy information that may help:\n\n{policy_snippet}"
            return base

        summary = [
            "I found the following matching flight(s):"
        ]
        for flight in flights:
            summary.append(
                f"- {flight.flight_no} ({flight.airline_name}) from {flight.origin} to {flight.destination} "
                f"on {flight.departure_date} at {flight.departure_time}: {flight.status}."
            )
            if flight.delay_minutes > 0:
                reason = f" Reason: {flight.delay_reason}." if flight.delay_reason else ""
                summary.append(f"  Delay: {flight.delay_minutes} minutes.{reason}")
        if policy_snippet:
            summary.append("\nPolicy guidance:\n" + policy_snippet)
        return "\n".join(summary)

    def _retrieve_policy_snippet(self, query: str) -> str | None:
        normalized = query.lower()
        if any(term in normalized for term in ["bag", "baggage", "luggage"]):
            return POLICY_SNIPPETS["baggage"]
        if any(term in normalized for term in ["refund", "money back"]):
            return POLICY_SNIPPETS["refund"]
        if any(term in normalized for term in ["cancel", "cancelled"]):
            return POLICY_SNIPPETS["cancellation"]
        if any(term in normalized for term in ["change", "reschedule", "modify"]):
            return POLICY_SNIPPETS["change"]
        if any(term in normalized for term in ["delay", "status"]):
            return POLICY_SNIPPETS["delay"]
        return None

    def _extract_flight_number(self, query: str) -> str | None:
        match = re.search(r"\b([A-Z]{2,3}\d{1,4})\b", query)
        return match.group(1) if match else None

    def _extract_location(self, query: str, mode: str) -> str | None:
        if mode == "origin":
            pattern = r"from\s+([A-Z]{3})"
        else:
            pattern = r"to\s+([A-Z]{3})"
        match = re.search(pattern, query)
        return match.group(1) if match else None
