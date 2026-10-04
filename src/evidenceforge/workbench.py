"""Local UI facade: bounded background work, checkpoint reconnect and scoped reads."""

import asyncio
import json
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from evidenceforge.config import load_settings
from evidenceforge.graph.state import ResearchState
from evidenceforge.guardrails import require_research_request
from evidenceforge.identity import new_id
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import PlanDraft
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch
from evidenceforge.retrieval.fixtures import (
    DisputeFixture,
    FixtureRetrievalAdapter,
    SecondPassFixture,
)
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.storage.checkpoints import CheckpointFailure, CheckpointRepository


class LocalWorkbench:
    """Single-machine demo. Scope names are storage boundaries, not authentication."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.reader = ResearchService(data_dir)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="evidenceforge")
        self.jobs: dict[tuple[str, str], Future[ResearchState]] = {}
        self.lock = Lock()

    def service(
        self,
        demo: str = "immediate",
        options: ResearchOptions | None = None,
        *,
        gemini: bool = False,
        model_id: str | None = None,
    ) -> ResearchService:
        retrieval = None
        if demo in {"second-pass", "empty", "dispute"}:
            adapter = (
                SecondPassFixture()
                if demo == "second-pass"
                else DisputeFixture()
                if demo == "dispute"
                else FixtureRetrievalAdapter(RetrievalBatch(results=()))
            )
            retrieval = RetrievalService(self.data_dir, {SourceType.WEB: adapter})
        model = None
        if gemini:
            settings = load_settings()
            if settings.model_api_key is None or (model_id or settings.model_id) is None:
                raise CheckpointFailure("Configure a Gemini model and API key first.")
            model = GeminiResearchModel(
                model_id or str(settings.model_id), settings.model_api_key, settings.budget
            )
        return ResearchService(
            self.data_dir,
            model=model,
            retrieval=retrieval,
            options=options or ResearchOptions(require_plan_approval=True),
        )

    def registered_service(self, owner: str, thread: str) -> ResearchService:
        profile = json.loads(
            CheckpointRepository(self.data_dir / "checkpoints", owner).load(thread).profile
        )
        gemini = str(profile["model"]).endswith(".GeminiResearchModel")
        if (
            profile.get("graph_version") != 8
            or (gemini and profile.get("model_ledger_version") != 1)
            or (not gemini and not str(profile["model"]).endswith(".FixtureResearchModel"))
        ):
            raise CheckpointFailure("This workflow has an incompatible checkpoint configuration.")
        adapters = profile["adapters"]
        demo = (
            "dispute"
            if any(n.endswith(".DisputeFixture") for n in adapters.values())
            else "second-pass"
            if any(n.endswith(".SecondPassFixture") for n in adapters.values())
            else "empty"
            if profile.get("fixture_empty", {}).get("web")
            else "immediate"
        )
        return self.service(
            demo,
            ResearchOptions.model_validate(profile["research_options"]),
            gemini=gemini,
            model_id=profile.get("model_id"),
        )

    def submit(self, owner: str, key: str, operation: object) -> str:
        from collections.abc import Callable
        from typing import cast

        with self.lock:
            if any(not job.done() for job in self.jobs.values()):
                raise CheckpointFailure("A local UI operation is active. Wait for it to finish.")
            existing = self.jobs.get((owner, key))
            if existing is not None and not existing.done():
                raise CheckpointFailure("This workflow is already active.")
            # Retain bounded completion notices; checkpoints are the durable authority.
            self.jobs = {k: v for k, v in list(self.jobs.items())[-49:]}
            self.jobs[(owner, key)] = self.executor.submit(
                cast(Callable[[], ResearchState], operation)
            )
        return key

    def start(
        self,
        request: ResearchRequest,
        demo: str = "second-pass",
        *,
        budget: BudgetLimits | None = None,
        gemini: bool = False,
    ) -> str:
        request = require_research_request(request)
        if demo not in {"immediate", "second-pass", "empty", "dispute"}:
            raise ValueError("Unknown fixture scenario.")
        if request.document_ids:
            demo = "immediate"
        service = self.service(demo, gemini=gemini)
        return self.submit(
            request.owner_scope,
            new_id("job"),
            lambda: asyncio.run(service.run(request, budget or BudgetLimits())),
        )

    def resume(self, owner: str, thread: str, decision: PlanDecision | None = None) -> str:
        service = self.registered_service(owner, thread)
        return self.submit(
            owner, thread, lambda: asyncio.run(service.resume(thread, owner, decision=decision))
        )

    def edit(self, owner: str, thread: str, plan: PlanDraft, version: int) -> str:
        service = self.registered_service(owner, thread)
        return self.submit(
            owner, thread, lambda: asyncio.run(service.edit_plan(thread, plan, version, owner))
        )

    def result(self, owner: str, key: str) -> ResearchState | None:
        with self.lock:
            future = self.jobs.get((owner, key))
        return future.result() if future is not None and future.done() else None

    def active(self, owner: str) -> bool:
        with self.lock:
            return any(o == owner and not job.done() for (o, _), job in self.jobs.items())

    def snapshot(self, owner: str, thread: str) -> ResearchState:
        return asyncio.run(self.reader.snapshot(thread, owner))

    def threads(self, owner: str) -> list[str]:
        return CheckpointRepository(self.data_dir / "checkpoints", owner).threads()

    def cancel(self, owner: str, thread: str) -> None:
        self.reader.cancel(thread, owner)

    def timeline(self, owner: str, thread: str) -> list[dict[str, str]]:
        from evidenceforge.services.observability import public_timeline

        return public_timeline(self.snapshot(owner, thread))

    def export(self, owner: str, thread: str) -> str:
        from evidenceforge.exports import report_export

        return report_export(self.snapshot(owner, thread))

    def paid_usage(self, owner: str, thread: str) -> dict[str, object] | None:
        from evidenceforge.storage.model_calls import ModelCallLedger, model_usage

        registration = CheckpointRepository(self.data_dir / "checkpoints", owner).load(thread)
        profile = json.loads(registration.profile)
        if profile.get("model_ledger_version") != 1:
            return None
        initial = registration.initial_state
        ledger = ModelCallLedger(
            self.data_dir / "model_calls",
            owner,
            str(initial["run_id"]),
            str(profile["model_id"]),
            BudgetLimits.model_validate(initial["budget"]),
            existing=True,
        )
        return model_usage(ledger.records())

    def close(self) -> None:
        self.executor.shutdown(wait=True)
