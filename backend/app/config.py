from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/leadforge"
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def asyncpg_url(self) -> str:
        """Convert SQLAlchemy-style URL to plain postgres URL for asyncpg."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
