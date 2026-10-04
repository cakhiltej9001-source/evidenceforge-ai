"""Phase 2 graph: fixed fan-out, all-predecessor join, then query generation."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from evidenceforge.config import ConfigurationError
from evidenceforge.graph.state import ResearchState
from evidenceforge.models.base import PlanningModel
from evidenceforge.nodes.context import ContextManager
from evidenceforge.nodes.manager import manager
from evidenceforge.nodes.planner import Planner
from evidenceforge.nodes.queries import QueryGenerator
from evidenceforge.planning import PlanningOptions
from evidenceforge.storage.context import ContextRepository


def build_planning_graph(
    model: PlanningModel,
    repository: ContextRepository,
    options: PlanningOptions | None = None,
) -> CompiledStateGraph[ResearchState, None, ResearchState, ResearchState]:
    if model.is_fixture is not True:
        raise ConfigurationError(
            "A live planning adapter is not implemented in Phase 2; no call was made."
        )
    options = options or PlanningOptions()
    graph = StateGraph(ResearchState)
    graph.add_node("manager", manager)
    graph.add_node("planner", Planner(model, options))
    graph.add_node("context_manager", ContextManager(repository, options))
    graph.add_node("query_generator", QueryGenerator(model, options))
    graph.add_edge(START, "manager")
    graph.add_edge("manager", "planner")
    graph.add_edge("manager", "context_manager")
    graph.add_edge(["planner", "context_manager"], "query_generator")
    graph.add_edge("query_generator", END)
    return graph.compile()
