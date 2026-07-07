from app.core.config import Settings


def test_database_url_uses_asyncpg_driver() -> None:
    settings = Settings(
        POSTGRES_USER="nova",
        POSTGRES_PASSWORD="secret",
        POSTGRES_HOST="postgres",
        POSTGRES_PORT=5432,
        POSTGRES_DB="core",
    )

    assert settings.database_url == "postgresql+asyncpg://nova:secret@postgres:5432/core"
