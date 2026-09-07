"""LangGraph wiring: Planner -> Tool Executor -> Critic, with a bounded retry loop."""

from langgraph.graph import END, StateGraph

from agent.nodes import critic_node, planner_node, tool_executor_node
from agent.state import AgentState


def route_after_planner(state: AgentState) -> str:
    if state.get("next_action") == "propose_patch":
        return "tool_executor"
    if state.get("next_action") == "gather_context":
        return "tool_executor"
    return "give_up"


def route_after_critic(state: AgentState) -> str:
    if state.get("critic_verdict") == "pass":
        return "commit"
    if state["iteration"] >= state["max_iterations"]:
        return "give_up"
    return "planner"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {"tool_executor": "tool_executor", "give_up": END},
    )
    graph.add_edge("tool_executor", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"commit": END, "planner": "planner", "give_up": END},
    )

    return graph.compile()
