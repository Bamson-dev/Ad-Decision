"""
Runtime configuration for Adley.

Coolify injects environment variables at container start. For local development,
copy `.env.example` to `.env` — python-dotenv loads it when present.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _path_from_env(key: str, default: str) -> Path:
    raw = os.getenv(key, default).strip()
    return Path(raw)


class Settings:
    """Application settings from environment (Docker / Coolify / local .env)."""

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()

    # Persistent user data (mount a Coolify volume at this path, default /data in Docker)
    adley_data_dir: Path = _path_from_env("ADLEY_DATA_DIR", "./data")

    # Reserved for future self-hosted services on the same Coolify stack
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    redis_url: str = os.getenv("REDIS_URL", "").strip()
    storage_backend: str = os.getenv("STORAGE_BACKEND", "json").strip().lower()

    log_level: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    deepseek_timeout_seconds: int = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "90"))
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

    def validate_required(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment.")
        if not self.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is missing in environment.")
        if self.storage_backend not in ("json",):
            raise RuntimeError(
                f"Unsupported STORAGE_BACKEND={self.storage_backend!r}. "
                "Only 'json' is implemented; set DATABASE_URL when Postgres support ships."
            )

    @property
    def users_json_path(self) -> Path:
        return self.adley_data_dir.resolve() / "users.json"


settings = Settings()


def setup_logging() -> None:
    level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )
