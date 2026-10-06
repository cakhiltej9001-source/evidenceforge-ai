"""Bounded research with local evidence and atomic report delivery."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Command
from langsmith import tracing_context

from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.evidence.projection import audit, project, render_inspection
from evidenceforge.graph.research import build_research_graph
from evidenceforge.graph.state import (
    ResearchState,
    StateSnapshot,
    apply_update,
    initial_state,
    validate_state,
)
from evidenceforge.guardrails import require_research_request
from evidenceforge.identity import stable_id
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.nodes.common import record_data
from evidenceforge.nodes.extraction import EvidenceExtractor
from evidenceforge.nodes.quality import CitationChecker
from evidenceforge.nodes.quality_common import quality_error
from evidenceforge.nodes.sources import SourceProcessor
from evidenceforge.planning import ModelUnavailable, PlanDraft, normalized
from evidenceforge.reporting import finalize, render_report
from evidenceforge.research import ResearchModel, ResearchOptions
from evidenceforge.retrieval.carbon_intensity import CarbonIntensityAdapter
from evidenceforge.retrieval.contracts import CallReceipt, RetrievalAdapter, RetrievalBatch
from evidenceforge.retrieval.documents import DocumentRetrievalAdapter
from evidenceforge.retrieval.fallback import OrderedSearch
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.retrieval.tavily import TavilyAdapter
from evidenceforge.retrieval.wikipedia import WikipediaAdapter
from evidenceforge.schemas import (
    BudgetLimits,
    ResearchQuestion,
    ResearchRequest,
    RunEvent,
    SourceType,
    utc_now,
)
from evidenceforge.services.cancellation import RunCancellation
from evidenceforge.services.node_trace import NodeTrace
from evidenceforge.services.observability import TraceSink, public_progress, trace_phase
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.services.usage import PriceTable, usage_summary
from evidenceforge.storage.checkpoints import CheckpointFailure, CheckpointRepository
from evidenceforge.storage.context import ContextRepository
from evidenceforge.storage.documents import DocumentStore
from evidenceforge.storage.local_context import LocalContextRepository
from evidenceforge.storage.reports import ReportRepository


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class ResearchService:
    def __init__(
        self,
        data_dir: Path,
        model: ResearchModel | None = None,
        retrieval: RetrievalService | None = None,
        repository: ContextRepository | None = None,
        options: ResearchOptions | None = None,
        trace_sink: TraceSink | None = None,
        prices: PriceTable | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.model = model or FixtureResearchModel()
        self._live_started = False
        self.retrieval = retrieval
        self.documents = DocumentStore(data_dir / "documents")
        self.reports = ReportRepository(data_dir / "memory")
        self.repository = repository or LocalContextRepository(self.documents, self.reports)
        self.options = options or ResearchOptions()
        self.trace_sink = trace_sink
        self.prices = prices
        self._owned_live_adapters: list[
            TavilyAdapter | CarbonIntensityAdapter | WikipediaAdapter
        ] = []
        if retrieval:
            for kind, adapter in retrieval.adapters.items():
                enabled = (kind == SourceType.WEB and self.options.live_web) or (
                    kind == SourceType.API and self.options.live_energy
                )
                if adapter.is_live and not enabled:
                    raise ValueError(
                        "Live retrieval requires an explicit matching research option."
                    )

    def report_path(self, state: ResearchState) -> Path:
        return self.data_dir / "reports" / state["run_id"] / "report.md"

    def retrieval_for(self, request: ResearchRequest) -> RetrievalService:
        if self.retrieval is not None:
            return self.retrieval
        if self.options.live_web or self.options.live_energy:
            adapters: dict[SourceType, RetrievalAdapter] = {}
            if self.options.live_web:
                key = load_settings().tavily_api_key
                if key is None:
                    raise ConfigurationError(
                        "Live web research requires EVIDENCEFORGE_TAVILY_API_KEY."
                    )
                web = TavilyAdapter(key)
                adapters[SourceType.WEB] = web
                self._owned_live_adapters.append(web)
                if self.options.production_policy_version:
                    fallback = WikipediaAdapter()
                    self._owned_live_adapters.append(fallback)
                    adapters[SourceType.WEB] = OrderedSearch((web, fallback))
            if self.options.live_energy:
                energy = CarbonIntensityAdapter()
                adapters[SourceType.API] = energy
                self._owned_live_adapters.append(energy)
            if request.document_ids:
                adapters[SourceType.DOCUMENT] = DocumentRetrievalAdapter(
                    self.documents, request.owner_scope, request.document_ids
                )
            return RetrievalService(self.data_dir, adapters)
        if request.document_ids:
            return RetrievalService(
                self.data_dir,
                {
                    SourceType.DOCUMENT: DocumentRetrievalAdapter(
                        self.documents, request.owner_scope, request.document_ids
                    )
                },
            )
        return RetrievalService(self.data_dir)

    def profile(self, retrieval: RetrievalService) -> str:
        return json.dumps(
            {
                "graph_version": 8,
                **(
                    {"model_id": self.model.model_id, "model_ledger_version": 1}
                    if isinstance(self.model, GeminiResearchModel)
                    else {}
                ),
                "model": type(self.model).__module__ + "." + type(self.model).__qualname__,
                "context": type(self.repository).__module__
                + "."
                + type(self.repository).__qualname__,
                "adapters": {
                    kind.value: type(adapter).__module__ + "." + type(adapter).__qualname__
                    for kind, adapter in retrieval.adapters.items()
                },
                **(
                    {
                        "fallback_providers": {
                            kind.value: [
                                type(p).__module__ + "." + type(p).__qualname__
                                for p in adapter.providers
                            ]
                            for kind, adapter in retrieval.adapters.items()
                            if isinstance(adapter, OrderedSearch)
                        }
                    }
                    if any(isinstance(a, OrderedSearch) for a in retrieval.adapters.values())
                    else {}
                ),
                "fixture_empty": {
                    kind.value: isinstance(adapter, FixtureRetrievalAdapter)
                    and isinstance(adapter.response, RetrievalBatch)
                    and not adapter.response.results
                    for kind, adapter in retrieval.adapters.items()
                },
                "retrieval_options": retrieval.options.model_dump(mode="json"),
                "research_options": {
                    **self.options.model_dump(
                        mode="json",
                        exclude={
                            "live_web",
                            "live_energy",
                            "quality_input_version",
                            "production_policy_version",
                        },
                    ),
                    **(
                        {"quality_input_version": 2}
                        if self.options.quality_input_version == 2
                        else {}
                    ),
                    **(
                        {"production_policy_version": 1}
                        if self.options.production_policy_version
                        else {}
                    ),
                    **({"live_web": True} if self.options.live_web else {}),
                    **({"live_energy": True} if self.options.live_energy else {}),
                },
            },
            sort_keys=True,
        )

    def restore_quality_profile(self, profile: str) -> None:
        version = json.loads(profile)["research_options"].get("quality_input_version", 1)
        if type(version) is not int or version not in (1, 2):
            raise CheckpointFailure("Unsupported research input contract version.")
        policy = json.loads(profile)["research_options"].get("production_policy_version", 0)
        if type(policy) is not int or policy not in (0, 1):
            raise CheckpointFailure("Unsupported production policy version.")
        self.options = self.options.model_copy(
            update={"quality_input_version": version, "production_policy_version": policy}
        )

    def cancel(self, thread_id: str, owner_scope: str = "local") -> None:
        """Request owner-scoped cooperative cancellation without taking the run lock."""
        checkpoint = CheckpointRepository(self.data_dir / "checkpoints", owner_scope)
        checkpoint.request_cancel(thread_id)

    async def run(
        self,
        request: ResearchRequest,
        budget: BudgetLimits | None = None,
        *,
        pause_after: str | None = None,
    ) -> ResearchState:
        request = require_research_request(request)
        state = initial_state(request, budget)
        if self.options.quality_input_version == 2:
            event = RunEvent(
                id=stable_id("working_evidence", state["run_id"]),
                kind="working_evidence_enabled",
                message="Repeated literal passages are grouped; source provenance is retained.",
            )
            state = apply_update(state, {"events": {event.id: record_data(event)}})
        if isinstance(self.model, GeminiResearchModel):
            if self._live_started:
                raise CheckpointFailure("Create a fresh model and service for each paid run.")
            self.model.bind_budget(BudgetLimits.model_validate(state["budget"]))
            self._live_started = True
            event = RunEvent(
                id=stable_id("model_configuration", state["run_id"]),
                kind="gemini_model",
                message=self.model.model_id,
            )
            state = apply_update(state, {"events": {event.id: record_data(event)}})
        try:
            retrieval = self.retrieval_for(request)
            if any(adapter.is_live for adapter in retrieval.adapters.values()):
                event = RunEvent(
                    id=stable_id("live_retrieval", state["run_id"]),
                    kind="live_retrieval",
                    message="Explicit live source acquisition is enabled.",
                )
                state = apply_update(state, {"events": {event.id: record_data(event)}})
            checkpoint = CheckpointRepository(self.data_dir / "checkpoints", request.owner_scope)
            checkpoint.register(state, self.profile(retrieval))
            return await self.execute(
                state, retrieval, checkpoint, resume=False, pause_after=pause_after
            )
        finally:
            await self.close_live_adapters()

    async def snapshot(self, thread_id: str, owner_scope: str = "local") -> ResearchState:
        """Read a checkpoint only after validating the owner registration."""
        checkpoint = CheckpointRepository(self.data_dir / "checkpoints", owner_scope)
        registration = checkpoint.load(thread_id)
        async with AsyncSqliteSaver.from_conn_string(str(checkpoint.path)) as saver:
            saved = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
        if saved is None:
            return validate_state(registration.initial_state)
        state = validate_state(
            {
                k: v
                for k, v in saved.checkpoint["channel_values"].items()
                if k in StateSnapshot.model_fields
            }
        )
        initial = registration.initial_state
        for key in ("owner_scope", "run_id", "thread_id", "request", "budget", "started_at"):
            if dict(state)[key] != initial[key]:
                raise CheckpointFailure("Checkpoint identity or request integrity failed.")
        return state

    async def edit_plan(
        self,
        thread_id: str,
        plan: PlanDraft,
        expected_version: int,
        owner_scope: str = "local",
    ) -> ResearchState:
        """Replace a pending plan, then interrupt again for review of the new version."""
        PlanDecision(approved=False, plan_version=expected_version)
        plan = PlanDraft.model_validate(plan)
        if len(plan.model_dump_json().encode("utf-8")) > 100_000:
            raise CheckpointFailure("Edited plan exceeded the size allowance.")
        checkpoint = CheckpointRepository(self.data_dir / "checkpoints", owner_scope)
        registration = checkpoint.load(thread_id)
        self.restore_quality_profile(registration.profile)
        initial = validate_state(registration.initial_state)
        try:
            retrieval = self.retrieval_for(ResearchRequest.model_validate(initial["request"]))
            if self.profile(retrieval) != registration.profile:
                raise CheckpointFailure("Edit configuration differs from the registered workflow.")
            artifacts, ledger = retrieval.components(initial)
            config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
            with tracing_context(enabled=False), checkpoint.exclusive(thread_id):
                state = await self.snapshot(thread_id, owner_scope)
                if (
                    state["run_status"] != "running"
                    or state["approval_status"] != "awaiting_approval"
                    or checkpoint.cancellation_requested(thread_id)
                ):
                    raise CheckpointFailure("Only a pending, uncancelled plan can be edited.")
                if state["plan_version"] != expected_version:
                    raise CheckpointFailure("Edit plan version is stale.")
                if state["query_records"] or state["calls"] or state["evidence_store"]:
                    raise CheckpointFailure("Plan editing is allowed only before query generation.")
                if (
                    len(plan.questions)
                    > BudgetLimits.model_validate(state["budget"]).max_subquestions
                ):
                    raise CheckpointFailure("Edited plan exceeds the subquestion allowance.")
                questions = [
                    ResearchQuestion(
                        id=stable_id(
                            "question",
                            owner_scope,
                            normalized(str(state["request"]["question"])),
                            normalized(q.question),
                        ),
                        question=q.question,
                        acceptance_criteria=q.acceptance_criteria,
                        importance=q.importance,
                    )
                    for q in plan.questions
                ]
                event = RunEvent(
                    id=stable_id("plan_edit", state["run_id"], expected_version + 1),
                    kind="plan_edited",
                    message="Edited plan requires renewed approval.",
                )
                updated = apply_update(
                    state,
                    {
                        "research_questions": [record_data(q) for q in questions],
                        "plan_version": expected_version + 1,
                        "approval_status": "awaiting_approval",
                        "events": {event.id: record_data(event)},
                    },
                )
                async with AsyncSqliteSaver.from_conn_string(str(checkpoint.path)) as saver:
                    graph = build_research_graph(
                        self.model,
                        self.repository,
                        SourceProcessor(retrieval.adapters, artifacts, ledger, retrieval.options),
                        EvidenceExtractor(
                            artifacts,
                            retrieval.options,
                            evict_lowest=bool(self.options.production_policy_version),
                        ),
                        artifacts,
                        self.options,
                        checkpointer=saver,
                    )
                    await graph.aupdate_state(config, dict(updated), as_node="prepare_approval")
                    # Re-enter only the approval node. No planning/query/retrieval work is replayed.
                    async for value in graph.astream(None, config=config, stream_mode="values"):
                        updated = validate_state(
                            {k: v for k, v in value.items() if k != "__interrupt__"}
                        )
                return updated
        finally:
            await self.close_live_adapters()

    async def resume(
        self,
        thread_id: str,
        owner_scope: str = "local",
        *,
        decision: PlanDecision | None = None,
    ) -> ResearchState:
        checkpoint = CheckpointRepository(self.data_dir / "checkpoints", owner_scope)
        registration = checkpoint.load(thread_id)
        self.restore_quality_profile(registration.profile)
        state = validate_state(registration.initial_state)
        try:
            retrieval = self.retrieval_for(ResearchRequest.model_validate(state["request"]))
            if self.profile(retrieval) != registration.profile:
                raise CheckpointFailure(
                    "Resume configuration differs from the registered workflow."
                )
            return await self.execute(state, retrieval, checkpoint, resume=True, decision=decision)
        finally:
            await self.close_live_adapters()

    async def close_live_adapters(self) -> None:
        adapters, self._owned_live_adapters = self._owned_live_adapters, []
        for adapter in adapters:
            await adapter.aclose()

    async def execute(
        self,
        initial: ResearchState,
        retrieval: RetrievalService,
        checkpoint: CheckpointRepository,
        *,
        resume: bool,
        decision: PlanDecision | None = None,
        pause_after: str | None = None,
    ) -> ResearchState:
        try:
            return await self._execute(
                initial,
                retrieval,
                checkpoint,
                resume=resume,
                decision=decision,
                pause_after=pause_after,
            )
        finally:
            await self.close_live_adapters()

    async def _execute(
        self,
        initial: ResearchState,
        retrieval: RetrievalService,
        checkpoint: CheckpointRepository,
        *,
        resume: bool,
        decision: PlanDecision | None = None,
        pause_after: str | None = None,
    ) -> ResearchState:
        artifacts, ledger = retrieval.components(initial)
        trace_settings = load_settings()
        node_trace = (
            NodeTrace(
                self.data_dir / "traces" / (initial["run_id"] + ".jsonl"),
                payloads=trace_settings.trace_payloads,
            )
            if trace_settings.tracing_enabled or self.options.production_policy_version
            else None
        )
        config: RunnableConfig = {
            "recursion_limit": self.options.recursion_limit,
            "configurable": {"thread_id": initial["thread_id"]},
        }
        trace_metrics = {"attempted": 0, "accepted_by_sink": 0, "failed": 0}

        def emit(phase: str, state: ResearchState) -> None:
            if self.trace_sink is None:
                return
            trace_metrics["attempted"] += 1
            try:
                self.trace_sink.emit(phase, public_progress(state))
            except Exception:
                trace_metrics["failed"] += 1
            else:
                trace_metrics["accepted_by_sink"] += 1

        with tracing_context(enabled=False):
            with checkpoint.exclusive(initial["thread_id"]):
                if isinstance(self.model, GeminiResearchModel):
                    try:
                        self.model.trace_payloads = trace_settings.trace_payloads
                        self.model.bind_run(
                            self.data_dir / "model_calls",
                            initial["owner_scope"],
                            initial["run_id"],
                            BudgetLimits.model_validate(initial["budget"]),
                            existing=resume,
                        )
                    except ModelUnavailable as exc:
                        raise CheckpointFailure(str(exc)) from None
                async with AsyncSqliteSaver.from_conn_string(str(checkpoint.path)) as saver:
                    graph = build_research_graph(
                        self.model,
                        self.repository,
                        SourceProcessor(
                            retrieval.adapters,
                            artifacts,
                            ledger,
                            retrieval.options,
                            cancellation_requested=lambda: checkpoint.cancellation_requested(
                                initial["thread_id"]
                            ),
                        ),
                        EvidenceExtractor(
                            artifacts,
                            retrieval.options,
                            evict_lowest=bool(self.options.production_policy_version),
                        ),
                        artifacts,
                        self.options,
                        checkpointer=saver,
                        pause_after=pause_after,
                        node_trace=node_trace,
                    )
                    last = initial
                    graph_input: ResearchState | Command[object] | None = (
                        None if resume else initial
                    )
                    if resume:
                        saved = await graph.aget_state(config)
                        if not saved.values:
                            raise CheckpointFailure(
                                "No workflow checkpoint is available for this thread."
                            )
                        last = validate_state(saved.values)
                        for key in (
                            "owner_scope",
                            "run_id",
                            "thread_id",
                            "request",
                            "budget",
                            "started_at",
                        ):
                            if dict(last)[key] != dict(initial)[key]:
                                raise CheckpointFailure(
                                    "Checkpoint identity or request integrity failed."
                                )
                        if decision is not None:
                            if last["approval_status"] != "awaiting_approval" or not saved.next:
                                raise CheckpointFailure(
                                    "This thread is not awaiting plan approval."
                                )
                            if decision.plan_version != last["plan_version"]:
                                raise CheckpointFailure("Approval plan version is stale.")
                            graph_input = Command(resume=decision.model_dump(mode="json"))
                        if not saved.next:
                            if last["run_status"] == "running":
                                raise CheckpointFailure(
                                    "Running checkpoint has no pending workflow steps."
                                )
                            self.deliver(last)
                            return last
                    try:
                        if checkpoint.cancellation_requested(initial["thread_id"]):
                            raise RunCancellation()
                        async for value in graph.astream(
                            graph_input, config=config, stream_mode="values"
                        ):
                            previous = public_progress(last)
                            last = validate_state(
                                {k: v for k, v in value.items() if k != "__interrupt__"}
                            )
                            emit(trace_phase(previous, public_progress(last)), last)
                            if last[
                                "run_status"
                            ] == "running" and checkpoint.cancellation_requested(
                                initial["thread_id"]
                            ):
                                raise RunCancellation()
                    except RunCancellation:
                        if last["run_status"] == "running":
                            last = self.reconcile_calls(last, ledger)
                            last = apply_update(
                                last,
                                {
                                    "run_status": "cancelled",
                                    "stop_reason": "cancelled",
                                    "finished_at": utc_now().isoformat(),
                                },
                            )
                            await graph.aupdate_state(config, dict(last), as_node="finalizer")
                            emit("cancelled", last)
                    except GraphRecursionError:
                        if last["run_status"] != "running":
                            raise
                        last = apply_update(
                            last, quality_error(last, "graph", "provider", last["quality_attempts"])
                        )
                        last = apply_update(last, {"stop_reason": "recursion_limit"})
                        last = apply_update(last, CitationChecker(artifacts)(last))
                        last = apply_update(last, finalize(last))
                        await graph.aupdate_state(config, dict(last), as_node="finalizer")
                    if last["run_status"] != "running":
                        emit("final", last)
                        self.deliver(last, trace_metrics)
                        if node_trace is not None:
                            atomic_write(
                                self.report_path(last).with_name("local_trace_coverage.json"),
                                json.dumps(
                                    {
                                        "nodes_written": node_trace.written,
                                        "write_failures": node_trace.failed,
                                        "omitted_at_size_cap": node_trace.omitted,
                                        "payloads_enabled": node_trace.payloads,
                                        "remote_export": False,
                                    },
                                    indent=2,
                                ),
                            )
                    return last

    def reconcile_calls(self, state: ResearchState, ledger: object) -> ResearchState:
        """Include durable in-flight reservations in a cancelled run's usage record."""
        from evidenceforge.storage.calls import CallLedger

        assert isinstance(ledger, CallLedger)
        calls: dict[str, object] = {}
        reservations: dict[str, object] = {}
        usage: dict[str, object] = {}
        artifacts: dict[str, object] = {}
        for receipt in ledger.records().values():
            if receipt.call.status == "pending":
                receipt = CallReceipt.model_validate(
                    {
                        **receipt.model_dump(),
                        "call": {
                            **receipt.call.model_dump(),
                            "revision": receipt.call.revision + 1,
                            "status": "ambiguous",
                            "finished_at": utc_now(),
                        },
                        "reservation": {**receipt.reservation.model_dump(), "status": "settled"},
                        "error_category": "internal",
                    }
                )
                ledger.finish(receipt)
            calls[receipt.call.id] = record_data(receipt.call)
            reservations[receipt.reservation.id] = record_data(receipt.reservation)
            if receipt.usage is not None:
                usage[receipt.usage.id] = record_data(receipt.usage)
            if receipt.response is not None:
                artifacts[receipt.response.id] = record_data(receipt.response)
        return apply_update(
            state,
            {
                "calls": calls,
                "reservations": reservations,
                "usage": usage,
                "raw_result_refs": artifacts,
            },
        )

    def deliver(self, state: ResearchState, trace_metrics: dict[str, int] | None = None) -> None:
        path = self.report_path(state)
        from evidenceforge.exports import report_export

        atomic_write(path, render_report(state))
        atomic_write(path.with_name("report.json"), report_export(state))
        atomic_write(path.with_name("state.json"), json.dumps(state, ensure_ascii=False, indent=2))
        if isinstance(self.model, GeminiResearchModel):
            atomic_write(
                path.with_name("model_usage.json"),
                json.dumps(
                    {
                        "provider": "gemini",
                        "model": self.model.model_id,
                        "attempts": self.model.observations,
                        "estimated_cost_usd": None,
                        "durable_resume_supported": True,
                        "unconfirmed_call_policy": "block_automatic_retry",
                    },
                    indent=2,
                ),
            )
        atomic_write(
            path.with_name("graph.json"),
            json.dumps(project(state).model_dump(mode="json"), ensure_ascii=False, indent=2),
        )
        atomic_write(
            path.with_name("audit.json"), json.dumps(audit(state), ensure_ascii=False, indent=2)
        )
        atomic_write(path.with_name("inspection.md"), render_inspection(state))
        atomic_write(
            path.with_name("usage.json"),
            json.dumps(usage_summary(state, self.prices), ensure_ascii=False, indent=2),
        )
        atomic_write(
            path.with_name("progress.json"),
            json.dumps(public_progress(state).as_dict(), ensure_ascii=False, indent=2),
        )
        if trace_metrics is not None or not path.with_name("trace_coverage.json").exists():
            atomic_write(
                path.with_name("trace_coverage.json"),
                json.dumps(
                    {
                        "custom_sink": self.trace_sink is not None,
                        "local_emissions": trace_metrics
                        or {"attempted": 0, "accepted_by_sink": 0, "failed": 0},
                        "remote_delivery_verified": False,
                        "raw_graph_tracing_disabled": True,
                    },
                    indent=2,
                ),
            )
        self.reports.save(state)
