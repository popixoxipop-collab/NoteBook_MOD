import streamlit as st
from langgraph.graph import StateGraph
from state import ReviewState
from agents.analyzer_node import analyzer_node
from agents.critic_node import critic_node
from agents.supervisor_node import supervisor_node
from graph.route_next import route_next

llm = None


@st.cache_resource
def build_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("analyzer",   analyzer_node)
    builder.add_node("critic",     critic_node)
    builder.add_node("supervisor", supervisor_node)
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges("supervisor", route_next, {
        "analyzer": "analyzer",
        "critic":   "critic",
        "end":      "__end__",
    })
    builder.add_edge("analyzer", "supervisor")
    builder.add_edge("critic",   "supervisor")
    return builder.compile()
