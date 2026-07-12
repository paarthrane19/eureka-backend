from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Railway's MongoDB plugin (and most managed Mongo add-ons) inject
    # MONGODB_URI; MONGO_URI is kept for backwards compatibility with local dev.
    mongo_uri: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI"),
    )
    mongo_db: str = "eureka"

    jwt_secret: str = "dev-secret-change-me-to-something-long-and-random"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200  # 30 days

    # Comma-separated list of allowed browser origins for CORS. Defaults cover
    # local web dev and the deployed Vercel frontend. Native/mobile clients
    # (Expo Go, etc.) aren't subject to CORS, so this only affects browsers.
    cors_origins: str = (
        "http://localhost:3000,https://projecteureka.vercel.app"
    )

    # The eight canonical science categories used across the app.
    categories: list[str] = [
        "Physics",
        "Astronomy",
        "Biology",
        "Chemistry",
        "Math",
        "Earth Science",
        "Technology",
        "Medicine",
    ]

    # Automated content agent (the official @eureka account). Disable in an
    # environment (e.g. a staging deploy) by setting AGENT_ENABLED=false.
    agent_enabled: bool = True
    agent_posts_per_day: int = 10
    agent_username: str = "eureka"


@lru_cache
def get_settings() -> Settings:
    return Settings()
