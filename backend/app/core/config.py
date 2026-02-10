from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "POL Real Estate"
    API_V1_PREFIX: str = "/api/v1"

    POSTGRES_USER: str = "pol"
    POSTGRES_PASSWORD: str = "pol_dev_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pol_real_estate"

    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    DOLAR_API_BASE_URL: str = "https://dolarapi.com/v1"
    BLUELYTICS_API_URL: str = "https://api.bluelytics.com.ar/v2"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            url = url.replace("sslmode=", "ssl=")
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
