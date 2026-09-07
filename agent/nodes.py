"""Planner / Tool Executor / Critic node implementations.

Each function takes and returns an AgentState (or a partial dict merged into it).
Fill in the actual GPT-4o calls and tool dispatch as Phase 2/3 land.
"""

from agent.state import AgentState


def planner_node(state: AgentState) -> AgentState:
    """Decide the next action given current context (logs, diff, prior attempts).

    TODO: call GPT-4o with the failure context + memory lookup result and let it
    choose between gathering more context or proposing a patch.
    """
    raise NotImplementedError


def tool_executor_node(state: AgentState) -> AgentState:
    """Dispatch to the tool the planner requested (fetch logs/diff, apply patch, etc).

    TODO: route based on state["next_action"] to functions in tools/.
    """
    raise NotImplementedError


def critic_node(state: AgentState) -> AgentState:
    """Validate the candidate patch in the Docker sandbox and return a verdict.

    TODO: apply state["candidate_patch"] in an ephemeral container, re-run the
    originally failing check, and set state["critic_verdict"] / critic_notes.
    """
    raise NotImplementedError
