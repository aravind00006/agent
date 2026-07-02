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

def _parse_issue_url(issue_url: str) -> tuple[str, str, int]:
    """
    Break a GitHub issue URL into its parts.
    Returns: (owner, repo_name, issue_number)
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/issues/(\d+)"
    m = re.search(pattern, issue_url)
    if not m:
        raise ValueError(f"Cannot parse GitHub issue URL: {issue_url!r}")
    return m.group(1), m.group(2), int(m.group(3))

def _get_github_client() -> Github:
    """Create a GitHub API client using the token from .env"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        _log.warning("GITHUB_TOKEN not set — API rate limits will be very low")
    return Github(token)

