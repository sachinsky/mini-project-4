from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_no = Column(String, index=True, nullable=False)
    airline_code = Column(String, nullable=False)
    airline_name = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_date = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)
    arrival_date = Column(String, nullable=False)
    arrival_time = Column(String, nullable=False)
    status = Column(String, nullable=False)
    delay_minutes = Column(Integer, nullable=False)
    delay_reason = Column(Text, nullable=True)
    terminal = Column(String, nullable=True)
    gate = Column(String, nullable=True)
    aircraft_type = Column(String, nullable=True)
    seats_total = Column(Integer, nullable=True)
    seats_booked = Column(Integer, nullable=True)
    fare_inr = Column(Integer, nullable=True)


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    normalized_query = Column(String(500), index=True, nullable=False)
    response = Column(Text, nullable=False)
    category = Column(String(50), index=True, nullable=True)
    input_guardrail = Column(String(100), nullable=True)
    output_guardrail = Column(String(100), nullable=True)
    session_id = Column(String(64), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
