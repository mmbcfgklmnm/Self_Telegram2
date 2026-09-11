"""
main.py — Entry point for the Telegram emoji-to-sticker userbot.

Responsibilities:
  1. Load configuration from environment variables.
  2. Configure logging.
  3. Build and connect the Telethon client using a StringSession.
  4. Register message handlers.
  5. Run the client until disconnected, with automatic reconnect.
"""

import asyncio
import logging
import signal
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

from src.config import load_config
from src.handler import register_handlers
from src.logger import setup_logging

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def _install_signal_handlers(loop: asyncio.AbstractEventLoop, client: TelegramClient) -> None:
    """Register SIGINT / SIGTERM handlers for clean shutdown."""
    def _shutdown(sig_name: str) -> None:
        log.info("Received %s — shutting down gracefully…", sig_name)
        loop.create_task(client.disconnect())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown, sig.name)
        except (NotImplementedError, ValueError):
            # Windows does not support add_signal_handler for all signals
            pass


# ---------------------------------------------------------------------------
# Main coroutine
# ---------------------------------------------------------------------------

async def run_bot(config: dict) -> None:
    """
    Build the Telethon client, connect, register handlers, and run until
    disconnected. On Railway (or any PaaS), the process is restarted
    automatically by the platform if it exits unexpectedly.
    """
    log.info("Initialising Telethon client…")

    client = TelegramClient(
        session=StringSession(config["session_string"]),
        api_id=config["api_id"],
        api_hash=config["api_hash"],
        # Connection settings optimised for reliability on cloud platforms
        connection_retries=None,   # Retry indefinitely
        retry_delay=5,             # 5 s between retries
        auto_reconnect=True,
        flood_sleep_threshold=60,  # Auto-sleep on flood-wait up to 60 s
    )

    register_handlers(client, trigger_phrase=config["trigger_phrase"])

    loop = asyncio.get_event_loop()
    _install_signal_handlers(loop, client)

    async with client:
        me = await client.get_me()
        log.info(
            "✅ Logged in as %s (id=%d). Monitoring Saved Messages…",
            me.first_name, me.id,
        )
        log.info("Trigger phrase: '%s'", config["trigger_phrase"])
        await client.run_until_disconnected()

    log.info("Client disconnected. Process will exit (platform will restart if configured).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        config = load_config()
    except EnvironmentError as exc:
        # Print before logging is set up
        print(f"[FATAL] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config["log_level"])
    log.info("Starting telegram-emoji-sticker-bot…")

    try:
        asyncio.run(run_bot(config))
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except Exception as exc:
        log.critical("Unhandled exception — bot crashed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
