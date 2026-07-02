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

@tool
def fetch_github_issue(issue_url: str) -> dict:
    _log.tool_call("fetch_github_issue", issue_url=issue_url)

    try:
        owner, repo_name, issue_number = _parse_issue_url(issue_url)
        _log.debug("Parsed issue URL", owner=owner, repo=repo_name, issue=issue_number)

        gh    = _get_github_client()
        repo  = gh.get_repo(f"{owner}/{repo_name}")
        issue = repo.get_issue(issue_number)

        comments = [
            {"author": c.user.login, "body": c.body}
            for c in issue.get_comments()
        ][:10]

        result = {
            "number":     issue.number,
            "title":      issue.title,
            "body":       issue.body or "",
            "labels":     [lbl.name for lbl in issue.labels],
            "comments":   comments,
            "repo_url":   repo.clone_url,
            "state":      issue.state,
            "created_at": str(issue.created_at),
        }

        _log.tool_result("fetch_github_issue", success=True, title=issue.title, comments=len(comments))
        return result

    except GithubException as exc:
        _log.tool_result("fetch_github_issue", success=False, error=str(exc))
        raise RuntimeError(f"GitHub API error: {exc}") from exc
    
@tool
def clone_repository(repo_url: str, target_dir: str = "") -> str:
    _log.tool_call("clone_repository", repo_url=repo_url, target_dir=target_dir)

    dest = target_dir or tempfile.mkdtemp(prefix="bugfixer_repo_")
    _log.debug("Cloning into", dest=dest)

    try:
        with _log.timed(f"git clone {repo_url}"):
            Repo.clone_from(repo_url, dest, depth=1)

        _log.tool_result("clone_repository", success=True, path=dest)
        _log.success(f"Repository cloned → {dest}")
        return dest

    except GitCommandError as exc:
        _log.tool_result("clone_repository", success=False, error=str(exc))
        raise RuntimeError(f"Git clone failed: {exc}") from exc
    
