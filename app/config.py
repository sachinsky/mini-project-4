from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./flights.db"
    flight_csv: str = "Flights_Schedule_Data_v1.csv"
    openai_api_key: str | None = None
    api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
