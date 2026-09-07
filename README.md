# CI/CD AI Agent

An autonomous agent that watches GitHub Actions pipelines, diagnoses failures, and proposes (and validates) code fixes on its own.

When a CI run fails, the agent pulls the failing job's logs and the relevant commit/PR diff, reasons about the root cause with GPT-4o, and generates a targeted patch. Before anything is committed, the patch is applied inside an isolated Docker sandbox and re-run against the original failing check — only a patch that actually turns the build green gets pushed. Every run, decision, and patch is persisted so the agent can recognize a failure it has already fixed before and skip redundant LLM calls.

## How it works

The agent is a small graph of three cooperating nodes, built with LangGraph:

```
 GitHub Actions ──(failed run)──▶ Planner ──▶ Tool Executor ──▶ Critic
                                     ▲                              │
                                     └──────────(retry, bounded)────┘
                                                                     │
                                                          pass ──▶ commit / open PR
                                                          fail ──▶ report + stop
```

- **Planner** — a GPT-4o node that looks at the failure signature, logs, and diff, and decides what to do next: pull more context, or propose a patch.
- **Tool Executor** — executes whatever the Planner asked for: fetch logs, fetch diff, apply a patch, run tests in the sandbox.
- **Critic** — takes a proposed patch, applies it in a disposable Docker container, re-runs the failing check, and returns a verdict. A failing verdict loops back to the Planner (up to a retry limit); a passing verdict moves to commit.

Everything the agent sees and decides — logs, prompts, tool calls, patches, verdicts — is written to PostgreSQL. Before planning, the agent checks whether it has already seen this failure signature before and reuses that memory instead of re-running the LLM from scratch.

## Tech stack

| Concern | Choice |
|---|---|
| Agent orchestration | LangGraph |
| Reasoning | GPT-4o |
| CI integration | GitHub Actions REST/GraphQL API |
| Patch validation sandbox | Docker (ephemeral containers) |
| Persistence (runs, patches, memory) | PostgreSQL |
| Language | Python |

## Project status

Early scaffolding. See [`PLAN.md`](PLAN.md) for the phased build plan and [`docs/architecture.md`](docs/architecture.md) for the current design notes.

## Project layout

```
ci_cd_agent/
├── agent/          # LangGraph graph definition + Planner/Executor/Critic nodes
├── tools/          # GitHub API, log/diff retrieval, Docker sandbox, patch apply
├── db/             # SQLAlchemy models, migrations, memory lookup
├── api/            # Webhook/polling entrypoint that triggers agent runs
├── sandbox/        # Dockerfile for the disposable validation container
├── tests/          # Unit + integration tests, seeded failing repos
docker-compose.yml
requirements.txt
.env.example
```

## Getting started

```bash
cp .env.example .env   # fill in GITHUB_TOKEN, OPENAI_API_KEY, DB credentials
docker-compose up --build
```

This brings up PostgreSQL, the sandbox runner, and the agent service. See `.env.example` for required configuration.
