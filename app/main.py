from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .schemas import SupportQuery, SupportResponse
from .support import CustomerSupportAgent

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="Airline AI Support",
    description="FastAPI backend for airline customer support using flight data and retrieval-based knowledge.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/support/query", response_model=SupportResponse)
def support_query(payload: SupportQuery, db: Session = Depends(get_db)) -> SupportResponse:
    agent = CustomerSupportAgent(db)
    answer, flights, knowledge_snippet = agent.handle_query(payload.query)
    return SupportResponse(answer=answer, retrieved_flights=flights, knowledge_snippet=knowledge_snippet)
