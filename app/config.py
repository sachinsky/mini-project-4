from pathlib import Path

from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = "sqlite:///./flights.db"
    flight_csv: str = str(ROOT_DIR / "Flights_Schedule_Data_v1.csv")
    knowledge_base_pdf: str = str(ROOT_DIR / "Knowledge_Base_for_Airline_Info_and_FAQs.pdf")
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    hf_token: str | None = None
    pinecone_api_key: str | None = None
    pinecone_index_name: str = "airline-faq-index"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    openai_embedding_model: str = "text-embedding-3-small"
    rag_fetch_k: int = 8
    rag_k: int = 2
    rag_lambda_mult: float = 0.8
    api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
