"""
agent_state.py — The shared notebook passed between all agents.

"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class AgentStatus(str, Enum):
    PENDING     = "pending"
    RUNNING     = "running"
    SUCCESS     = "success"
    FAILED      = "failed"
    MAX_RETRIES = "max_retries"

class TestResult(BaseModel):
    passed:         bool
    total_tests:    int
    failed_tests:   int
    error_output:   str
    failure_reason: Optional[str] = None

class CodePatch(BaseModel):
    file_path:     str
    original_code: str
    patched_code:  str
    explanation:   str
    diff:          str

