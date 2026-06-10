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

class AgentState(BaseModel):

    issue_url:            str
    repo_url:             str         = ""
    repo_local_path:      str         = ""

    issue_title:          str         = ""
    issue_body:           str         = ""
    bug_description:      str         = ""
    reproduction_steps:   List[str]   = Field(default_factory=list)
    affected_files_hint:  List[str]   = Field(default_factory=list)

    relevant_files:         List[str] = Field(default_factory=list)
    buggy_file:             str       = ""
    buggy_lines:            str       = ""
    localization_reasoning: str       = ""

    current_patch: Optional[CodePatch]= None
    patch_history: List[CodePatch]    = Field(default_factory=list)
    fix_strategy:  str                = ""

    test_result:  Optional[TestResult]= None
    test_history: List[TestResult]    = Field(default_factory=list)

    reflection_notes: str = ""
    retry_count:      int = 0
    max_retries:      int = 3

    branch_name: str      = ""
    pr_url:      str      = ""
    pr_number:   int      = 0

    status:            AgentStatus = AgentStatus.PENDING
    error_message:     str         = ""
    total_tokens_used: int         = 0
    run_id:            str         = ""
    started_at:        str         = ""
    finished_at:       str         = ""