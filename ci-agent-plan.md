# CI Fix Agent — Implementation Plan (v1)

A LangGraph agent that runs inside GitHub Actions. When CI fails after a push to `main`, it reads the failure, reads the code, fixes it, re-runs the tests, and opens a PR (from a new branch into `main`) with the fix.

Everything is built and tested **directly on GitHub**. No local runs.

---

## 1. Scope for v1 (kept deliberately simple)

- **Single-branch flow:** you push to `main`; if CI fails, the agent reacts. No feature branches, no fork PRs.
- The agent lives **in the same repo** as billsplit, in an `agent/` folder.
- **Two workflows:** `ci.yml` (already exists) and a new `agent.yml`.
- **LLM:** Anthropic `claude-haiku-4-5-20251001` via `langchain-anthropic` (`ChatAnthropic`).
- **No Docker, no Postgres, no guards** beyond the basics in section 7. Token usage is limited by the API account itself.
- **Output:** the fix is pushed to a new branch `agent-fix/<run_id>` and a **PR into `main`** is opened. A PR needs two different branches, so the agent can't open a PR "on main" itself. Nothing is pushed to `main` directly.

---

## 2. Folder layout

```
billsplit-ci/
  billsplit.py
  test_billsplit.py
  requirements.txt
  .github/workflows/
    ci.yml
    agent.yml
  agent/
    requirements.txt   # langgraph, langchain-anthropic, requests
    main.py            # entry point: reads env vars, builds graph, runs it
    state.py           # State definition
    tools.py           # list_files, read_file, edit_file
    nodes.py           # gather_context, planner, critic, push, give_up
    graph.py           # wires nodes and edges
```

---

## 3. One-time GitHub setup (what you need to provide)

1. **Anthropic API key as a secret:** repo Settings → Secrets and variables → Actions → New repository secret, named `ANTHROPIC_API_KEY`.
2. **Allow Actions to open PRs:** Settings → Actions → General → Workflow permissions → check "Allow GitHub Actions to create and approve pull requests". Without this the PR step fails.
3. **`agent.yml` must be on `main`:** a `workflow_run` trigger only works from the default branch.

No other keys are needed. `GITHUB_TOKEN` is provided automatically.

---

## 4. The `agent.yml` workflow

**Two triggers:**

- `workflow_run` on the `CI` workflow, type `completed` — the real automatic trigger.
- `workflow_dispatch` with inputs `run_id` and `dry_run` (true/false) — a **manual "Run workflow" button** in the Actions tab. Use it to test and re-test the agent without breaking CI each time. Compare `dry_run` as the string `'true'`.

**Condition (automatic trigger):** only run if the CI conclusion was `failure`.

**Permissions:** `contents: write`, `pull-requests: write`, `actions: read`.

**Steps:**

1. Check out the repo at the failing commit (`workflow_run.head_sha`; for manual runs, look up the run's `head_sha` via the API or just use `main`).
2. Set up Python 3.11.
3. Install the app requirements and `agent/requirements.txt`.
4. Run `python agent/main.py` with env vars:
   - `RUN_ID` — from the event, or from the manual input
   - `REPO` — `github.repository`
   - `GITHUB_TOKEN` — `secrets.GITHUB_TOKEN`
   - `ANTHROPIC_API_KEY` — from secrets
   - `DRY_RUN` — if true, skip the push node
5. **Always** (`if: always()`) upload a debug file as an artifact: the final `git diff` and a text dump of what each node did. Logs in the Actions tab are your only window into the agent, so print clearly at each node.

---

## 5. The state

| Field | What it holds | Update style |
|---|---|---|
| `run_id`, `repo` | Which failure we're fixing | set once |
| `failure_log` | Trimmed error output from CI | set once |
| `messages` | Planner's conversation with the LLM, including tool calls | append (`add_messages`) |
| `test_count_before` | Number of tests before any edits | set once |
| `critic_feedback` | pytest output from the last failed attempt | overwrite |
| `attempts` | How many times the critic has run | overwrite (+1 each time) |
| `status` | `fixed` / `gave_up` | overwrite |

---

## 6. The graph

```
START → gather_context → planner ⇄ tool_executor
                            │
                            ▼  (planner stops calling tools)
                         critic
                  ┌─────────┼──────────┐
             passed      failed,      failed,
                │      attempts < 3  attempts = 3
                ▼          │              ▼
              push    back to planner   give_up
                ▼                         ▼
               END                       END
```

### gather_context (plain Python, no LLM)
- Call the GitHub API: list jobs in the run → find the failed job → download its log (the logs endpoint returns a redirect; follow it).
- **Trim** the log to the pytest failure section (from `FAILURES` to the short summary line). If there's no such section (collection errors, install failures), fall back to the last ~100 lines. Strip timestamps and ANSI codes.
- Record `test_count_before` using `pytest --collect-only -q`.
- Print the trimmed log so it appears in the Actions output.

### planner (LLM: Haiku)
- System prompt, roughly: *"A CI test failed. Here is the log. Use the tools to read the code, find the cause, and fix it. Decide whether the bug is in the code or in the test. When you have finished editing, reply with a short explanation and no tool calls."*
- On retries, it also gets `critic_feedback`.
- Print each tool call it requests.

### tool_executor (LangGraph's prebuilt `ToolNode`)
Three tools:
- `list_files()` — so the LLM knows what exists (skip `.git`, `agent/`, caches).
- `read_file(path)`
- `edit_file(path, old_text, new_text)` — replace one exact piece of text. Return a clear error if `old_text` is found zero times or more than once.

**Routing after planner:** if the last message has tool calls → `tool_executor`; otherwise → `critic`.

### critic (plain Python)
1. Run `pytest -v` with `subprocess`, capture output and exit code.
2. **Guard:** compare `pytest --collect-only -q` count with `test_count_before`. Fewer tests = failure, even if pytest passed (blocks "delete the failing test").
3. Increment `attempts`; on failure, save pytest output to `critic_feedback`.

**Routing after critic:** passed → `push`; failed and `attempts < 3` → `planner`; otherwise → `give_up`.

### push (plain Python)
- If `DRY_RUN` → print `git diff` and stop.
- Otherwise: set a bot git name/email, create branch `agent-fix/<run_id>`, commit, `git push origin agent-fix/<run_id>`.
- Open a PR **into `main`** with the `gh` CLI (preinstalled on runners, uses `GITHUB_TOKEN`). PR body: the trimmed failure log, the planner's explanation, and the diff. If test files changed, say so prominently in the body.

### give_up
- Print what was tried and the last `critic_feedback`. Exit with a non-zero code so the workflow shows as failed.

---

## 7. Loop safety (minimal)

- Pushes and PRs made with `GITHUB_TOKEN` don't trigger new workflow runs, so the agent's branch won't re-trigger CI or the agent. **Consequence:** CI will not run on the agent's PR; the critic's local pytest run is the only verification before you merge.
- `attempts` limit of 3 inside one run.
- LangGraph `recursion_limit` (e.g. 50) so a planner stuck calling tools stops.
- Optional cheap extra: skip the agent when `workflow_run.head_branch` starts with `agent-fix/`, in case you switch tokens later.

---

## 8. Build order (all on GitHub)

Each milestone is one commit to `main`, tested with the **Run workflow** button. Keep `DRY_RUN=true` until milestone 6.

1. **Skeleton workflow.** `agent.yml` with both triggers that just prints `RUN_ID` and runs `pytest -v || true`. Confirms secrets, checkout and triggers work. Push a failing commit once to see the automatic trigger fire.
2. **gather_context only.** `main.py` fetches and trims the log for a real failed run ID and prints it. Check the printed log is just the useful part.
3. **Tools.** Add `tools.py`. Temporarily call each tool directly from `main.py` and print the results (e.g. read `billsplit.py`, try an `edit_file` with text that doesn't exist and check the error message).
4. **Planner + tool_executor loop.** Build the graph up to the planner, ending after it stops calling tools. Print `git diff`. Check it edited the **test**, not `split_evenly`.
5. **Critic + retry edge.** Add the critic and conditional edges. Check the printed attempt count and pytest result.
6. **Push node.** Set `DRY_RUN=false`. Confirm the `agent-fix/<run_id>` branch and the PR appear.
7. **End to end.** Break a test on `main` and let the automatic trigger do everything.

**Tip:** every print matters. At each node, print a header like `=== CRITIC (attempt 2) ===` and the key values.

---

## 9. Decisions made

1. **LLM:** Claude Haiku (`claude-haiku-4-5-20251001`) via `langchain-anthropic`.
2. **PR, not direct push:** fix goes to `agent-fix/<run_id>`, PR targets `main`.
3. **`failure_log` source:** the GitHub API (matches the project description), not re-running pytest on the runner.
4. **Single-branch flow:** only `main`; no feature-branch or fork handling.

---

## 10. Known limitations / later additions (not in v1)

- No CI run on the agent's PR (needs a PAT or GitHub App token, which brings back the need for a loop guard).
- Test-count guard doesn't catch weakened tests (`skip`, `xfail`, changed expected values) — review the PR.
- Tools aren't path-restricted, and the critic runs pytest with secrets in the environment. Add path checks and a scrubbed env later.
- Failure logs are untrusted input to the LLM (prompt injection risk).
- Pin `langgraph` / `langchain-anthropic` versions once things work.
- Run the critic inside a Docker container with no network and no secrets.
- Postgres: LangGraph checkpointer for crash recovery, plus tables for patch history and success-rate metrics.
- A benchmark set of intentionally broken commits to measure the success rate.
