from fastapi import FastAPI, HTTPException, Query

from .analytics import (
    get_analytics_summary,
    get_daily_volume,
    get_recent_conversations,
    get_top_queries,
    log_conversation,
)
from .database import Base, engine
from .pipeline import process_user_query
from .schemas import (
    AnalyticsSummary,
    CategoryCount,
    DailyVolumeItem,
    DailyVolumeResponse,
    HealthResponse,
    RecentConversationItem,
    RecentConversationsResponse,
    SupportQuery,
    SupportResponse,
    TopQueriesResponse,
    TopQueryItem,
)

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
        history = [
            {"role": turn.role, "content": turn.content}
            for turn in payload.conversation_history
        ]
        result = process_user_query(payload.query.strip(), conversation_history=history)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}") from exc

    log_conversation(
        query=payload.query.strip(),
        response=result.response,
        category=result.category,
        input_guardrail=result.input_guardrail,
        output_guardrail=result.output_guardrail,
        session_id=payload.session_id,
    )

    return SupportResponse(
        response=result.response,
        category=result.category,
        input_guardrail=result.input_guardrail,
        output_guardrail=result.output_guardrail,
    )


@app.get("/analytics/summary", response_model=AnalyticsSummary, tags=["Analytics"])
def analytics_summary(days: int = Query(30, ge=1, le=365)) -> AnalyticsSummary:
    """High-level support volume and category breakdown for the airline ops team."""
    summary = get_analytics_summary(days=days)
    return AnalyticsSummary(
        total_queries=summary["total_queries"],
        queries_today=summary["queries_today"],
        period_days=summary["period_days"],
        category_breakdown=[CategoryCount(**item) for item in summary["category_breakdown"]],
    )


@app.get("/analytics/top-queries", response_model=TopQueriesResponse, tags=["Analytics"])
def analytics_top_queries(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
) -> TopQueriesResponse:
    """Most frequent customer queries so the airline team can spot recurring issues."""
    items = get_top_queries(limit=limit, days=days)
    return TopQueriesResponse(
        period_days=days,
        limit=limit,
        items=[TopQueryItem(**item) for item in items],
    )


@app.get("/analytics/recent", response_model=RecentConversationsResponse, tags=["Analytics"])
def analytics_recent(
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(30, ge=1, le=365),
) -> RecentConversationsResponse:
    """Latest logged conversations for operational review."""
    items = get_recent_conversations(limit=limit, days=days)
    return RecentConversationsResponse(
        period_days=days,
        limit=limit,
        items=[RecentConversationItem(**item) for item in items],
    )


@app.get("/analytics/daily-volume", response_model=DailyVolumeResponse, tags=["Analytics"])
def analytics_daily_volume(days: int = Query(30, ge=1, le=365)) -> DailyVolumeResponse:
    """Daily query volume for trend charts."""
    items = get_daily_volume(days=days)
    return DailyVolumeResponse(
        period_days=days,
        items=[DailyVolumeItem(**item) for item in items],
    )
