from pydantic import BaseModel, Field


class SupportQuery(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about flights, policies, or airline services.",
        examples=["What is the status of flight SG528?"],
    )


class SupportResponse(BaseModel):
    response: str = Field(..., description="Final answer returned to the user.")
    category: str | None = Field(
        None,
        description="Routing category: Need SQL, Non SQL, Out of Context, or Unsupported.",
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
