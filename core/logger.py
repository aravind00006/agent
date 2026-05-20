"""
core/logger.py — How the agent talks to you.

"""

from __future__ import annotations
from typing import Optional
import logging

# ANSI terminal colors

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}

_LEVEL_ICONS = {
    "DEBUG": "·",
    "INFO": "●",
    "WARNING": "▲",
    "ERROR": "✖",
    "CRITICAL": "☠",
}


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname

        color = _LEVEL_COLORS.get(level, "")
        icon = _LEVEL_ICONS.get(level, "•")

        prefix = f"{color}{icon} {level}{_RESET}"

        return f"{prefix} {record.name}: {record.getMessage()}"

def get_logger(name: str, run_id: Optional[str] = None) -> logging.Logger:
    """
    Create or return a shared logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "[%(levelname)s] %(name)s: %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger