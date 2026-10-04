# CI/CD AI Agent

An agent that runs inside GitHub Actions. When CI fails after a push to `main`, it reads the failing job's log, finds the cause, edits the code, re-runs the tests, and opens a pull request with the fix.

The repo contains a small demo app (`billsplit.py` with tests in `test_billsplit.py`). One test is intentionally wrong (`test_split_100_between_4`) so you can watch the agent work.

## How it works

```
push to main ──▶ CI (ci.yml) fails ──▶ CI Fix Agent (agent.yml)
                                              │
 gather_context ─▶ planner ⇄ tool_executor ─▶ critic ─┬─ pass ─▶ push branch + open PR
                      ▲                               ├─ fail, attempts < 3 ─▶ back to planner
                      └───────────────────────────────┘
                                                      └─ fail, attempts = 3 ─▶ give up
```

- **gather_context** (plain Python): fetches the failed job's log from the GitHub API, trims it to the pytest failure section, and records the test count.
- **planner** (Claude Haiku via `langchain-anthropic`): reads the log, uses the tools, and decides whether the bug is in the code or in the test.
- **tool_executor**: LangGraph `ToolNode` with three tools: `list_files`, `read_file`, `edit_file`. Paths are restricted to the repo.
- **critic** (plain Python): runs `pytest -v`. It also fails the attempt if the test count dropped, which blocks "delete the failing test". Up to 3 attempts.
- **push** (plain Python): creates the branch `agent-fix/<run_id>`, commits, pushes, and opens a PR into `main` with the failure log, the explanation and the diff. The PR flags any modified test files.
- **give_up**: prints what was tried and exits non-zero.

Nothing is pushed to `main` directly. You review and merge the PR.

## Setup

1. Add a repo secret named `ANTHROPIC_API_KEY` (Settings → Secrets and variables → Actions). Paste the key without quotes.
2. Enable Settings → Actions → General → Workflow permissions → "Allow GitHub Actions to create and approve pull requests".
3. Keep `agent.yml` on `main`, since `workflow_run` triggers only work from the default branch. The `name:` in `ci.yml` must stay `CI`.

`GITHUB_TOKEN` is provided automatically. No keys are stored in the code.

## Running it

- **Automatic:** push a commit to `main` that breaks CI. The "CI Fix Agent" workflow starts when CI completes and opens a PR.
- **Manual:** Actions → "CI Fix Agent" → Run workflow. Enter the `run_id` of a failed CI run (the number in its URL).
  - `dry_run` on (default): runs the full pipeline but only prints the diff. No branch, no PR.
  - `dry_run` off: pushes the branch and opens the PR.
  - Automatic runs are never dry.

Each run uploads an `agent-debug` artifact with the node-by-node log and the final diff.

## Project layout

```
billsplit.py            # demo app
test_billsplit.py       # demo tests (one intentionally wrong)
requirements.txt        # app requirements
ci-agent-plan.md        # design and build plan
.github/workflows/
  ci.yml                # runs pytest on push / PR
  agent.yml             # runs the agent when CI fails
agent/
  requirements.txt      # langgraph, langchain-core, langchain-anthropic, requests
  main.py               # entry point
  state.py              # graph state
  tools.py              # list_files, read_file, edit_file
  nodes.py              # gather_context, planner, critic, push, give_up
  graph.py              # wires nodes and edges
```

## Known limitations

- CI does not run on the agent's PR, because PRs opened with `GITHUB_TOKEN` don't trigger workflows. The critic's local pytest run is the only check before you merge.
- The test-count guard doesn't catch weakened tests (`skip`, `xfail`, changed expected values). Review the PR diff.
- Handles only pushes to `main`. No feature-branch or fork support.
- The failure log is untrusted input to the LLM, and the critic runs pytest with secrets in its environment.

## Possible later additions

- Run the critic in a Docker container with no network and no secrets.
- PostgreSQL for LangGraph checkpoints, patch history and success-rate metrics.
- A benchmark set of intentionally broken commits to measure the success rate.
- A PAT or GitHub App token so CI runs on the agent's PR (this needs a loop guard).
