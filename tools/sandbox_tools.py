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
    
    g      = summary.groups()
    passed = int(g[0] or g[3] or 0)
    failed = int(g[1] or g[2] or 0)
    total  = passed + failed
    all_ok = failed == 0 and total > 0

    fail_section = ""
    if not all_ok:
        m = re.search(r"(FAILURES|ERRORS)(.*?)=====", combined, re.DOTALL)
        if m:
            fail_section = m.group(2)[:2000]

    return TestResult(
        passed=all_ok,
        total_tests=total,
        failed_tests=failed,
        error_output=fail_section or combined[:2000],
        failure_reason=None if all_ok else f"{failed} test(s) failed",
    )

def _run_in_docker(repo_path: str, test_command: str) -> TestResult:
    """Run test_command inside an isolated Docker container."""
    try:
        import docker
    except ImportError:
        raise RuntimeError("docker SDK not installed. Run: pip install docker")

    _log.step("Starting Docker sandbox", image=_IMAGE, command=test_command)
    client = docker.from_env()

    cmd   = f"bash -c 'pip install -e . -q 2>&1 && {test_command} -v 2>&1'"
    start = time.perf_counter()

    try:
        raw = client.containers.run(
            image=_IMAGE,
            command=cmd,
            volumes={repo_path: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            mem_limit=_MEM_LIMIT,
            network_disabled=True,
            remove=True,
            timeout=_TIMEOUT,
        )
        stdout = raw.decode("utf-8", errors="replace")
        stderr = ""

    except Exception as exc:
        stdout = ""
        stderr = str(exc)
        _log.warning("Container exited with error", error=str(exc)[:200])

        elapsed = time.perf_counter() - start
    _log.debug(
        "Docker sandbox finished",
        elapsed_s=round(elapsed, 2),
        stdout_chars=len(stdout),
    )

    return _parse_pytest_output(stdout, stderr)

@tool
def run_tests_in_sandbox(repo_path: str, test_command: str = "pytest") -> dict:
    """
    Run the test suite inside an isolated Docker container.
    """
    _log.tool_call("run_tests_in_sandbox", repo=repo_path, cmd=test_command)

    with _log.timed(f"sandbox [{test_command}]"):
        result = _run_in_docker(repo_path, test_command)

    status = "PASS ✅" if result.passed else "FAIL ❌"
    _log.info(
        f"Test result: {status}",
        total=result.total_tests,
        failed=result.failed_tests,
        reason=result.failure_reason,
    )
    _log.tool_result("run_tests_in_sandbox", success=result.passed)

    return result.model_dump()