import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

IS_VERCEL = bool(os.environ.get("VERCEL"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
    )

    play_store_app_id: str = "com.nextbillion.groww"
    app_store_app_id: int = 1404871703

    review_weeks: int = 12
    max_reviews_per_source: int = 3000

    groq_api_key: str = ""
    gemini_api_key: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    resend_api_key: str = ""


settings = Settings()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path("/tmp/data") if IS_VERCEL else BASE_DIR / "data"
REVIEWS_FILE = DATA_DIR / "reviews.json"
THEMES_FILE = DATA_DIR / "themes.json"
CLASSIFICATIONS_FILE = DATA_DIR / "classifications.json"
WEEKLY_NOTES_DIR = DATA_DIR / "weekly-notes"
