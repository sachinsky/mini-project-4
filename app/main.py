from fastapi import FastAPI, HTTPException

from .database import Base, engine
from .pipeline import process_user_query
from .schemas import HealthResponse, SupportQuery, SupportResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Airline AI Support API",
    description=(
        "REST API for the AI-powered airline customer support system.\n\n"
        "**Features:**\n"
        "- Input/output guardrails\n"
        "- Flight data lookup via SQL (PostgreSQL/SQLite)\n"
        "- Policy and FAQ answers via RAG\n\n"
        "Use **POST /support/query** to send a user question and receive a JSON response."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Check whether the API server is running."""
    return HealthResponse(status="ok")


@app.post("/support/query", response_model=SupportResponse, tags=["Support"])
def support_query(payload: SupportQuery) -> SupportResponse:
    """
    Process an airline support query through the full backend pipeline.

    The request is validated by input guardrails, classified, routed to SQL or RAG
    as needed, and the final answer is checked by output guardrails before returning.
    """
    try:
        result = process_user_query(payload.query.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}") from exc

    return SupportResponse(
        response=result.response,
        category=result.category,
        input_guardrail=result.input_guardrail,
        output_guardrail=result.output_guardrail,
    )
