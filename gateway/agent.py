"""
LangGraph Agent — Orchestrates tool calls using a state graph.

This agent uses LangGraph's StateGraph to:
1. Analyze the incoming query via the smart router
2. Call the appropriate tools in parallel
3. Rank and aggregate results
4. Return a unified PersonalContext

Works without an LLM (rule-based routing). If an LLM is configured,
it can be used for smarter routing and summarization.
"""

import json
import logging
from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from gateway.router import route_query
from gateway.ranker import merge_and_rank
from gateway.context import PersonalContext

logger = logging.getLogger(__name__)


# ── Agent State ──

class AgentState(TypedDict):
    """State passed through the LangGraph nodes."""
    query: str
    routes: list[dict[str, Any]]
    tool_results: dict[str, Any]
    context: dict[str, Any]


# ── Graph Nodes ──

def analyze_query(state: AgentState) -> AgentState:
    """Route the query to determine which tools to call."""
    routes = route_query(state["query"])
    logger.info(f"Query routed to {len(routes)} categories: {[r['category'] for r in routes]}")
    return {**state, "routes": routes}


def execute_tools(state: AgentState) -> AgentState:
    """Execute the tools determined by the router."""
    results: dict[str, Any] = {}
    query = state["query"]

    for route in state["routes"]:
        category = route["category"]

        try:
            if category == "semantic":
                from core_mcp.tools.search import semantic_search
                results["semantic"] = semantic_search(query, top_k=5)

            elif category == "graph":
                from knowledge_graph.graph_store import GraphStore
                if not hasattr(execute_tools, '_graph_store'):
                    execute_tools._graph_store = GraphStore()
                store = execute_tools._graph_store
                if store.is_connected():
                    graph_data = store.graph_search(query, max_depth=2)
                    results["graph"] = graph_data.get("results", [])
                else:
                    results["graph"] = []

            elif category == "notes":
                from core_mcp.tools.notes import list_notes
                results["notes"] = list_notes()

            elif category == "activity":
                from core_mcp.event_logger.database import get_recent_events
                results["activity"] = get_recent_events(limit=20)

            elif category == "browser":
                from connectors.browser_mcp.tools import get_recent_history, search_history
                if any(kw in query.lower() for kw in ["search", "find"]):
                    results["browser"] = search_history(query, limit=10)
                else:
                    results["browser"] = get_recent_history(limit=10)

            elif category == "code":
                from connectors.code_mcp.tools import get_vscode_recent_files
                results["code"] = get_vscode_recent_files()

            elif category == "files":
                from connectors.files_mcp.tools import list_files
                results["files"] = list_files("./data", recursive=True)

            elif category == "stats":
                from core_mcp.tools.search import get_index_stats
                results["stats"] = get_index_stats()

        except Exception as e:
            logger.warning(f"Tool execution failed for {category}: {e}")
            results[category] = [{"error": str(e)}]

    return {**state, "tool_results": results}


def build_context(state: AgentState) -> AgentState:
    """Aggregate and rank all tool results into a PersonalContext."""
    results = state["tool_results"]
    ctx = PersonalContext(query=state["query"])

    # Add semantic search results
    semantic = results.get("semantic", [])
    if isinstance(semantic, list):
        ctx.semantic_results = semantic
        for r in semantic[:5]:
            ctx.add_source(
                source="semantic_search",
                content=r.get("content", str(r))[:300],
                relevance=r.get("relevance", 0.5),
                filename=r.get("filename", ""),
            )

    # Add graph results
    graph = results.get("graph", [])
    if isinstance(graph, list):
        ctx.graph_results = graph
        for r in graph[:5]:
            connections = r.get("connections", [])
            content = f"{r.get('entity', '')} ({r.get('type', '')}) -> {len(connections)} connections"
            ctx.add_source(
                source="knowledge_graph",
                content=content,
                relevance=min(1.0, len(connections) / 10.0),
            )

    # Add recent activity
    activity = results.get("activity", [])
    if isinstance(activity, list):
        ctx.recent_activity = activity[:10]
        for e in activity[:5]:
            ctx.add_source(
                source="recent_activity",
                content=f"[{e.get('event_type', '')}] {e.get('src_path', '')}",
                relevance=0.3,
            )

    # Add notes listing
    notes = results.get("notes", [])
    if isinstance(notes, list):
        for n in notes[:5]:
            ctx.add_source(
                source="notes",
                content=f"{n.get('name', '')} ({n.get('size_bytes', 0)} bytes)",
                relevance=0.4,
            )

    # Add browser history
    browser = results.get("browser", [])
    if isinstance(browser, list):
        for b in browser[:5]:
            ctx.add_source(
                source="browser_history",
                content=f"{b.get('title', '')}: {b.get('url', '')}",
                relevance=0.3,
            )

    # Add code/VSCode results
    code = results.get("code", [])
    if isinstance(code, list):
        for c in code[:5]:
            ctx.add_source(
                source="code_activity",
                content=f"[{c.get('type', '')}] {c.get('path', '')}",
                relevance=0.3,
            )

    # Sort sources by relevance
    ctx.sources = ctx.ranked_sources()
    ctx.total_sources = len(ctx.sources)

    return {**state, "context": ctx.model_dump()}


# ── Build the Graph ──

def create_agent() -> StateGraph:
    """Create and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze", analyze_query)
    workflow.add_node("execute", execute_tools)
    workflow.add_node("aggregate", build_context)

    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "execute")
    workflow.add_edge("execute", "aggregate")
    workflow.add_edge("aggregate", END)

    return workflow.compile()


# Singleton compiled agent
_agent = None


def get_agent():
    """Get or create the compiled agent."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


def query_context(query: str) -> dict[str, Any]:
    """
    Run a query through the agent and return PersonalContext.

    This is the main entry point for the gateway.

    Args:
        query: Natural language query.

    Returns:
        PersonalContext dict with ranked results from all sources.
    """
    agent = get_agent()
    initial_state: AgentState = {
        "query": query,
        "routes": [],
        "tool_results": {},
        "context": {},
    }

    result = agent.invoke(initial_state)
    return result["context"]
