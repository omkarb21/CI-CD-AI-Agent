"""Shared state passed between LangGraph nodes."""

from typing import Literal, TypedDict


class AgentState(TypedDict, total=False):
    repo: str
    commit_sha: str
    job_name: str
    log_excerpt: str
    diff_context: str
    error_signature: str

    planner_reasoning: str
    next_action: Literal["gather_context", "propose_patch", "commit", "give_up"]

    candidate_patch: str
    critic_verdict: Literal["pass", "fail"]
    critic_notes: str

    iteration: int
    max_iterations: int
