# Airline AI Customer Support Demo

This project creates an end-to-end airline customer support system inside GitHub Codespaces.
It combines the flight schedule dataset with a FastAPI backend, a retrieval-guided support agent, and a Streamlit frontend.

## What it includes

- `app/main.py`: FastAPI backend exposing `/support/query`.
- `app/support.py`: support agent that retrieves flight data and policy guidance.
- `scripts/load_flights.py`: loads `Flights_Schedule_Data_v1.csv` into a SQL database.
- `streamlit_app.py`: simple Streamlit UI to submit user queries and display answers.
- `requirements.txt`: Python dependencies for backend and frontend.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Load flight data into the database:

```bash
python scripts/load_flights.py
```

3. Start the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Launch the Streamlit UI:

```bash
streamlit run streamlit_app.py
```

## How it works

- The backend uses SQLAlchemy to read flight data from `flights.db` or from a PostgreSQL database provided via `DATABASE_URL`.
- `CustomerSupportAgent` retrieves matching flights and selects a relevant policy snippet.
- If `OPENAI_API_KEY` is set, the backend will use OpenAI ChatCompletion to produce a richer response.
- Otherwise, it falls back to a helpful, rule-based summary.

## Optional PostgreSQL configuration

To use PostgreSQL instead of SQLite, set `DATABASE_URL` in a `.env` file or environment variable:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/airline
```

Then run `python scripts/load_flights.py` again to populate the database.

## Example queries

- "What is the status of flight IX149?"
- "Is my flight from BLR to PNQ delayed?"
- "What is the baggage policy for this airline?"
- "How can I get a refund for a cancelled flight?"
