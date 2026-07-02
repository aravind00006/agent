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
    
@tool
def create_branch(repo_local_path: str, branch_name: str) -> bool:
    _log.tool_call("create_branch", path=repo_local_path, branch=branch_name)

    try:
        repo = Repo(repo_local_path)
        repo.git.checkout("-b", branch_name)

        _log.tool_result("create_branch", success=True, branch=branch_name)
        _log.success(f"Branch created: {branch_name}")
        return True

    except GitCommandError as exc:
        _log.tool_result("create_branch", success=False, error=str(exc))
        raise RuntimeError(f"Branch creation failed: {exc}") from exc


@tool
def commit_and_push(repo_local_path: str, branch_name: str, commit_message: str) -> bool:
    _log.tool_call("commit_and_push", path=repo_local_path, branch=branch_name, message=commit_message[:80])

    try:
        repo = Repo(repo_local_path)
        repo.git.add("-A")
        repo.index.commit(commit_message)

        with _log.timed("git push"):
            repo.remotes.origin.push(branch_name)

        _log.tool_result("commit_and_push", success=True, branch=branch_name)
        _log.success(f"Committed and pushed → {branch_name}")
        return True

    except GitCommandError as exc:
        _log.tool_result("commit_and_push", success=False, error=str(exc))
        raise RuntimeError(f"Commit/push failed: {exc}") from exc
    
@tool
def open_pull_request(
    repo_url: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
) -> str:
    _log.tool_call("open_pull_request", branch=branch_name, title=title[:60], base=base_branch)

    try:
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", repo_url)
        if not m:
            raise ValueError(f"Cannot parse repo URL: {repo_url!r}")
        owner, repo_name = m.group(1), m.group(2)

        gh   = _get_github_client()
        repo = gh.get_repo(f"{owner}/{repo_name}")
        pr   = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )

        _log.tool_result("open_pull_request", success=True, pr_number=pr.number)
        _log.pr(pr.html_url, number=pr.number)
        return pr.html_url

    except GithubException as exc:
        _log.tool_result("open_pull_request", success=False, error=str(exc))
        raise RuntimeError(f"PR creation failed: {exc}") from exc