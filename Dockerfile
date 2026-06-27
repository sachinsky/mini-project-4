FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_BASE_URL=http://127.0.0.1:8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

EXPOSE 8000 8501 8502

CMD ["sh", "-c", "python scripts/load_flights.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true & streamlit run dashboard_app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true & wait"]
