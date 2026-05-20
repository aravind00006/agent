from __future__ import annotations

import logging
from typing import Optional


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


# ─────────────────────────────────────────────────────────────────────────────
# Agent identity colors/icons
# ─────────────────────────────────────────────────────────────────────────────

_AGENT_COLORS = {
    "issue_agent": "\033[94m",
    "localization_agent": "\033[95m",
    "fix_agent": "\033[96m",
    "test_agent": "\033[92m",
    "reflection_agent": "\033[93m",
    "pr_agent": "\033[91m",
}

_AGENT_ICONS = {
    "issue_agent": "📋",
    "localization_agent": "🔍",
    "fix_agent": "🔧",
    "test_agent": "🧪",
    "reflection_agent": "🤔",
    "pr_agent": "📬",
}


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname

        level_color = _LEVEL_COLORS.get(level, "")
        level_icon = _LEVEL_ICONS.get(level, "•")

        agent_color = _AGENT_COLORS.get(record.name, "")
        agent_icon = _AGENT_ICONS.get(record.name, "🤖")

        level_part = (
            f"{level_color}{level_icon} {level}{_RESET}"
        )

        agent_part = (
            f"{agent_color}{agent_icon} {record.name}{_RESET}"
        )

        return f"{level_part} {agent_part}: {record.getMessage()}"


def get_logger(name: str, run_id: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())

    logger.addHandler(handler)
    logger.propagate = False

    return logger