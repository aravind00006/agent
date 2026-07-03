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

@tool
def search_codebase(repo_path: str, query: str) -> List[dict]:
    """
    Search for a text pattern across all files in the repository.
    """
    _log.tool_call("search_codebase", repo=repo_path, query=query)

    result = _run_ripgrep([query, repo_path, "--max-count=20"])

    if result.returncode == 2:
        _log.tool_result("search_codebase", success=False, stderr=result.stderr[:200])
        raise RuntimeError(f"ripgrep error: {result.stderr}")