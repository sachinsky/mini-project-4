from pydantic import BaseModel


class FlightSchema(BaseModel):
    id: int
    flight_no: str
    airline_code: str
    airline_name: str
    origin: str
    destination: str
    departure_date: str
    departure_time: str
    arrival_date: str
    arrival_time: str
    status: str
    delay_minutes: int
    delay_reason: str | None = None
    terminal: str | None = None
    gate: str | None = None
    aircraft_type: str | None = None
    seats_total: int | None = None
    seats_booked: int | None = None
    fare_inr: int | None = None

    model_config = {"from_attributes": True}


class SupportQuery(BaseModel):
    query: str


class SupportResponse(BaseModel):
    answer: str
    retrieved_flights: list[FlightSchema] = []
    knowledge_snippet: str | None = None
