"""Environment-based application configuration."""
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str
    log_level: str
    max_message_chars: int
    owner_notify: bool


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "PASTE_YOUR_BOTFATHER_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN sozlanmagan. .env fayliga BotFather tokenini kiriting."
        )

    database_path = os.getenv("DATABASE_PATH", "data/bot.sqlite3").strip()
    max_chars_raw = os.getenv("MAX_MESSAGE_CHARS", "2500")
    try:
        max_chars = max(100, min(int(max_chars_raw), 3500))
    except ValueError as exc:
        raise RuntimeError("MAX_MESSAGE_CHARS butun son bo'lishi kerak.") from exc

    Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=token,
        database_path=database_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        max_message_chars=max_chars,
        owner_notify=_bool_env("OWNER_NOTIFY", True),
    )
