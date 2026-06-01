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
    "DEBUG":    "\033[36m",   
    "INFO":     "\033[32m",   
    "WARNING":  "\033[33m",   
    "ERROR":    "\033[31m",   
    "CRITICAL": "\033[35m",   
}

_AGENT_COLORS = {
    "issue_agent":        "\033[94m",   
    "localization_agent": "\033[95m",   
    "fix_agent":          "\033[96m",   
    "test_agent":         "\033[92m",   
    "reflection_agent":   "\033[93m",   
    "pr_agent":           "\033[91m",   
    "graph":              "\033[97m", 
    "tools":              "\033[36m", 
    "api":                "\033[34m", 
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

# ─────────────────────────────────────────────────────────────────────────────
# JSON formatter — saves structured data to a log file
# ─────────────────────────────────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """ Writes each log entry as one JSON line to the log file."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        # Attach optional context if present
        for field in ("agent", "run_id", "extra_data"):
            val = getattr(record, field, None)
            if val is not None:
                payload[field] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)

# ─────────────────────────────────────────────────────────────────────────────
# Setup function — call once at startup
# ─────────────────────────────────────────────────────────────────────────────
_ROOT = "bugfixer"
_initialized = False

def setup_logging(
    *,
    level: str = "DEBUG",
    run_id: Optional[str] = None,
    log_to_file: bool = True,
) -> None:
    
    global _initialized

    root = logging.getLogger(_ROOT)
    root.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    root.handlers.clear()

    # Console handler — colored output to your terminal
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ConsoleFormatter())
    console.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    root.addHandler(console)

    # File handler — JSON lines on disk
    if log_to_file:
        log_dir = Path("logs") / (run_id or "global")
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "agent.jsonl", mode="a", encoding="utf-8")
        fh.setFormatter(JSONFormatter())
        fh.setLevel(logging.DEBUG)
        root.addHandler(fh)

    # Silence noisy third-party libraries
    for lib in ("httpx", "httpcore", "urllib3", "git", "docker"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _initialized = True

# ─────────────────────────────────────────────────────────────────────────────
# AgentLogger — the class every agent uses
# ────────────────────────────────────────────────────────────────────────────

class AgentLogger:
    """
    A logger scoped to one agent.
    """

    def __init__(self, agent_name: str, run_id: Optional[str] = None) -> None:
        self.agent_name = agent_name
        self.run_id     = run_id
        self._log       = logging.getLogger(f"{_ROOT}.{agent_name}")

    def _emit(self, level: int, msg: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Internal: add agent/run context and emit the log record."""
        extra: dict[str, Any] = {"agent": self.agent_name, "run_id": self.run_id}

        if kwargs:
            extra["extra_data"] = kwargs

        self._log.log(
            level,
            msg,
            extra=extra,
            exc_info=exc_info,
            stacklevel=3,
        )

    # ── Standard log levels ───────────────────────────────────────────────────

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Low-level detail. Shown only in DEBUG mode."""
        self._emit(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Normal progress messages."""
        self._emit(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Something unexpected but recoverable."""
        self._emit(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Something went wrong."""
        self._emit(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Fatal error — agent cannot continue."""
        self._emit(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)

    # ── Semantic shortcuts — describe WHAT happened, not just the level ───────

    def step(self, step_name: str, **kwargs: Any) -> None:
        """Log the start of a named step. Shows ▶ prefix."""
        self._emit(logging.INFO, f"▶  {step_name}", **kwargs)

    def success(self, msg: str, **kwargs: Any) -> None:
        """Log a successful outcome. Shows ✔ prefix."""
        self._emit(logging.INFO, f"✔  {msg}", **kwargs)

    def fail(self, msg: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log a failure. Shows ✘ prefix."""
        self._emit(logging.ERROR, f"✘  {msg}", exc_info=exc_info, **kwargs)

    def tokens(self, used: int, step: Optional[str] = None, **kwargs: Any) -> None:
        """Log how many tokens the LLM used."""
        label = f" [{step}]" if step else ""
        self._emit(logging.DEBUG, f"🔢 Tokens used{label}: {used:,}", tokens=used, **kwargs)

    def retry(self, attempt: int, max_retries: int, reason: str) -> None:
        """Log a retry attempt with its reason."""
        self._emit(
            logging.WARNING,
            f"↺  Retry {attempt}/{max_retries} — {reason}",
            attempt=attempt,
            max_retries=max_retries,
            reason=reason,
        )

    def tool_call(self, tool_name: str, **kwargs: Any) -> None:
        """Log that a tool is being called."""
        self._emit(logging.DEBUG, f"🛠  Tool call: {tool_name}", tool=tool_name, **kwargs)

    def tool_result(self, tool_name: str, success: bool, **kwargs: Any) -> None:
        """Log the result of a tool call."""
        icon  = "✔" if success else "✘"
        level = logging.DEBUG if success else logging.WARNING
        self._emit(level, f"{icon}  Tool result: {tool_name}", tool=tool_name, success=success, **kwargs)

    def patch(self, file_path: str, strategy: str, **kwargs: Any) -> None:
        """Log that a code patch was applied."""
        self._emit(logging.INFO, f"🩹 Patch applied: {file_path}", file=file_path, strategy=strategy, **kwargs)

    def pr(self, pr_url: str, **kwargs: Any) -> None:
        """Log that a Pull Request was opened."""
        self._emit(logging.INFO, f"📬 PR opened: {pr_url}", pr_url=pr_url, **kwargs)

    def timed(self, label: str) -> "_TimedBlock":
        """logs how long a block of code takes."""
        return _TimedBlock(self, label)
    

class _TimedBlock:
    """Used by log.timed() — measures and logs elapsed time."""

    def __init__(self, logger: AgentLogger, label: str) -> None:
        self._log = logger
        self._label = label
        self._start = 0.0

    def __enter__(self) -> "_TimedBlock":
        self._start = time.perf_counter()
        self._log.debug(f"⏱  Start: {self._label}")
        return self