"""
Talk to GitHub: fetch issues, clone repos, open PRs.

"""

from __future__ import annotations

import os
import re
import tempfile
from github import Github, GithubException
from git import Repo, GitCommandError
from langchain_core.tools import tool
from core.logger import get_logger

_log = get_logger("tools")