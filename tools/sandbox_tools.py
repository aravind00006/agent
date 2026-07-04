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