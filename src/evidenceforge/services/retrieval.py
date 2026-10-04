"""Planning followed by one retrieval/extraction pass; reports remain unfinished."""

from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from evidenceforge.graph.state import ResearchState, StateSnapshot, validate_state
from evidenceforge.nodes.extraction import EvidenceExtractor
from evidenceforge.nodes.sources import SourceProcessor
from evidenceforge.retrieval.contracts import RetrievalAdapter, RetrievalOptions
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.planning import PlanningService
from evidenceforge.storage.artifacts import ArtifactStore
from evidenceforge.storage.calls import CallLedger


def build_retrieval_graph(
    processor: SourceProcessor,
    extractor: EvidenceExtractor,
) -> CompiledStateGraph[ResearchState, None, ResearchState, ResearchState]:
    graph = StateGraph(ResearchState)
    graph.add_node("source_processor", processor)
    graph.add_node("evidence_extractor", extractor)
    graph.add_edge(START, "source_processor")
    graph.add_edge("source_processor", "evidence_extractor")
    graph.add_edge("evidence_extractor", END)
    return graph.compile()


class RetrievalService:
    def __init__(
        self,
        data_dir: Path,
        adapters: dict[SourceType, RetrievalAdapter] | None = None,
        options: RetrievalOptions | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.adapters: dict[SourceType, RetrievalAdapter] = (
            adapters if adapters is not None else {SourceType.WEB: FixtureRetrievalAdapter()}
        )
        self.options = options or RetrievalOptions()

    def components(self, state: ResearchState) -> tuple[ArtifactStore, CallLedger]:
        snapshot = StateSnapshot.model_validate(state)
        return (
            ArtifactStore(
                self.data_dir / "artifacts",
                snapshot.owner_scope,
                snapshot.run_id,
                self.options.max_artifact_bytes,
            ),
            CallLedger(self.data_dir / "calls", snapshot.owner_scope, snapshot.run_id),
        )

    async def retrieve(self, state: ResearchState) -> ResearchState:
        state = validate_state(state)
        artifacts, ledger = self.components(state)
        graph = build_retrieval_graph(
            SourceProcessor(self.adapters, artifacts, ledger, self.options),
            EvidenceExtractor(artifacts, self.options),
        )
        result = await graph.ainvoke(state, config={"recursion_limit": 8})
        return validate_state(result)

    async def run(
        self, request: ResearchRequest, budget: BudgetLimits | None = None
    ) -> ResearchState:
        planned = await PlanningService().plan(request, budget)
        return await self.retrieve(planned)
