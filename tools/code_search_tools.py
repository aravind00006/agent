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
    
    matches: list[dict] = []
    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            matches.append({
                "file":         parts[0],
                "line_number":  int(parts[1]),
                "line_content": parts[2].strip(),
            })

    matches = matches[:_MAX_RESULTS]

    _log.tool_result("search_codebase", success=True, matches=len(matches), query=query)

    if not matches:
        _log.warning("No matches found", query=query, repo=repo_path)

    return matches

@tool
def find_function_definition(repo_path: str, function_name: str) -> List[dict]:
    """
    Find where a function is defined in the repository.
    """
    _log.tool_call("find_function_definition", repo=repo_path, fn=function_name)

    pattern = (
        rf"(def\s+{function_name}\s*\(|"
        rf"async\s+def\s+{function_name}\s*\(|"
        rf"function\s+{function_name}\s*\(|"
        rf"async\s+function\s+{function_name}\s*\()"
    )

    result = _run_ripgrep(["-e", pattern, repo_path])

    definitions: list[dict] = []
    if result.returncode == 0:
        for raw_line in result.stdout.splitlines()[:_MAX_RESULTS]:
            parts = raw_line.split(":", 2)
            if len(parts) >= 2:
                definitions.append({
                    "file_path":  parts[0],
                    "start_line": int(parts[1]) if parts[1].isdigit() else 0,
                    "full_code":  parts[2].strip() if len(parts) == 3 else "",
                })

    _log.tool_result("find_function_definition", success=True, fn=function_name, found=len(definitions))
    return definitions