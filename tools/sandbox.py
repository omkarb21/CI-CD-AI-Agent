"""Docker sandbox tool: apply a patch and re-run the failing check in isolation."""

import os

import docker

SANDBOX_IMAGE = os.environ.get("SANDBOX_IMAGE", "ci-agent-sandbox:latest")
SANDBOX_TIMEOUT = int(os.environ.get("SANDBOX_TIMEOUT_SECONDS", "300"))
NETWORK_DISABLED = os.environ.get("SANDBOX_NETWORK_DISABLED", "true").lower() == "true"


def run_in_sandbox(repo_path: str, commit_sha: str, patch_diff: str, test_command: str) -> dict:
    """Checkout commit_sha, apply patch_diff, run test_command in an ephemeral container.

    Returns {"exit_code": int, "stdout": str, "stderr": str}.

    TODO:
      1. mount repo_path read-only (or a fresh clone) into the container
      2. checkout commit_sha, apply patch_diff via `git apply`
      3. run test_command with a timeout, network disabled per SANDBOX_NETWORK_DISABLED
      4. always remove the container afterwards (use client.containers.run with remove=True,
         or an explicit try/finally around container.stop()/remove())
    """
    client = docker.from_env()
    raise NotImplementedError
