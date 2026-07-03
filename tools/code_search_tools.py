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