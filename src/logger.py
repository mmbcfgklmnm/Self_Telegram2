"""
logger.py — Configure structured console logging for the entire bot.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger with a consistent format.

    Args:
        level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    fmt = "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=numeric_level,
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet noisy third-party loggers
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialised at level %s", level.upper()
    )
