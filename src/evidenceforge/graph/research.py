"""Full Phase 4 graph with bounded research and shared quality revisions."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.nodes.approval import after_approval, approve_plan, prepare_approval
from evidenceforge.nodes.context import ContextManager
from evidenceforge.nodes.extraction import EvidenceExtractor
from evidenceforge.nodes.intelligence import EvidenceIntelligence
from evidenceforge.nodes.manager import manager
from evidenceforge.nodes.planner import Planner
from evidenceforge.nodes.quality import (
    CitationChecker,
    CoverageEvaluator,
    Critic,
    Synthesis,
    can_rewrite,
    research_stop,
    reserve_rewrite,
)
from evidenceforge.nodes.queries import QueryGenerator
from evidenceforge.nodes.sources import SourceProcessor
from evidenceforge.planning import PlanningOptions
from evidenceforge.reporting import finalize
from evidenceforge.research import ResearchModel, ResearchOptions
from evidenceforge.storage.artifacts import ArtifactStore
from evidenceforge.storage.context import ContextRepository


def after_queries(state: ResearchState) -> str:
    if state["run_status"] != "running":
        return "finalizer"
    return "source_processor" if state["search_queries"] else "coverage_evaluator"


def after_coverage(state: ResearchState) -> str:
    s = StateSnapshot.model_validate(state)
    if s.run_status != "running":
        return "finalizer"
    if s.stop_reason is None and research_stop(s) is None:
        return "query_generator"
    return "synthesis" if s.evidence_store else "finalizer"


def after_synthesis(state: ResearchState) -> str:
    if state["stage_error"] == "synthesis":
        return "citation_checker" if state["draft_report"] else "finalizer"
    return "critic" if state["draft_report"] else "finalizer"


def after_critic(state: ResearchState) -> str:
    s = StateSnapshot.model_validate(state)
    if s.critic_verdict and s.critic_verdict.decision == "revise" and can_rewrite(s):
        return "reserve_rewrite"
    return "citation_checker"


def after_citations(state: ResearchState) -> str:
    s = StateSnapshot.model_validate(state)
    if any(
        not a.structural_valid or a.support != "supported" for a in s.citation_audit
    ) and can_rewrite(s):
        return "reserve_rewrite"
    return "finalizer"


def build_research_graph(
    model: ResearchModel,
    repository: ContextRepository,
    processor: SourceProcessor,
    extractor: EvidenceExtractor,
    artifacts: ArtifactStore,
    options: ResearchOptions,
    checkpointer: BaseCheckpointSaver[str] | None = None,
    pause_after: str | None = None,
) -> CompiledStateGraph[ResearchState, None, ResearchState, ResearchState]:
    if model.is_fixture is not True and not isinstance(model, GeminiResearchModel):
        raise ValueError("Unsupported live research model.")
    planning = PlanningOptions(available_source_types=tuple(processor.adapters))
    graph = StateGraph(ResearchState)
    graph.add_node("manager", manager)
    graph.add_node("planner", Planner(model, planning))
    graph.add_node("context_manager", ContextManager(repository, planning))
    graph.add_node(
        "prepare_approval", lambda state: prepare_approval(state, options.require_plan_approval)
    )
    graph.add_node("plan_approval", approve_plan)
    graph.add_node("query_generator", QueryGenerator(model, planning))
    graph.add_node("source_processor", processor)
    graph.add_node("evidence_extractor", extractor)
    graph.add_node("evidence_intelligence", EvidenceIntelligence(options.analysis))
    evaluator = CoverageEvaluator(model, options)

    async def coverage(state: ResearchState) -> dict[str, object]:
        from evidenceforge.graph.state import apply_update
        from evidenceforge.nodes.common import checked_patch

        update = await evaluator(state)
        candidate = apply_update(state, update)
        s = StateSnapshot.model_validate(candidate)
        reason = research_stop(s)
        if reason and candidate["stop_reason"] is None and s.run_status == "running":
            update["stop_reason"] = reason
        return checked_patch(state, update)

    graph.add_node("coverage_evaluator", coverage)
    graph.add_node("synthesis", Synthesis(model, options))
    graph.add_node("critic", Critic(model, options))
    graph.add_node("citation_checker", CitationChecker(artifacts))
    graph.add_node("reserve_rewrite", reserve_rewrite)
    graph.add_node("finalizer", finalize)
    graph.add_edge(START, "manager")
    graph.add_edge("manager", "planner")
    graph.add_edge("manager", "context_manager")
    graph.add_edge(["planner", "context_manager"], "prepare_approval")
    graph.add_edge("prepare_approval", "plan_approval")
    graph.add_conditional_edges("plan_approval", after_approval)
    graph.add_conditional_edges("query_generator", after_queries)
    graph.add_edge("source_processor", "evidence_extractor")
    graph.add_edge("evidence_extractor", "evidence_intelligence")
    graph.add_edge("evidence_intelligence", "coverage_evaluator")
    graph.add_conditional_edges("coverage_evaluator", after_coverage)
    graph.add_conditional_edges("synthesis", after_synthesis)
    graph.add_conditional_edges("critic", after_critic)
    graph.add_conditional_edges("citation_checker", after_citations)
    graph.add_edge("reserve_rewrite", "synthesis")
    graph.add_edge("finalizer", END)
    if pause_after is not None and pause_after not in {
        "query_generator",
        "source_processor",
        "evidence_extractor",
    }:
        raise ValueError("Unsupported checkpoint pause boundary.")
    return graph.compile(
        checkpointer=checkpointer, interrupt_after=[pause_after] if pause_after else None
    )
