from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict, total=False):
    run_id: str
    repo: str
    failure_log: str
    messages: Annotated[list, add_messages]
    test_count_before: int
    critic_feedback: str
    attempts: int
    explanation: str
    status: str  # "fixed" | "gave_up"
