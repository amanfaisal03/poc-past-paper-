from collections.abc import Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://pastpaper:password@localhost:5433/past_paper"
    )
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmins"
    minio_bucket_name: str = "past-papers"
    minio_public_endpoint: str | None = None
    llama_cloud_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llama_parse_tier: str = "agentic"
    material_toc_max_pages: int = 12
    parsing_trace: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
