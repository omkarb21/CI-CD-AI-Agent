from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from nodes import (
    critic,
    gather_context,
    give_up,
    planner,
    push,
    route_after_critic,
    route_after_planner,
)
from state import State
from tools import TOOLS


def build_graph():
    g = StateGraph(State)
    g.add_node("gather_context", gather_context)
    g.add_node("planner", planner)
    g.add_node("tool_executor", ToolNode(TOOLS))
    g.add_node("critic", critic)
    g.add_node("push", push)
    g.add_node("give_up", give_up)

    g.add_edge(START, "gather_context")
    g.add_edge("gather_context", "planner")
    g.add_conditional_edges("planner", route_after_planner, ["tool_executor", "critic"])
    g.add_edge("tool_executor", "planner")
    g.add_conditional_edges("critic", route_after_critic, ["push", "planner", "give_up"])
    g.add_edge("push", END)
    g.add_edge("give_up", END)
    return g.compile()
