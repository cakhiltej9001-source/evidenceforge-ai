"""One bounded retrieval batch, durable receipts, retained snapshots and provenance."""

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import ValidationError

from evidenceforge.graph.reducers import RecordMap
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.nodes.queries import query_key
from evidenceforge.planning import PlanningContractError, parse_response
from evidenceforge.retrieval.contracts import (
    ArtifactFailure,
    CallReceipt,
    ErrorCategory,
    RetrievalAdapter,
    RetrievalBatch,
    RetrievalFailure,
    RetrievalOptions,
    RetrievedDocument,
)
from evidenceforge.retrieval.fallback import OrderedSearch
from evidenceforge.schemas import (
    ArtifactReference,
    BudgetReservation,
    CallRecord,
    RejectedEvidence,
    RunEvent,
    SearchQuery,
    SourceAcquisition,
    SourceRecord,
    SourceType,
    ToolError,
    UsageRecord,
    utc_now,
)
from evidenceforge.services.cancellation import RunCancellation
from evidenceforge.services.retry import retry_delay
from evidenceforge.storage.artifacts import ArtifactStore
from evidenceforge.storage.calls import CallLedger


@dataclass
class Outcome:
    query: SearchQuery
    receipt: CallReceipt | None = None
    batch: RetrievalBatch | None = None
    category: ErrorCategory | None = None
    prior_receipts: tuple[CallReceipt, ...] = ()
    attempts: int = 1
    retry_after_seconds: float | None = None


def retrieval_error(
    state: ResearchState, query: SearchQuery, category: ErrorCategory, attempt: int = 1
) -> ToolError:
    messages = {
        "authentication": "Search authentication failed; no retry was made.",
        "rate_limit": "Search rate limit reached; bounded retry policy stopped.",
        "timeout": "Search timed out; usage may be unknown.",
        "schema": "Search response failed validation.",
        "provider": "Search adapter/source channel is unavailable.",
        "budget": "Search stopped at a configured allowance.",
        "internal": "Search outcome/artifact is uncertain; no retry was made.",
    }
    return ToolError(
        id=stable_id("retrieval_error", state["run_id"], query.id, category),
        provider="source_processor",
        query_id=query.id,
        category=category,
        retryable=False,
        attempt=attempt,
        message=messages[category],
    )


class SourceProcessor:
    def __init__(
        self,
        adapters: dict[SourceType, RetrievalAdapter],
        artifacts: ArtifactStore,
        ledger: CallLedger,
        options: RetrievalOptions,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> None:
        self.cancellation_requested = cancellation_requested or (lambda: False)
        self.adapters, self.artifacts, self.ledger, self.options = (
            adapters,
            artifacts,
            ledger,
            options,
        )

    def validate_batch(
        self, snapshot: StateSnapshot, query: SearchQuery, batch: RetrievalBatch
    ) -> None:
        for result in batch.results:
            if result.source_type != query.source_type:
                raise RetrievalFailure("schema")
            if isinstance(result, RetrievedDocument) and (
                result.owner_scope != snapshot.owner_scope
                or result.document_id not in snapshot.request.document_ids
                or not any(
                    c.kind == "document" and c.target_id == result.document_id
                    for c in snapshot.context_refs
                )
            ):
                raise RetrievalFailure("schema")

    async def _retrieve(self, state: ResearchState, query: SearchQuery) -> Outcome:
        adapter = self.adapters.get(query.source_type)
        if adapter is None:
            return Outcome(query, category="provider")
        providers = adapter.providers if isinstance(adapter, OrderedSearch) else (adapter,)
        receipts: list[CallReceipt] = []
        maximum = StateSnapshot.model_validate(state).budget.max_attempts_per_call
        for provider_index, provider in enumerate(providers):
            for attempt in range(1, maximum + 1):
                if self.cancellation_requested():
                    raise RunCancellation()
                outcome = await self._attempt(state, query, attempt, provider, provider_index)
                if outcome.receipt is not None:
                    receipts.append(outcome.receipt)
                outcome.prior_receipts = tuple(receipts[:-1] if outcome.receipt else receipts)
                outcome.attempts = len(receipts) or attempt
                if outcome.category in {"internal", "budget"}:
                    return outcome
                if outcome.category is None:
                    if outcome.batch and any(r.content.strip() for r in outcome.batch.results):
                        return outcome
                    break
                delay = retry_delay(
                    outcome.category, attempt, query.id, provider, outcome.retry_after_seconds
                )
                remaining = (
                    StateSnapshot.model_validate(state).budget.max_elapsed_seconds
                    - (utc_now() - StateSnapshot.model_validate(state).started_at).total_seconds()
                )
                if delay is None or attempt >= maximum or remaining <= delay:
                    break
                await asyncio.sleep(delay)
        return outcome

    async def _attempt(
        self,
        state: ResearchState,
        query: SearchQuery,
        attempt: int,
        provider: RetrievalAdapter | None = None,
        provider_index: int = 0,
    ) -> Outcome:
        if self.cancellation_requested():
            raise RunCancellation()
        snapshot = StateSnapshot.model_validate(state)
        adapter = provider or self.adapters.get(query.source_type)
        if adapter is None:
            return Outcome(query, category="provider")
        if (
            query_key(query.text, query.source_type, snapshot.owner_scope)
            in snapshot.attempted_query_keys
        ):
            return Outcome(query)
        elapsed = max(0.0, (utc_now() - snapshot.started_at).total_seconds())
        remaining = snapshot.budget.max_elapsed_seconds - elapsed
        identifier = (
            stable_id("call", snapshot.run_id, query.id, attempt)
            if provider_index == 0
            else stable_id("call", snapshot.run_id, query.id, "fallback", provider_index, attempt)
        )
        request_hash = hashlib.sha256(
            json.dumps(
                {
                    "query": query.model_dump(mode="json"),
                    "provider": adapter.name,
                    "options": self.options.model_dump(mode="json"),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        receipt = CallReceipt(
            owner_scope=snapshot.owner_scope,
            run_id=snapshot.run_id,
            call=CallRecord(
                id=identifier,
                request_hash=request_hash,
                provider=adapter.name,
                kind="search",
                status="pending",
                started_at=utc_now(),
            ),
            reservation=BudgetReservation(
                id=stable_id("reservation", identifier),
                call_id=identifier,
                searches=1,
            ),
        )
        known = self.ledger.records()
        if identifier not in known and (
            remaining <= 0 or (adapter.is_live and snapshot.budget.max_cost_usd is not None)
        ):
            # Cached outcomes make no new paid operation, even after a deadline.
            # New live calls with a dollar ceiling need a verified pricing policy.
            return Outcome(query, category="budget")
        extra = sum(
            r.searches
            for r in snapshot.reservations.values()
            if r.call_id not in known and r.status != "released"
        )
        try:
            receipt, created = self.ledger.reserve(receipt, snapshot.budget, extra)
        except RetrievalFailure as exc:
            return Outcome(query, category=exc.category)
        if not created:
            if receipt.call.status == "completed" and receipt.response is not None:
                try:
                    cached_batch = RetrievalBatch.model_validate_json(
                        self.artifacts.read(receipt.response)
                    )
                    self.validate_batch(snapshot, query, cached_batch)
                    return Outcome(query, receipt, cached_batch)
                except (ArtifactFailure, ValidationError, RetrievalFailure):
                    return Outcome(query, receipt, category="internal")
            if receipt.call.status == "pending":
                receipt = CallReceipt.model_validate(
                    {
                        **receipt.model_dump(),
                        "call": {
                            **receipt.call.model_dump(),
                            "status": "ambiguous",
                            "revision": receipt.call.revision + 1,
                            "finished_at": utc_now(),
                        },
                        "reservation": {**receipt.reservation.model_dump(), "status": "settled"},
                        "error_category": "internal",
                    }
                )
                self.ledger.finish(receipt)
            return Outcome(query, receipt, category=receipt.error_category or "internal")
        if self.cancellation_requested():
            raise RunCancellation()
        started = time.monotonic()
        batch: RetrievalBatch | None = None
        reference: ArtifactReference | None = None
        category: ErrorCategory | None = None
        retry_after_seconds: float | None = None
        try:
            task = asyncio.create_task(adapter.search(query, self.options))
            try:
                deadline = time.monotonic() + min(self.options.timeout_seconds, remaining)
                while True:
                    if self.cancellation_requested():
                        raise RunCancellation()
                    available = deadline - time.monotonic()
                    if available <= 0:
                        raise TimeoutError()
                    done, _ = await asyncio.wait({task}, timeout=min(0.1, available))
                    if done:
                        response = task.result()
                        break
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            batch = parse_response(response, RetrievalBatch, self.options.max_response_bytes)
            if len(batch.results) > self.options.max_results:
                raise RetrievalFailure("schema")
            self.validate_batch(snapshot, query, batch)
            reference = self.artifacts.put(batch.model_dump_json(), "retrieval_response_v1")
        except (ValidationError, PlanningContractError):
            category = "schema"
        except RetrievalFailure as exc:
            category = exc.category
            retry_after_seconds = exc.retry_after_seconds
        except TimeoutError:
            category = "timeout"
        except ArtifactFailure:
            category = "internal"
        except asyncio.CancelledError:
            # Pending durable receipt intentionally remains uncertain after cancellation.
            raise
        finish = utc_now()
        receipt = CallReceipt.model_validate(
            {
                **receipt.model_dump(),
                "call": {
                    **receipt.call.model_dump(),
                    "revision": 2,
                    "status": "completed" if reference is not None else "failed",
                    "finished_at": finish,
                    "response_artifact_id": reference.id if reference else None,
                },
                "reservation": {**receipt.reservation.model_dump(), "status": "settled"},
                "response": reference,
                "usage": UsageRecord(
                    id=stable_id("usage", identifier),
                    call_id=identifier,
                    provider=adapter.name,
                    latency_ms=max(0.0, (time.monotonic() - started) * 1000),
                    search_credits=batch.search_credits if batch else None,
                ),
                "error_category": category,
            }
        )
        self.ledger.finish(receipt)
        return Outcome(
            query,
            receipt,
            batch if reference else None,
            category,
            retry_after_seconds=retry_after_seconds,
        )

    async def __call__(self, state: ResearchState) -> Update:
        if self.cancellation_requested():
            raise RunCancellation()
        snapshot = StateSnapshot.model_validate(state)
        if snapshot.run_status != "running" or snapshot.planning_status != "ready":
            return {}
        if not snapshot.search_queries:
            return {}
        if snapshot.iteration_count >= snapshot.budget.max_research_passes:
            return {}
        if any(q.research_pass != snapshot.iteration_count + 1 for q in snapshot.search_queries):
            raise ValueError("retrieval batch must address the next completed pass")
        semaphore = asyncio.Semaphore(snapshot.budget.max_concurrency)

        async def worker(query: SearchQuery) -> Outcome:
            async with semaphore:
                return await self._retrieve(state, query)

        tasks = [asyncio.create_task(worker(query)) for query in snapshot.search_queries]
        try:
            outcomes = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        update: Update = {}
        calls: RecordMap = {}
        reservations: RecordMap = {}
        usage: RecordMap = {}
        artifacts: RecordMap = {}
        sources: RecordMap = {}
        acquisitions: RecordMap = {}
        errors: RecordMap = {}
        rejected: RecordMap = {}
        attempted: list[str] = []
        for outcome in outcomes:
            query, receipt = outcome.query, outcome.receipt
            for prior in outcome.prior_receipts:
                calls[prior.call.id] = record_data(prior.call)
                reservations[prior.reservation.id] = record_data(prior.reservation)
                if prior.usage is not None:
                    usage[prior.usage.id] = record_data(prior.usage)
                if prior.response is not None:
                    artifacts[prior.response.id] = record_data(prior.response)
            if receipt is not None:
                calls[receipt.call.id] = record_data(receipt.call)
                reservations[receipt.reservation.id] = record_data(receipt.reservation)
                if receipt.usage is not None:
                    usage[receipt.usage.id] = record_data(receipt.usage)
                if receipt.response is not None:
                    artifacts[receipt.response.id] = record_data(receipt.response)
                attempted.append(query_key(query.text, query.source_type, snapshot.owner_scope))
            if outcome.category is not None:
                error = retrieval_error(state, query, outcome.category, outcome.attempts)
                errors[error.id] = state["tool_errors"].get(error.id) or record_data(error)
            batch = outcome.batch
            if batch is None:
                continue
            for index, result in enumerate(batch.results):
                candidate = stable_id("candidate", snapshot.run_id, query.id, index)
                reason = None
                if not result.content.strip():
                    reason = "unavailable_content"
                elif len(result.content.encode("utf-8")) > self.options.max_source_bytes:
                    reason = "content_limit"
                if reason is not None:
                    rejection = RejectedEvidence(
                        id=stable_id("rejection", candidate, reason),
                        candidate_id=candidate,
                        reason=reason,
                        rationale="Source content was empty or exceeded its configured bound.",
                    )
                    rejected[rejection.id] = record_data(rejection)
                    continue
                try:
                    reference = self.artifacts.put(
                        result.content,
                        f"{result.source_type.value}_{result.content_scope}_v1",
                    )
                except ArtifactFailure:
                    rejection = RejectedEvidence(
                        id=stable_id("rejection", candidate, "snapshot_limit"),
                        candidate_id=candidate,
                        reason="snapshot_limit",
                        rationale="Source snapshot could not be retained.",
                    )
                    rejected[rejection.id] = record_data(rejection)
                    continue
                artifacts[reference.id] = record_data(reference)
                private = isinstance(result, RetrievedDocument)
                location = (
                    result.chunk_id if isinstance(result, RetrievedDocument) else str(result.url)
                )
                source_id = stable_id(
                    "source",
                    snapshot.owner_scope,
                    location,
                    reference.content_hash,
                    result.content_scope,
                )
                source = SourceRecord(
                    id=source_id,
                    title=result.title,
                    source_type=result.source_type,
                    provider=receipt.call.provider if receipt else "fixture",
                    content_hash=reference.content_hash,
                    url=result.url,
                    owner_scope=result.owner_scope if private else None,
                    document_id=result.document_id
                    if isinstance(result, RetrievedDocument)
                    else None,
                    document_hash=result.document_hash
                    if isinstance(result, RetrievedDocument)
                    else None,
                    chunk_id=result.chunk_id if isinstance(result, RetrievedDocument) else None,
                    publisher=None if isinstance(result, RetrievedDocument) else result.publisher,
                    publication_date=None
                    if isinstance(result, RetrievedDocument)
                    else result.publication_date,
                    primary_evidence=None
                    if isinstance(result, RetrievedDocument)
                    else result.primary_evidence,
                    methodology_transparent=None
                    if isinstance(result, RetrievedDocument)
                    else result.methodology_transparent,
                    metadata_rationale=None
                    if isinstance(result, RetrievedDocument)
                    else result.metadata_rationale,
                    source_family=stable_id("source_family", result.document_id)
                    if isinstance(result, RetrievedDocument)
                    else result.source_family or stable_id("source_family", result.url.host),
                    access_status="available"
                    if result.content_scope == "full_text"
                    else "excerpt_only",
                )
                sources[source.id] = (
                    state["source_records"].get(source.id)
                    or sources.get(source.id)
                    or record_data(source)
                )
                acquisition = SourceAcquisition(
                    id=stable_id("acquisition", snapshot.run_id, query.id, source.id, reference.id),
                    source_id=source.id,
                    query_id=query.id,
                    snapshot_id=reference.id,
                    retrieved_at=batch.retrieved_at,
                    page=result.page if isinstance(result, RetrievedDocument) else None,
                    paragraph=result.paragraph if isinstance(result, RetrievedDocument) else None,
                    section=result.section if isinstance(result, RetrievedDocument) else None,
                    document_start_offset=result.document_start_offset
                    if isinstance(result, RetrievedDocument)
                    else None,
                    document_end_offset=result.document_end_offset
                    if isinstance(result, RetrievedDocument)
                    else None,
                    content_scope=result.content_scope,
                )
                acquisitions[acquisition.id] = record_data(acquisition)
        event = RunEvent(
            id=stable_id("retrieval_pass", snapshot.run_id, snapshot.iteration_count + 1),
            kind="retrieval_batch_completed",
            message=f"Completed one retrieval batch: {len(sources)} sources, {len(errors)} errors.",
        )
        update.update(
            {
                "calls": calls,
                "reservations": reservations,
                "usage": usage,
                "raw_result_refs": artifacts,
                "source_records": sources,
                "source_acquisitions": acquisitions,
                "tool_errors": errors,
                "rejected_evidence": rejected,
                "attempted_query_keys": attempted,
                "search_queries": [],
                "iteration_count": snapshot.iteration_count + 1,
                "events": {event.id: state["events"].get(event.id) or record_data(event)},
            }
        )
        return checked_patch(state, update)
