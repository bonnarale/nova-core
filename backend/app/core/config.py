from functools import lru_cache
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="NOVA CORE", alias="PROJECT_NAME")
    environment: str = Field(default="production", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    allowed_origins: str = Field(default="http://localhost:5173,http://localhost:3000", alias="ALLOWED_ORIGINS")

    postgres_db: str = Field(default="nova_core", alias="POSTGRES_DB")
    postgres_user: str = Field(default="nova_core", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change-this-postgres-password", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str = Field(default="change-this-redis-password", alias="REDIS_PASSWORD")

    chroma_host: str = Field(default="chroma", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")

    ollama_host: str = Field(default="ollama", alias="OLLAMA_HOST")
    ollama_port: int = Field(default=11434, alias="OLLAMA_PORT")
    ollama_embedding_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL")

    @property
    def database_url(self) -> str:
        """Database URL with hidden password — safe for logging/display."""
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )
        return url.render_as_string(hide_password=True)

    @property
    def database_url_raw(self) -> str:
        """Database URL with password — for actual connection only."""
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )
        return url.render_as_string(hide_password=False)

    @property
    def redis_url(self) -> str:
        password = quote(self.redis_password, safe="")
        return f"redis://:{password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    @property
    def ollama_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"

    # Autonomous execution settings
    nova_autonomous_interval_seconds: int = Field(default=3600, alias="NOVA_AUTONOMOUS_INTERVAL_SECONDS")
    nova_autonomous_user_id: str = Field(default="", alias="NOVA_AUTONOMOUS_USER_ID")
    nova_autonomous_enabled: bool = Field(default=True, alias="NOVA_AUTONOMOUS_ENABLED")
    nova_autonomous_max_goals_per_cycle: int = Field(default=5, alias="NOVA_AUTONOMOUS_MAX_GOALS_PER_CYCLE")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
