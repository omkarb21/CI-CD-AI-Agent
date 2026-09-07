"""Entrypoint: receives/polls for failed GitHub Actions runs and kicks off an agent run.

For Phase 1 this just needs to prove the wiring works end-to-end:
GitHub -> detect failure -> write a Run row to Postgres.
The actual LangGraph invocation gets wired in during Phase 3.
"""

from dotenv import load_dotenv

from db.session import init_db

load_dotenv()


def main() -> None:
    init_db()
    # TODO Phase 1: poll GitHub Actions (or receive a webhook) for failed runs,
    # write a Run + Failure row per failure.
    # TODO Phase 3: build_graph().invoke(initial_state) per new Failure.
    print("CI/CD AI Agent starting up. Database initialized.")


if __name__ == "__main__":
    main()
