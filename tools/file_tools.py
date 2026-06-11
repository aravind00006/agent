"""
This file Read, write, list, and patch files on disk.
These are the agent's hands — without these tools the AI can think
but can't actually touch anything on the filesystem.

"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool
from core.logger import get_logger

# Module-level logger — no run_id here, agents pass context via log.bind
_log = get_logger("tools")

# Directories we always skip when listing — they're noisy and irrelevant
_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build",
    ".tox", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
}

# Token limit for reading files
_MAX_TOKENS      = 4_000
_CHARS_PER_TOKEN = 4 # rough estimate: 1 token ≈ 4 characters

# ─────────────────────────────────────────────────────────────────────────────

@tool
def read_file(file_path: str, max_tokens: int = _MAX_TOKENS) -> str:
    _log.tool_call("read_file", path=file_path)

    path = Path(file_path)

    if not path.exists():
        _log.tool_result("read_file", success=False, reason="file_not_found")
        raise FileNotFoundError(f"File not found: {file_path}")

    text       = path.read_text(encoding="utf-8", errors="replace")
    char_limit = max_tokens * _CHARS_PER_TOKEN

    truncated  = False
    if len(text) > char_limit:
        text      = text[:char_limit]
        truncated = True

    _log.tool_result("read_file", success=True, path=file_path, chars=len(text), truncated=truncated)

    if truncated:
        _log.warning("File truncated to fit context window", path=file_path, max_tokens=max_tokens)
        text += f"\n\n... [TRUNCATED at {max_tokens:,} tokens] ..."

    return text

# ─────────────────────────────────────────────────────────────────────────────

@tool
def write_file(file_path: str, content: str) -> bool:
    _log.tool_call("write_file", path=file_path, bytes=len(content))

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        path.write_text(content, encoding="utf-8")
        _log.tool_result("write_file", success=True, path=file_path, bytes=len(content))
        return True
    except Exception as e:
        _log.tool_result("write_file", success=False, path=file_path, error=str(e))
        return False

# ─────────────────────────────────────────────────────────────────────────────

@tool
def list_directory(dir_path: str, max_depth: int = 2) -> str:
    _log.tool_call("list_directory", path=dir_path, depth=max_depth)

    root = Path(dir_path)
    if not root.is_dir():
        _log.tool_result("list_directory", success=False, reason="not_a_directory")
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    lines = [str(root)]

    def _walk(current: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return

        try:
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return

        entries = [
            e for e in entries
            if e.name not in _SKIP_DIRS
            and not e.name.endswith(".egg-info")
        ]

        for i, entry in enumerate(entries):
            is_last   = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            suffix    = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix + extension, depth + 1)

    _walk(root, "", 1)

    tree = "\n".join(lines)
    _log.tool_result("list_directory", success=True, entries=len(lines) - 1)
    return tree
