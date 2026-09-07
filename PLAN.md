# Build Plan

Five phases, each with a concrete exit criteria so progress is checkable.

## Phase 1 — Foundations & Architecture Skeleton
Repo structure, PostgreSQL schema, Docker Compose, and a stub that detects a failed
GitHub Actions run and writes it to the database. No intelligence yet.

**Exit criteria:** `docker-compose up` runs the agent service; a failed GH Actions run
gets persisted to Postgres.

## Phase 2 — Tool Layer (GitHub + Sandbox + Diff/Log Retrieval)
All the "hands" the agent will use, independently testable before any LLM is involved:
GitHub Actions log/diff retrieval, Docker sandbox execution, patch apply/rollback.

**Exit criteria:** Given a known failing commit SHA, tools can fetch logs, fetch diff,
reproduce the failure in Docker, and apply + revert a sample patch — all via tests,
no agent loop yet.

## Phase 3 — LangGraph Multi-Node Agent (Planner → Tool Executor → Critic)
The reasoning loop: Planner (GPT-4o) decides the next action, Tool Executor dispatches
to Phase 2 tools, Critic validates a proposed patch in the sandbox and loops back to
the Planner on failure (bounded retries).

**Exit criteria:** End-to-end on a seeded failing repo: agent proposes a patch, Critic
validates it in the sandbox, loop terminates with a validated patch or a "couldn't fix"
report.

## Phase 4 — Persistence, Memory & Commit Flow
Persist full agent trajectories in Postgres. Before planning, look up similar past
failures by error signature to skip redundant LLM calls. On Critic approval, commit
the patch and open a PR via the GitHub API; on repeated failure, report instead.

**Exit criteria:** Agent runs against a real repo's failing CI and opens a real PR on
success; a repeated identical failure measurably skips redundant planning calls.

## Phase 5 — Hardening, Observability & Evaluation
Guardrails (patch size limits, path denylist, sandbox resource/time/network limits),
structured logging, a simple dashboard over Postgres, and an evaluation harness against
seeded failure scenarios (lint error, failing unit test, dependency break).

**Exit criteria:** Reproducible eval report with fix success rate, iterations-to-fix,
and LLM call count with/without memory.
