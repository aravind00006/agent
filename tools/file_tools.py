"""
This file Read, write, list, and patch files on disk.
These are the agent's hands — without these tools the AI can think
but can't actually touch anything on the filesystem.

"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool
from core.logger import get_logger

_log = get_logger("tools")