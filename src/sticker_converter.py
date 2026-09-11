"""
sticker_converter.py — Download an emoji Document and produce a sticker file.

Strategy (zero-re-encode where possible):
  • TGS  (.tgs)  → Pass through as-is. TGS *is* the Telegram animated sticker
                   format. No conversion needed — just rename/re-send.
  • WebM (.webm) → Pass through as-is. Telegram accepts WebM VP9 stickers
                   directly. No re-encoding needed.
  • Static WebP / PNG → Pass through as-is for static stickers.

If any intermediate processing is needed (e.g. resizing a static image to
512×512 as Telegram requires), we apply it with Pillow without changing the
compression level from the default lossless WebP quality.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from telethon import TelegramClient

from .emoji_extractor import EmojiInfo

log = logging.getLogger(__name__)

# Telegram sticker size requirement for static stickers
STICKER_SIZE = 512


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def convert_emoji_to_sticker(
    client: TelegramClient, emoji_info: EmojiInfo
) -> Path:
    """
    Download the emoji document and prepare a sticker-ready file.

    For animated emoji (TGS / WebM) no conversion is applied — the file is
    used as-is to preserve maximum quality.

    For static emoji the image is resized to 512×512 (maintaining aspect ratio,
    padding with transparency) and saved as lossless WebP.

    Args:
        client:     Connected Telethon client.
        emoji_info: EmojiInfo produced by emoji_extractor.

    Returns:
        Path to the temporary sticker file. Caller is responsible for cleanup.

    Raises:
        RuntimeError: If download or processing fails.
    """
    log.info(
        "Starting conversion for document_id=%d (type=%s).",
        emoji_info.document_id, emoji_info.emoji_type,
    )

    # --- Download raw bytes from Telegram ---
    raw_bytes = await _download_document(client, emoji_info)
    log.debug("Downloaded %d bytes for document_id=%d.", len(raw_bytes), emoji_info.document_id)

    # --- Decide output path ---
    suffix = emoji_info.file_extension
    tmp_file = _make_temp_file(suffix)

    try:
        if emoji_info.emoji_type in ("animated_lottie", "animated_video"):
            # Zero-copy pass-through — these formats ARE the sticker format
            log.info(
                "Animated emoji (%s): writing raw bytes directly to %s.",
                emoji_info.emoji_type, tmp_file,
            )
            tmp_file.write_bytes(raw_bytes)

        else:
            # Static — ensure correct dimensions for Telegram
            log.info("Static emoji: resizing to %dx%d WebP.", STICKER_SIZE, STICKER_SIZE)
            processed = _resize_static(raw_bytes)
            tmp_file.write_bytes(processed)
            suffix = ".webp"
            # Rename if suffix changed
            if tmp_file.suffix != suffix:
                new_path = tmp_file.with_suffix(suffix)
                tmp_file.rename(new_path)
                tmp_file = new_path

    except Exception as exc:
        _cleanup(tmp_file)
        raise RuntimeError(f"Conversion failed for document_id={emoji_info.document_id}: {exc}") from exc

    log.info(
        "Sticker ready at '%s' (%d bytes).", tmp_file, tmp_file.stat().st_size
    )
    return tmp_file


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _download_document(client: TelegramClient, emoji_info: EmojiInfo) -> bytes:
    """Download a Telegram Document into memory and return raw bytes."""
    buf = io.BytesIO()
    try:
        await client.download_media(emoji_info.document, file=buf)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download document_id={emoji_info.document_id}: {exc}"
        ) from exc
    raw = buf.getvalue()
    if not raw:
        raise RuntimeError(
            f"Download returned 0 bytes for document_id={emoji_info.document_id}. "
            "The document may have expired or be inaccessible."
        )
    return raw


def _resize_static(raw_bytes: bytes) -> bytes:
    """
    Resize a static image to 512×512, preserving aspect ratio with
    transparent padding. Returns lossless WebP bytes.

    Requires: Pillow
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for static emoji conversion. "
            "Install it with: pip install Pillow"
        ) from exc

    with Image.open(io.BytesIO(raw_bytes)) as img:
        img = img.convert("RGBA")
        img.thumbnail((STICKER_SIZE, STICKER_SIZE), Image.LANCZOS)

        # Pad to exact 512×512 with transparent background
        canvas = Image.new("RGBA", (STICKER_SIZE, STICKER_SIZE), (0, 0, 0, 0))
        offset_x = (STICKER_SIZE - img.width) // 2
        offset_y = (STICKER_SIZE - img.height) // 2
        canvas.paste(img, (offset_x, offset_y), img)

        out = io.BytesIO()
        canvas.save(out, format="WEBP", lossless=True, quality=100)
        return out.getvalue()


def _make_temp_file(suffix: str) -> Path:
    """Create a named temporary file and return its Path (file is closed after creation)."""
    fd, path_str = tempfile.mkstemp(suffix=suffix, prefix="emoji_sticker_")
    os.close(fd)
    return Path(path_str)


def _cleanup(path: Optional[Path]) -> None:
    """Silently remove a temp file if it exists."""
    if path and path.exists():
        try:
            path.unlink()
        except OSError:
            pass
