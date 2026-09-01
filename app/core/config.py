from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = 'Formaslov API'
    debug: bool = True
    secret_key: str
    jwt_access_token_lifetime: int = 86400
    jwt_refresh_token_lifetime: int = 86400
    cors_allowed_origins: str = (
        'http://localhost:3000,http://127.0.0.1:3000'
    )
    redis_url: str | None = None
    cache_ttl_seconds: int = 300
    celery_broker_url: str = 'amqp://guest:guest@localhost:5672//'
    import_storage_dir: Path = Path('/tmp/formaslov_imports')
    export_storage_dir: Path = Path('/tmp/formaslov_exports')
    max_archive_size: int = 10 * 1024 * 1024
    max_archive_files: int = 100
    max_document_size: int = 2 * 1024 * 1024
    allowed_document_extensions: str = '.txt,.docx'
    database_url: str | None = None
    postgres_user: str = 'formaslov'
    postgres_password: str = 'formaslov'
    postgres_db: str = 'formaslov'
    db_host: str = 'localhost'
    db_port: int = 5432

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if (
            isinstance(value, str)
            and value.lower() in {'release', 'prod', 'production'}
        ):
            return False
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        url = URL.create(
            drivername='postgresql+asyncpg',
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.db_host,
            port=self.db_port,
            database=self.postgres_db,
        )
        return url.render_as_string(hide_password=False)

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(',')
            if origin.strip()
        ]

    @property
    def document_extensions(self) -> set[str]:
        return {
            extension.strip().lower()
            for extension in self.allowed_document_extensions.split(',')
            if extension.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
