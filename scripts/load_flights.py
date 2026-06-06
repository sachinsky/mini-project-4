import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import Flight


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def load_flight_data(csv_path: str) -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        session.query(Flight).delete()
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                flight = Flight(
                    id=parse_int(row.get("id")),
                    flight_no=row.get("flight_no", "").strip(),
                    airline_code=row.get("airline_code", "").strip(),
                    airline_name=row.get("airline_name", "").strip(),
                    origin=row.get("origin", "").strip(),
                    destination=row.get("destination", "").strip(),
                    departure_date=row.get("departure_date", "").strip(),
                    departure_time=row.get("departure_time", "").strip(),
                    arrival_date=row.get("arrival_date", "").strip(),
                    arrival_time=row.get("arrival_time", "").strip(),
                    status=row.get("status", "").strip(),
                    delay_minutes=parse_int(row.get("delay_minutes")),
                    delay_reason=row.get("delay_reason", "").strip(),
                    terminal=row.get("terminal", "").strip(),
                    gate=row.get("gate", "").strip(),
                    aircraft_type=row.get("aircraft_type", "").strip(),
                    seats_total=parse_int(row.get("seats_total")),
                    seats_booked=parse_int(row.get("seats_booked")),
                    fare_inr=parse_int(row.get("fare_inr")),
                )
                session.add(flight)
        session.commit()
        print(f"Loaded flights from {csv_path}")
    finally:
        session.close()


if __name__ == "__main__":
    load_flight_data(settings.flight_csv)
