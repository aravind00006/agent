"""
core/logger.py — How the agent talks to you.

"""

from __future__ import annotations
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# ANSI color codes — these make terminal text colored
# ─────────────────────────────────────────────────────────────────────────────

_RESET = "\033[0m"   # back to normal color
_BOLD  = "\033[1m"
_DIM   = "\033[2m"   # slightly faded (used for timestamps)


_LEVEL_COLORS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}

_AGENT_COLORS = {
    "issue_agent":        "\033[94m",   # bright blue
    "localization_agent": "\033[95m",   # bright magenta
    "fix_agent":          "\033[96m",   # bright cyan
    "test_agent":         "\033[92m",   # bright green
    "reflection_agent":   "\033[93m",   # bright yellow
    "pr_agent":           "\033[91m",   # bright red
    "graph":              "\033[97m",   # white
    "tools":              "\033[36m",   # cyan
    "api":                "\033[34m",   # blue
}

_LEVEL_ICONS = {
    "DEBUG":    "·",
    "INFO":     "●",
    "WARNING":  "▲",
    "ERROR":    "✖",
    "CRITICAL": "☠",
}

_AGENT_ICONS = {
    "issue_agent":        "📋",
    "localization_agent": "🔍",
    "fix_agent":          "🔧",
    "test_agent":         "🧪",
    "reflection_agent":   "🤔",
    "pr_agent":           "📬",
    "graph":              "🕸 ",
    "tools":              "🛠 ",
    "api":                "🌐",
}


# ─────────────────────────────────────────────────────────────────────────────
# Console formatter — makes each log line look nice in the terminal
# ─────────────────────────────────────────────────────────────────────────────

class ConsoleFormatter(logging.Formatter):
    """Turns a raw log record into a colored, readable terminal line."""

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = _LEVEL_COLORS.get(level, "")
        icon  = _LEVEL_ICONS.get(level, "●")

        agent      = getattr(record, "agent", None)
        run_id     = getattr(record, "run_id", None)
        extra_data = getattr(record, "extra_data", None)

        # Timestamp — dimmed so it doesn't distract
        ts = f"{_DIM}{datetime.now().strftime('%H:%M:%S')}{_RESET}"

        # Level badge: colored + bold + icon
        level_str = f"{color}{_BOLD}{icon} {level:<8}{_RESET}"

        # Agent badge: shows which agent is speaking
        if agent:
            agent_color = _AGENT_COLORS.get(agent, "")
            agent_icon  = _AGENT_ICONS.get(agent, "")
            agent_str   = f"{agent_color}[{agent_icon} {agent}]{_RESET} "
        else:
            agent_str = ""

        # Short run ID in the corner — dimmed so it's there but subtle
        run_str = f" {_DIM}#{run_id[:8]}{_RESET}" if run_id else ""

        extra_str = ""
        if extra_data:
            parts = []
            for k, v in extra_data.items():
                if isinstance(v, float):
                    parts.append(f"{_DIM}{k}={v:.3f}{_RESET}")
                else:
                    parts.append(f"{_DIM}{k}={v!r}{_RESET}")
            extra_str = "  " + "  ".join(parts)

        # Exception traceback if there is one
        exc_str = ""
        if record.exc_info:
            exc_str = "\n" + self.formatException(record.exc_info)

        return f"{ts} {level_str} {agent_str}{record.getMessage()}{run_str}{extra_str}{exc_str}"
