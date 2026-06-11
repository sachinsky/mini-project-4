from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., min_length=1, description="Message text")


class SupportQuery(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about flights, policies, or airline services.",
        examples=["What is the status of flight SG528?"],
    )
    conversation_history: list[ChatTurn] = Field(
        default_factory=list,
        description="Optional prior chat turns for multi-turn grounded responses.",
    )
    session_id: str | None = Field(
        None,
        description="Optional client session id used to group multi-turn conversations in analytics.",
    )


class SupportResponse(BaseModel):
    response: str = Field(..., description="Final answer returned to the user.")
    category: str | None = Field(
        None,
        description="Routing category: Need SQL, Non SQL, Out of Context, Unsupported, Clarification, or Safety.",
    )
    input_guardrail: str | None = Field(None, description="Input guardrail result (SAFE or UNSAFE).")
    output_guardrail: str | None = Field(None, description="Output guardrail result (SAFE or UNSAFE).")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "The current status of flight SG528 is Cancelled.",
                    "category": "Need SQL",
                    "input_guardrail": "SAFE",
                    "output_guardrail": "SAFE",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])


class CategoryCount(BaseModel):
    category: str
    count: int


class AnalyticsSummary(BaseModel):
    total_queries: int
    queries_today: int
    period_days: int
    category_breakdown: list[CategoryCount]


class TopQueryItem(BaseModel):
    rank: int
    query: str
    normalized_query: str
    count: int
    latest_category: str | None = None
    last_seen: str | None = None


class TopQueriesResponse(BaseModel):
    period_days: int
    limit: int
    items: list[TopQueryItem]


class RecentConversationItem(BaseModel):
    id: int
    query: str
    response: str
    category: str | None = None
    session_id: str | None = None
    created_at: str | None = None


class RecentConversationsResponse(BaseModel):
    period_days: int
    limit: int
    items: list[RecentConversationItem]


class DailyVolumeItem(BaseModel):
    date: str
    count: int


class DailyVolumeResponse(BaseModel):
    period_days: int
    items: list[DailyVolumeItem]
