import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import requests
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from tools import TOOLS

MODEL = "claude-haiku-4-5-20251001"
MAX_ATTEMPTS = 3
DEBUG_FILE = os.environ.get("DEBUG_FILE", "agent_debug.txt")

SYSTEM_PROMPT = (
    "A CI test failed in a small Python repo. You are given the failure log. "
    "Use the tools to read the code, find the cause, and fix it. "
    "Decide whether the bug is in the code or in the test, and fix the right one. "
    "Never delete tests or skip them. "
    "When you have finished editing, reply with a short explanation and no tool calls."
)


def log(msg: str = "") -> None:
    print(msg, flush=True)
    with open(DEBUG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _collect_count() -> int:
    out = _run([sys.executable, "-m", "pytest", "--collect-only", "-q"]).stdout
    m = re.search(r"(\d+) tests? collected", out)
    if m:
        return int(m.group(1))
    return len([l for l in out.splitlines() if "::" in l])


# ---------------------------------------------------------------- gather_context

def _clean(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return "\n".join(re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ", "", l) for l in text.splitlines())


def _trim_log(raw: str) -> str:
    lines = _clean(raw).splitlines()
    start = next((i for i, l in enumerate(lines) if re.search(r"=+ (FAILURES|ERRORS) =+", l)), None)
    if start is None:
        return "\n".join(lines[-100:])
    end = next((i for i in range(start, len(lines)) if "short test summary info" in lines[i]), None)
    if end is None:
        return "\n".join(lines[start:start + 150])
    summary_end = end + 1
    while summary_end < len(lines) and not lines[summary_end].startswith("====="):
        summary_end += 1
    return "\n".join(lines[start:summary_end])[:8000]


def _fetch_failed_job_log(repo: str, run_id: str, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{repo}/actions"
    jobs = requests.get(f"{base}/runs/{run_id}/jobs", headers=headers, timeout=30)
    jobs.raise_for_status()
    failed = [j for j in jobs.json()["jobs"] if j.get("conclusion") == "failure"]
    if not failed:
        raise RuntimeError(f"no failed job found in run {run_id}")
    resp = requests.get(f"{base}/jobs/{failed[0]['id']}/logs", headers=headers, timeout=60)
    resp.raise_for_status()
    if resp.content[:2] == b"PK":  # zipped
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            return "\n".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())
    return resp.text


def gather_context(state):
    log("=== GATHER_CONTEXT ===")
    run_id, repo = os.environ["RUN_ID"], os.environ["REPO"]
    raw = _fetch_failed_job_log(repo, run_id, os.environ["GITHUB_TOKEN"])
    trimmed = _trim_log(raw)
    count = _collect_count()
    log(f"run_id={run_id} repo={repo} test_count_before={count}")
    log("--- trimmed failure log ---")
    log(trimmed)
    msg = HumanMessage(f"CI failed. Failure log:\n\n{trimmed}")
    return {
        "run_id": run_id,
        "repo": repo,
        "failure_log": trimmed,
        "test_count_before": count,
        "attempts": 0,
        "messages": [msg],
    }


# ---------------------------------------------------------------- planner

_llm = None


def planner(state):
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model=MODEL, max_tokens=2048).bind_tools(TOOLS)
    log(f"=== PLANNER (attempt {state.get('attempts', 0) + 1}) ===")
    resp = _llm.invoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])
    for call in resp.tool_calls:
        log(f"tool call: {call['name']}({call['args']})")
    update = {"messages": [resp]}
    if not resp.tool_calls:
        update["explanation"] = _text(resp.content)
        log(f"planner explanation: {update['explanation']}")
    return update


def route_after_planner(state):
    return "tool_executor" if state["messages"][-1].tool_calls else "critic"


# ---------------------------------------------------------------- critic

def critic(state):
    attempts = state.get("attempts", 0) + 1
    log(f"=== CRITIC (attempt {attempts}) ===")
    result = _run([sys.executable, "-m", "pytest", "-v"])
    output = (result.stdout + result.stderr)[-3000:]
    log(output)
    passed = result.returncode == 0
    feedback = ""
    if passed:
        after = _collect_count()
        if after < state["test_count_before"]:
            passed = False
            feedback = (
                f"Tests passed but the test count dropped from {state['test_count_before']} to {after}. "
                "Do not delete tests. Fix the real problem."
            )
    else:
        feedback = f"pytest still fails:\n{output}"
    log(f"critic passed={passed}")
    update = {"attempts": attempts}
    if passed:
        update["status"] = "fixed"
    else:
        update["critic_feedback"] = feedback
        update["messages"] = [HumanMessage(feedback + "\n\nTry again.")]
    return update


def route_after_critic(state):
    if state.get("status") == "fixed":
        return "push"
    return "planner" if state["attempts"] < MAX_ATTEMPTS else "give_up"


# ---------------------------------------------------------------- push

def _git(*args: str) -> str:
    r = _run(["git", *args])
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout


def push(state):
    log("=== PUSH ===")
    diff = _git("diff")
    log(diff)
    if os.environ.get("DRY_RUN", "").lower() == "true":
        log("DRY_RUN is true: skipping branch push and PR")
        return {}
    if not diff.strip():
        log("no changes to push")
        return {"status": "gave_up"}

    run_id = state["run_id"]
    branch = f"agent-fix/{run_id}"
    changed = _git("diff", "--name-only").split()
    tests_changed = [f for f in changed if "test" in f.lower()]

    _git("config", "user.name", "ci-fix-agent")
    _git("config", "user.email", "ci-fix-agent@users.noreply.github.com")
    _git("checkout", "-B", branch)
    _git("add", "-u")
    _git("commit", "-m", f"fix: agent fix for CI run {run_id}")
    _git("push", "--force", "origin", branch)

    warning = f"**Test files modified:** {', '.join(tests_changed)}\n\n" if tests_changed else ""
    body = (
        f"Automated fix for failed CI run {run_id}.\n\n{warning}"
        f"## Explanation\n{state.get('explanation', '')}\n\n"
        f"## Failure log\n```\n{state['failure_log']}\n```\n\n"
        f"## Diff\n```diff\n{diff}\n```\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(body)
        body_file = f.name
    base = os.environ.get("BASE_BRANCH", "main")
    r = _run([
        "gh", "pr", "create", "--base", base, "--head", branch,
        "--title", f"Agent fix for CI run {run_id}", "--body-file", body_file,
        "--repo", state["repo"],
    ])
    log(r.stdout + r.stderr)
    if r.returncode != 0:
        raise RuntimeError("gh pr create failed")
    return {}


# ---------------------------------------------------------------- give_up

def give_up(state):
    log("=== GIVE_UP ===")
    log(f"attempts used: {state.get('attempts')}")
    log(f"last critic feedback:\n{state.get('critic_feedback', '')}")
    return {"status": "gave_up"}
