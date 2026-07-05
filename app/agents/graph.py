from collections.abc import AsyncGenerator

from app.agents.nodes.comparator_node import comparator_node
from app.agents.nodes.reporter_node import reporter_node
from app.agents.nodes.retriever_node import retriever_node
from app.agents.nodes.sentiment_node import sentiment_node
from app.agents.nodes.supervisor import supervisor_node
from app.agents.state import AgentState


def run_graph(initial_state: AgentState) -> AgentState:
    state = initial_state
    for _ in range(8):
        state = supervisor_node(state)
        step = state.get("next_step")
        if step == "retriever":
            state = retriever_node(state)
        elif step == "comparator":
            state = comparator_node(state)
        elif step == "sentiment":
            state = sentiment_node(state)
        elif step == "reporter":
            state = reporter_node(state)
        else:
            break
    return state


async def stream_graph(initial_state: AgentState) -> AsyncGenerator[dict, None]:
    state = initial_state
    for event_name, node in (
        ("supervisor", supervisor_node),
        ("retriever", retriever_node),
        ("comparator", comparator_node),
        ("sentiment", sentiment_node),
        ("reporter", reporter_node),
    ):
        state = node(state)
        yield {"event": event_name, "state": state}


try:
    from langgraph.graph import END, StateGraph

    def build_langgraph():
        graph = StateGraph(AgentState)
        graph.add_node("supervisor", supervisor_node)
        graph.add_node("retriever", retriever_node)
        graph.add_node("comparator", comparator_node)
        graph.add_node("sentiment", sentiment_node)
        graph.add_node("reporter", reporter_node)
        graph.set_entry_point("supervisor")
        graph.add_conditional_edges(
            "supervisor",
            lambda state: state.get("next_step", "end"),
            {
                "retriever": "retriever",
                "comparator": "comparator",
                "sentiment": "sentiment",
                "reporter": "reporter",
                "end": END,
            },
        )
        graph.add_edge("retriever", "supervisor")
        graph.add_edge("comparator", "supervisor")
        graph.add_edge("sentiment", "supervisor")
        graph.add_edge("reporter", "supervisor")
        return graph.compile()

except Exception:
    build_langgraph = None
