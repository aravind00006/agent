"""
Run tests safely inside an isolated Docker container.
"""

from __future__ import annotations
import os
import re
import time
from langchain_core.tools import tool
from core.logger import get_logger
from state.agent_state import TestResult

_log = get_logger("sandbox")

_TIMEOUT   = 120
_MEM_LIMIT = "512m"
_IMAGE     = "python:3.11-slim"

def _parse_pytest_output(stdout: str, stderr: str) -> TestResult:
    """Read pytest output and return a structured TestResult."""
    combined = stdout + "\n" + stderr

    if "timed out" in combined.lower():
        _log.warning("Test suite timed out", timeout_s=_TIMEOUT)
        return TestResult(
            passed=False, total_tests=0, failed_tests=0,
            error_output=combined[:2000], failure_reason="timeout",
        )

    if "ImportError" in combined or "ModuleNotFoundError" in combined:
        _log.warning("Test suite failed with import error")
        return TestResult(
            passed=False, total_tests=0, failed_tests=0,
            error_output=combined[:2000], failure_reason="import_error",
        )
    
    summary = re.search(
        r"(\d+) passed(?:,\s*(\d+) failed)?|(\d+) failed(?:,\s*(\d+) passed)?",
        combined,
    )

    if not summary:
        _log.error("Could not parse pytest output — treating as failure")
        return TestResult(
            passed=False, total_tests=0, failed_tests=0,
            error_output=combined[:2000], failure_reason="unparseable_output",
        )