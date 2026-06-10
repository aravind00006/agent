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

