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
_IMAGE     = "bugfixer-sandbox:latest"

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

    try:
        client = docker.from_env()
    except Exception as exc:
        _log.error("Could not connect to Docker", error=str(exc))
        return TestResult(
            passed=False,
            total_tests=0,
            failed_tests=0,
            error_output=str(exc),
            failure_reason="docker_not_available",
        )

    cmd = (
    f"bash -c 'pip install -e . -q 2>&1 && "
    f"{test_command} -v 2>&1'"
        )

    stdout = ""
    stderr = ""

    start = time.perf_counter()

    try:
        # Run with detach=True so we control output capture ourselves
        container = client.containers.run(
            image=_IMAGE,
            command=cmd,
            volumes={repo_path: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            mem_limit=_MEM_LIMIT,
            network_disabled=True,
            detach=True,           # run in background so we can stream logs
        )

        # Wait for it to finish and grab all output
        container.wait()
        raw_logs = container.logs(stdout=True, stderr=True)
        stdout   = raw_logs.decode("utf-8", errors="replace")
        _log.debug("FULL OUTPUT", output=stdout)
        container.remove()         # clean up manually since remove=True won't work with detach=True

    except Exception as exc:
        stdout = ""
        stderr = str(exc)
        _log.warning("Container error", error=str(exc)[:200])

    elapsed = time.perf_counter() - start
    _log.debug(
        "Docker sandbox finished",
        elapsed_s=round(elapsed, 2),
        stdout_chars=len(stdout),
    )

    # Show a snippet of the output in logs so we can debug
    if stdout:
        _log.debug("Test output snippet", snippet=stdout[:300])

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