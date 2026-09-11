"""
config.py — Load and validate all environment variables for the bot.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


def _require(name: str) -> str:
    """Return the value of an environment variable, raising on missing."""
    value = os.getenv(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            "Check your .env file or Railway environment variables."
        )
    return value


def load_config() -> dict:
    """Parse and return the full bot configuration."""
    try:
        api_id = int(_require("API_ID"))
    except ValueError:
        raise EnvironmentError("API_ID must be a valid integer.")

    config = {
        # Telegram API credentials
        "api_id": api_id,
        "api_hash": _require("API_HASH"),
        # A pre-generated Telethon StringSession (no interactive login needed)
        "session_string": _require("SESSION_STRING"),
        # Phrase that triggers conversion (case-insensitive)
        "trigger_phrase": os.getenv("TRIGGER_PHRASE", "convert to sticker").strip().lower(),
        # Logging level
        "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
    }

    log.debug("Configuration loaded: api_id=%s, trigger_phrase='%s'",
              config["api_id"], config["trigger_phrase"])
    return config
