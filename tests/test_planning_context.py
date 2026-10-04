"""Scoped context metadata and optional repository failure checks."""

import asyncio
import json

import pytest

from evidenceforge.models.fixtures import FixturePlanningModel
from evidenceforge.planning import ContextUnavailable, PlanningOptions
from evidenceforge.schemas import ContextReference, ResearchRequest
from evidenceforge.services.planning import PlanningService
from evidenceforge.storage.context import InMemoryContextRepository

REQUEST = ResearchRequest(question="What is the measured solar output?", document_ids=("doc_a",))


def reference(identifier="context_a", owner="local", kind="document", target="doc_a"):
    return ContextReference(id=identifier, owner_scope=owner, kind=kind, target_id=target)


def run(repository, options=None, request=REQUEST):
    model = FixturePlanningModel()
    state = asyncio.run(PlanningService(model, repository, options).plan(request))
    return state, model


def test_repository_filters_owner_requested_documents_and_prior_reports():
    repo = InMemoryContextRepository(
        (
            reference(),
            reference("private_context", owner="different_owner", target="private_document"),
            reference("unrequested_context", target="unrequested_document"),
            reference("prior_context", kind="prior_report", target="old_report"),
        )
    )
    state, model = run(repo)
    assert {r["target_id"] for r in state["context_refs"]} == {"doc_a", "old_report"}
    assert model.query_calls == 1
    assert {q["source_type"] for q in state["search_queries"]} == {"web", "document"}
    assert state["evidence_store"] == {}
    assert "private_document" not in json.dumps(state)
    without_prior, _ = run(repo, PlanningOptions(include_prior_reports=False))
    assert [r["target_id"] for r in without_prior["context_refs"]] == ["doc_a"]


def test_prior_report_alone_is_context_and_does_not_enable_document_search():
    repo = InMemoryContextRepository(
        (reference("prior", kind="prior_report", target="old_report"),)
    )
    state, _ = run(repo, request=ResearchRequest(question=REQUEST.question))
    assert len(state["context_refs"]) == 1
    assert {q["source_type"] for q in state["search_queries"]} == {"web"}
    assert not state["source_records"] and not state["evidence_store"]


def test_missing_requested_document_is_disclosed_and_web_planning_continues():
    state, model = run(InMemoryContextRepository())
    assert state["planning_status"] == "ready"
    statuses = {r["role"]: r["status"] for r in state["initialization_results"].values()}
    assert statuses == {"planner": "ready", "context_manager": "unavailable"}
    assert model.query_calls == 1
    assert {q["source_type"] for q in state["search_queries"]} == {"web"}
    assert any(
        "1 requested document references unavailable" in e["message"]
        for e in state["events"].values()
    )


@pytest.mark.parametrize("kind", ["timeout", "unavailable"])
def test_optional_repository_failure_keeps_web_planning_and_sanitizes_errors(kind):
    class Repository:
        async def select(self, **kwargs):
            if kind == "unavailable":
                raise ContextUnavailable("private-path-and-secret")
            await asyncio.Event().wait()

    state, model = run(Repository(), PlanningOptions(node_timeout_seconds=0.02))
    assert state["planning_status"] == "ready" and state["run_status"] == "running"
    assert state["context_refs"] == []
    assert model.query_calls == 1
    assert {e["category"] for e in state["tool_errors"].values()} == {
        "timeout" if kind == "timeout" else "provider"
    }
    assert "private-path-and-secret" not in json.dumps(state)


@pytest.mark.parametrize(
    "references,options",
    [
        ([reference(owner="different_owner", target="private_document")], PlanningOptions()),
        ([reference(target="unrequested_document")], PlanningOptions()),
        (
            [reference(kind="prior_report", target="old_report")],
            PlanningOptions(include_prior_reports=False),
        ),
        ([reference(), reference()], PlanningOptions()),
        ([reference(), reference("different_id")], PlanningOptions()),
        (
            [reference(), reference("prior", kind="prior_report", target="report_a")],
            PlanningOptions(max_context_refs=1),
        ),
    ],
)
def test_malformed_or_cross_scope_repository_is_fatal_before_queries(references, options):
    class Repository:
        async def select(self, **kwargs):
            return {"references": [r.model_dump(mode="json") for r in references]}

    state, model = run(Repository(), options)
    assert state["planning_status"] == state["run_status"] == "failed"
    assert model.query_calls == 0
    assert state["context_refs"] == state["search_queries"] == []
    assert {e["category"] for e in state["tool_errors"].values()} == {"schema"}
    assert "private_document" not in json.dumps(state)
    assert "unrequested_document" not in json.dumps(state)


def test_no_enabled_source_after_optional_context_loss_is_explicit_failure():
    state, model = run(
        InMemoryContextRepository(),
        PlanningOptions(available_source_types=("document",)),
    )
    assert state["planning_status"] == "failed"
    assert model.query_calls == 0
    assert {e["category"] for e in state["tool_errors"].values()} == {"provider"}


def test_context_cap_is_deterministic_and_documents_are_selected_first():
    repo = InMemoryContextRepository(
        (
            reference("prior_b", kind="prior_report", target="report_b"),
            reference(),
            reference("prior_a", kind="prior_report", target="report_a"),
        )
    )
    first, _ = run(repo, PlanningOptions(max_context_refs=2))
    second, _ = run(repo, PlanningOptions(max_context_refs=2))
    assert first["context_refs"] == second["context_refs"]
    assert [r["target_id"] for r in first["context_refs"]] == ["doc_a", "report_a"]
