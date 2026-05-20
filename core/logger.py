"""
core/logger.py — How the agent talks to you.

"""

from __future__ import annotations
from typing import Optional
import logging

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