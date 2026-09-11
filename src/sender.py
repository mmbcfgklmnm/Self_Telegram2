"""
sender.py — Send stickers and feedback messages back to Saved Messages.

All outgoing messages are sent to "me" (Saved Messages) so nothing leaks
to other chats.
"""

import logging
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import Message

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def send_sticker(
    client: TelegramClient,
    sticker_path: Path,
    reply_to: Optional[Message] = None,
    force_document: bool = False,
) -> None:
    """
    Upload and send a sticker file to Saved Messages.

    For TGS / WebM files we let Telethon detect the type automatically.
    For static WebP we set `force_document=False` so Telegram renders it
    as a sticker rather than a file attachment.

    Args:
        client:         Connected Telethon client.
        sticker_path:   Local path of the prepared sticker file.
        reply_to:       Original message to reply to (optional).
        force_document: If True, sends as a raw file (useful for debugging).
    """
    reply_id = reply_to.id if reply_to else None
    log.info(
        "Sending sticker '%s' to Saved Messages (reply_to=%s).",
        sticker_path.name, reply_id,
    )

    try:
        await client.send_file(
            "me",
            file=str(sticker_path),
            reply_to=reply_id,
            force_document=force_document,
        )
        log.info("Sticker sent successfully.")
    except Exception as exc:
        raise RuntimeError(f"Failed to send sticker '{sticker_path.name}': {exc}") from exc


async def send_feedback(
    client: TelegramClient,
    text: str,
    reply_to: Optional[Message] = None,
) -> None:
    """
    Send a plain-text feedback or error message to Saved Messages.

    Args:
        client:   Connected Telethon client.
        text:     Message body.
        reply_to: Message to reply to (optional).
    """
    reply_id = reply_to.id if reply_to else None
    log.debug("Sending feedback to Saved Messages: %r", text)
    try:
        await client.send_message("me", text, reply_to=reply_id)
    except Exception as exc:
        # Feedback failures are non-fatal — log and continue
        log.warning("Could not send feedback message: %s", exc)
