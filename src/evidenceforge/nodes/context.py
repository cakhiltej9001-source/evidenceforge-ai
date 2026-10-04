"""Select only permitted context metadata; reject a repository that crosses scope."""

import asyncio

from pydantic import ValidationError

from evidenceforge.graph.state import ResearchState, StateSnapshot, validate_state
from evidenceforge.nodes.common import (
    Update,
    checked_patch,
    event_patch,
    failure_patch,
    initialization_patch,
    record_data,
)
from evidenceforge.planning import (
    ContextBatch,
    ContextUnavailable,
    PlanningContractError,
    PlanningOptions,
    parse_response,
)
from evidenceforge.storage.context import ContextRepository


class ContextManager:
    def __init__(self, repository: ContextRepository, options: PlanningOptions) -> None:
        self.repository = repository
        self.options = options

    async def __call__(self, state: ResearchState) -> Update:
        state = validate_state(state)
        request = StateSnapshot.model_validate(state).request
        try:
            response = await asyncio.wait_for(
                self.repository.select(
                    owner_scope=request.owner_scope,
                    document_ids=request.document_ids,
                    include_prior_reports=self.options.include_prior_reports,
                    limit=self.options.max_context_refs,
                ),
                timeout=self.options.node_timeout_seconds,
            )
            batch = parse_response(response, ContextBatch, self.options.max_response_bytes)
            if len(batch.references) > self.options.max_context_refs:
                raise PlanningContractError("context limit exceeded")
            if len({reference.id for reference in batch.references}) != len(batch.references):
                raise PlanningContractError("duplicate context reference")
            targets = [(reference.kind, reference.target_id) for reference in batch.references]
            if len(targets) != len(set(targets)):
                raise PlanningContractError("duplicate context target")
            for reference in batch.references:
                if reference.owner_scope != request.owner_scope:
                    raise PlanningContractError("repository crossed owner scope")
                if reference.kind == "document" and reference.target_id not in request.document_ids:
                    raise PlanningContractError("repository returned an unrequested document")
                if reference.kind == "prior_report" and not self.options.include_prior_reports:
                    raise PlanningContractError("prior reports are disabled")
            available = {
                reference.target_id
                for reference in batch.references
                if reference.kind == "document"
            }
            missing = len(set(request.document_ids) - available)
            status = "unavailable" if missing else "ready"
            return checked_patch(
                state,
                {
                    "context_refs": [record_data(reference) for reference in batch.references],
                    **initialization_patch(state, "context_manager", status),
                    **event_patch(
                        state,
                        "context_manager",
                        "context_selected",
                        f"Selected {len(batch.references)} scoped context references; "
                        f"{missing} requested document references unavailable.",
                    ),
                },
            )
        except (ValidationError, PlanningContractError):
            return failure_patch(state, "context_manager", "schema")
        except TimeoutError:
            return failure_patch(state, "context_manager", "timeout", optional=True)
        except ContextUnavailable:
            return failure_patch(state, "context_manager", "provider", optional=True)
