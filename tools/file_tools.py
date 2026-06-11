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