from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "football-analyzer"
    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str

    # ─── API-Football (Sudamérica + competiciones fuera de football-data.org) ──
    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"

    # ─── football-data.org (ligas europeas grandes, temporada actual) ─────────
    football_data_api_key: str = ""
    football_data_base_url: str = "https://api.football-data.org/v4"

    # ─── The Odds API (cuotas, independiente de la fuente de estadísticas) ────
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()