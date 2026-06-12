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
    """
    Read a file from disk and return its contents as a string

    """

    _log.tool_call("read_file", path=file_path)

    path = Path(file_path)

    # Check the file actually exists before trying to read it
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
    """
    Write content to a file, creating any missing parent directories.
    """

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
    """
    Return a directory tree as a readable string.
    Skips noisy folders like node_modules, .git, __pycache__.
    """

    _log.tool_call("list_directory", path=dir_path, depth=max_depth)

    root = Path(dir_path)
    if not root.is_dir():
        _log.tool_result("list_directory", success=False, reason="not_a_directory")
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    lines = [str(root)]

    def _walk(current: Path, prefix: str, depth: int) -> None:
        # Stop recursing when we hit the depth limit
        if depth > max_depth:
            return

        try:
            # Sort: directories first, then files, both alphabetically
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return

        # Filter out the noisy directories we never want to see
        entries = [
            e for e in entries
            if e.name not in _SKIP_DIRS
            and not e.name.endswith(".egg-info")
        ]

        for i, entry in enumerate(entries):
            # Last item uses └── , others use ├──
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

# ─────────────────────────────────────────────────────────────────────────────

@tool
def apply_patch(file_path: str, original: str, replacement: str) -> bool:
    """
    Find original text in a file and replace it with replacement.

    """
    _log.tool_call(
        "apply_patch",
        path=file_path,
        original_len=len(original),
        replacement_len=len(replacement),
    )

    path = Path(file_path)
    if not path.exists():
        _log.tool_result("apply_patch", success=False, reason="file_not_found")
        raise FileNotFoundError(f"File not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # Safety check — refuse to patch if original text isn't in the file
    if original not in content:
        _log.tool_result(
            "apply_patch",
            success=False,
            reason="original_not_found",
            path=file_path,
        )
        _log.warning(
            "Patch rejected — original text not found in file",
            path=file_path,
            search_len=len(original),
        )
        return False

    # Apply the replacement
    patched = content.replace(original, replacement, 1)  # only replace first match
    path.write_text(patched, encoding="utf-8")

    # Extra safety for Python files — check the syntax is still valid
    if path.suffix == ".py":
        try:
            ast.parse(patched)
            _log.debug("Python syntax valid after patch", path=file_path)
        except SyntaxError as exc:
            # Revert immediately — a broken file is worse than an unfixed bug
            _log.error(
                "Patch introduced a syntax error — reverting to original",
                path=file_path,
                error=str(exc),
            )
            path.write_text(content, encoding="utf-8")
            return False

    _log.tool_result("apply_patch", success=True, path=file_path)
    _log.patch(file_path, strategy="text_replace")
    return True