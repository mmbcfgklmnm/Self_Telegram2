"""
emoji_extractor.py — Detect and extract custom emoji documents from messages.

Telegram premium animated emoji are sent as MessageEntityCustomEmoji entities
inside a message. Each entity references a document by its ID. This module
fetches the underlying Document object so it can be converted to a sticker.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import (
    Document,
    DocumentAttributeAnimated,
    DocumentAttributeFilename,
    DocumentAttributeSticker,
    DocumentAttributeVideo,
    Message,
    MessageEntityCustomEmoji,
)
from telethon.tl.functions.messages import GetCustomEmojiDocumentsRequest

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmojiInfo:
    """All information needed to convert one custom emoji to a sticker."""
    document: Document          # The raw Telegram Document object
    document_id: int            # Numeric document ID
    emoji_type: str             # "animated_lottie", "animated_video", "static"
    mime_type: str              # e.g. "application/x-tgsticker", "video/webm", "image/webp"
    file_extension: str         # ".tgs", ".webm", ".webp"
    is_animated: bool
    is_video: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_first_custom_emoji(
    client: TelegramClient, message: Message
) -> Optional[EmojiInfo]:
    """
    Inspect *message* for the first MessageEntityCustomEmoji and return its
    EmojiInfo, or None if no custom emoji is found.

    Args:
        client:  Connected Telethon client.
        message: The Telegram message to inspect.

    Returns:
        EmojiInfo on success, None if the message has no custom emoji.

    Raises:
        RuntimeError: If the document cannot be fetched from Telegram.
    """
    if not message.entities:
        log.debug("Message %d has no entities — skipping.", message.id)
        return None

    # Find the first custom emoji entity
    custom_emoji_entity: Optional[MessageEntityCustomEmoji] = None
    for entity in message.entities:
        if isinstance(entity, MessageEntityCustomEmoji):
            custom_emoji_entity = entity
            break

    if custom_emoji_entity is None:
        log.debug("Message %d has no MessageEntityCustomEmoji.", message.id)
        return None

    document_id = custom_emoji_entity.document_id
    log.info("Found custom emoji document_id=%d in message %d.", document_id, message.id)

    # Fetch the Document object from Telegram
    try:
        result = await client(GetCustomEmojiDocumentsRequest(document_id=[document_id]))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch document for emoji {document_id}: {exc}"
        ) from exc

    if not result:
        raise RuntimeError(
            f"Telegram returned an empty result for emoji document_id={document_id}."
        )

    document: Document = result[0]
    log.debug("Fetched document: id=%d mime_type=%s", document.id, document.mime_type)

    emoji_info = _classify_document(document)
    log.info(
        "Emoji classified as type='%s', mime='%s', extension='%s'.",
        emoji_info.emoji_type, emoji_info.mime_type, emoji_info.file_extension,
    )
    return emoji_info


def _classify_document(document: Document) -> EmojiInfo:
    """
    Inspect a Document's attributes and MIME type to determine what kind of
    emoji it is and which output format should be used.

    Telegram uses three formats for custom emoji:
      • application/x-tgsticker  → TGS (gzip-compressed Lottie JSON) → animated_lottie
      • video/webm               → WebM VP9 video                    → animated_video
      • image/webp               → Static WebP image                 → static
    """
    mime = (document.mime_type or "").lower()
    attributes = document.attributes or []

    has_animated_attr = any(isinstance(a, DocumentAttributeAnimated) for a in attributes)
    has_video_attr = any(isinstance(a, DocumentAttributeVideo) for a in attributes)

    if mime == "application/x-tgsticker" or (mime == "application/x-tgs" or has_animated_attr):
        return EmojiInfo(
            document=document,
            document_id=document.id,
            emoji_type="animated_lottie",
            mime_type=mime or "application/x-tgsticker",
            file_extension=".tgs",
            is_animated=True,
            is_video=False,
        )

    if mime == "video/webm" or has_video_attr:
        return EmojiInfo(
            document=document,
            document_id=document.id,
            emoji_type="animated_video",
            mime_type=mime or "video/webm",
            file_extension=".webm",
            is_animated=True,
            is_video=True,
        )

    # Fallback: treat as static
    ext = ".webp" if "webp" in mime else ".png"
    return EmojiInfo(
        document=document,
        document_id=document.id,
        emoji_type="static",
        mime_type=mime or "image/webp",
        file_extension=ext,
        is_animated=False,
        is_video=False,
    )
