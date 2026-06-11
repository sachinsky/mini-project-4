"""Customer-facing messages for guardrails and safety responses."""


def to_polite_input_response(guardrail_result: str) -> str:
    """Convert an internal UNSAFE guardrail result into a polite user response."""
    lowered = guardrail_result.lower()

    if any(term in lowered for term in ("prompt injection", "system prompt", "system instructions")):
        return (
            "I'm here to help with airline travel questions such as flight status, "
            "baggage, bookings, and airline policies. I'm unable to help with that "
            "request, but please feel free to ask anything about your flight or journey."
        )

    if any(term in lowered for term in ("harmful", "illegal", "toxic", "violence", "bomb", "security")):
        return (
            "I'm sorry, but I'm unable to assist with that request. "
            "If you need help with flights, baggage, refunds, or travel policies, "
            "I'll be glad to support you."
        )

    if any(term in lowered for term in ("sensitive", "private", "customer record", "personal data")):
        return (
            "For your privacy and security, I cannot access private customer records "
            "or personal account details. You can ask me about flight schedules, status, "
            "gates, baggage rules, or cancellation policies, and I'll be happy to help."
        )

    return (
        "I'm sorry, I wasn't able to process that request. "
        "Please ask me about flights, travel policies, or airline services, "
        "and I'll do my best to help."
    )


def to_polite_output_response(guardrail_result: str) -> str:
    """Convert an output guardrail block into a polite user response."""
    return (
        "I apologize — I wasn't able to provide a reliable answer to that question. "
        "Could you please rephrase it as an airline-related query? For example, you can ask "
        "about flight status, baggage allowance, or cancellation rules."
    )
