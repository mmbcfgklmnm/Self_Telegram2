"""
handler.py — Message event handler: the brain of the userbot.

Flow:
  1. All new messages in Saved Messages ("me") are received here.
  2. If a message contains a custom emoji → store its ID in a tracked set.
  3. If a message is a reply whose text matches the trigger phrase:
       a. Look up the replied-to message.
       b. Extract its custom emoji document.
       c. Convert to sticker.
       d. Send back to Saved Messages.
       e. Clean up the temp file.
"""

import logging
from pathlib import Path
from typing import Optional, Set

from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageEntityCustomEmoji

from .emoji_extractor import EmojiInfo, extract_first_custom_emoji
from .sender import send_feedback, send_sticker
from .sticker_converter import convert_emoji_to_sticker, _cleanup

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory tracker (survives only for the process lifetime)
# ---------------------------------------------------------------------------

_tracked_emoji_message_ids: Set[int] = set()


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register_handlers(client: TelegramClient, trigger_phrase: str) -> None:
    """
    Register Telethon event handlers on *client*.

    Args:
        client:         Connected Telethon client.
        trigger_phrase: Lower-cased phrase that triggers conversion.
    """
    log.info("Registering handlers. Trigger phrase: '%s'", trigger_phrase)

    # ------------------------------------------------------------------ #
    # Handler 1 — Track incoming messages with custom emoji
    # ------------------------------------------------------------------ #
    @client.on(events.NewMessage(outgoing=True, chats="me"))
    async def on_new_message(event: events.NewMessage.Event) -> None:
        message: Message = event.message
        log.debug("Received outgoing message id=%d in Saved Messages.", message.id)

        # Detect custom emoji
        has_custom_emoji = _message_has_custom_emoji(message)
        if has_custom_emoji:
            _tracked_emoji_message_ids.add(message.id)
            log.info(
                "Tracked custom emoji message id=%d. "
                "Total tracked: %d.",
                message.id, len(_tracked_emoji_message_ids),
            )
            return  # Nothing else to do for this message

        # Detect trigger phrase
        text = (message.text or message.message or "").strip().lower()
        if text != trigger_phrase:
            log.debug("Message id=%d is neither emoji nor trigger — ignoring.", message.id)
            return

        # ---- Trigger phrase detected ----
        log.info("Trigger phrase detected in message id=%d.", message.id)
        await _handle_conversion(client, message)

    log.info("Handlers registered successfully.")


# ---------------------------------------------------------------------------
# Conversion workflow
# ---------------------------------------------------------------------------

async def _handle_conversion(
    client: TelegramClient, trigger_message: Message
) -> None:
    """
    Orchestrate the full emoji → sticker conversion for *trigger_message*.

    Sends feedback on every failure path so the user always gets a response.
    """
    # 1. Validate: must be a reply
    if not trigger_message.reply_to or not trigger_message.reply_to.reply_to_msg_id:
        log.warning("Trigger message id=%d is not a reply — aborting.", trigger_message.id)
        await send_feedback(
            client,
            "⚠️ Please reply to a message that contains a premium emoji.",
            reply_to=trigger_message,
        )
        return

    replied_msg_id = trigger_message.reply_to.reply_to_msg_id

    # 2. Fetch the replied-to message
    try:
        replied_message: Optional[Message] = await client.get_messages(
            "me", ids=replied_msg_id
        )
    except Exception as exc:
        log.error("Could not fetch replied-to message id=%d: %s", replied_msg_id, exc)
        await send_feedback(
            client,
            f"❌ Could not retrieve the replied-to message (id={replied_msg_id}). "
            "It may have been deleted.",
            reply_to=trigger_message,
        )
        return

    if replied_message is None:
        log.warning("Replied-to message id=%d not found.", replied_msg_id)
        await send_feedback(
            client,
            f"❌ Message id={replied_msg_id} was not found in Saved Messages.",
            reply_to=trigger_message,
        )
        return

    log.info("Replied-to message id=%d fetched successfully.", replied_msg_id)

    # 3. Extract the custom emoji
    try:
        emoji_info: Optional[EmojiInfo] = await extract_first_custom_emoji(
            client, replied_message
        )
    except Exception as exc:
        log.error("Emoji extraction failed: %s", exc)
        await send_feedback(
            client,
            f"❌ Failed to extract emoji from message id={replied_msg_id}:\n{exc}",
            reply_to=trigger_message,
        )
        return

    if emoji_info is None:
        log.warning("No custom emoji found in message id=%d.", replied_msg_id)
        await send_feedback(
            client,
            "⚠️ The replied-to message does not contain a premium custom emoji.\n"
            "Make sure you're replying to a message with a 💎 premium animated emoji.",
            reply_to=trigger_message,
        )
        return

    log.info(
        "Emoji extracted: type=%s, mime=%s, document_id=%d.",
        emoji_info.emoji_type, emoji_info.mime_type, emoji_info.document_id,
    )

    # 4. Convert to sticker
    sticker_path: Optional[Path] = None
    try:
        await send_feedback(
            client,
            f"⏳ Converting {_emoji_type_label(emoji_info.emoji_type)} emoji to sticker…",
            reply_to=trigger_message,
        )
        sticker_path = await convert_emoji_to_sticker(client, emoji_info)
    except Exception as exc:
        log.error("Conversion failed: %s", exc)
        await send_feedback(
            client,
            f"❌ Conversion failed:\n{exc}",
            reply_to=trigger_message,
        )
        return

    # 5. Send the sticker
    try:
        await send_sticker(client, sticker_path, reply_to=trigger_message)
        log.info("Sticker sent for document_id=%d.", emoji_info.document_id)
    except Exception as exc:
        log.error("Failed to send sticker: %s", exc)
        await send_feedback(
            client,
            f"❌ Sticker created but could not be sent:\n{exc}",
            reply_to=trigger_message,
        )
    finally:
        if sticker_path:
            _cleanup(sticker_path)
            log.debug("Temp file cleaned up: %s", sticker_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _message_has_custom_emoji(message: Message) -> bool:
    """Return True if *message* contains at least one MessageEntityCustomEmoji."""
    if not message.entities:
        return False
    return any(isinstance(e, MessageEntityCustomEmoji) for e in message.entities)


def _emoji_type_label(emoji_type: str) -> str:
    """Human-readable label for an emoji type."""
    return {
        "animated_lottie": "🎞️ Lottie-animated",
        "animated_video":  "🎬 video-animated",
        "static":          "🖼️ static",
    }.get(emoji_type, emoji_type)
