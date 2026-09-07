"""GitHub Actions API tool: fetch failed run logs and diff context."""

import os

from github import Github


def get_client() -> Github:
    token = os.environ["GITHUB_TOKEN"]
    return Github(token)


def get_failed_jobs(repo_name: str, workflow_run_id: int):
    """Return the failed jobs for a given workflow run.

    TODO: use gh.get_repo(repo_name).get_workflow_run(workflow_run_id).jobs()
    and filter to conclusion == "failure".
    """
    raise NotImplementedError


def get_job_logs(repo_name: str, job_id: int) -> str:
    """Fetch raw logs for a single job.

    TODO: PyGithub doesn't expose job logs directly; use the REST endpoint
    GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs via requests + token auth.
    """
    raise NotImplementedError


def get_commit_diff(repo_name: str, commit_sha: str) -> str:
    """Fetch the diff for the commit associated with the failing run."""
    raise NotImplementedError


def open_pull_request(repo_name: str, branch: str, base: str, title: str, body: str) -> str:
    """Push a fix branch and open a PR; return the PR URL."""
    raise NotImplementedError
