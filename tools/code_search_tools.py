"""
Search a codebase for patterns and function definitions.
"""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import List
from langchain_core.tools import tool
from core.logger import get_logger

_log = get_logger("tools")

_MAX_RESULTS = 20

def _run_ripgrep(args: list[str]) -> subprocess.CompletedProcess:
    """Run ripgrep with the given arguments and return the result."""
    cmd = ["rg", "--no-heading", "--line-number", "--color=never"] + args
    _log.debug("Running ripgrep", cmd=" ".join(cmd[:6]) + " ...")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)