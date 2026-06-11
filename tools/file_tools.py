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

_log = get_logger("tools")

_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build",
    ".tox", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
}

_MAX_TOKENS      = 4_000
_CHARS_PER_TOKEN = 4

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
    
@tool
def list_directory(dir_path: str, max_depth: int = 2) -> str:
    _log.tool_call("list_directory", path=dir_path, depth=max_depth)

    root = Path(dir_path)
    if not root.is_dir():
        _log.tool_result("list_directory", success=False, reason="not_a_directory")
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    lines = [str(root)]