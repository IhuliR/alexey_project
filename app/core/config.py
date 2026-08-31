from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = 'Formaslov API'
    debug: bool = True
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
