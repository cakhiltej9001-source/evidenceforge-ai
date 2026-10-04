"""Executable graph tests with no model credentials or network access."""

import asyncio
import json
import sys
from copy import deepcopy

import pytest
from pydantic import ValidationError

from evidenceforge.config import ConfigurationError
from evidenceforge.graph.builder import build_planning_graph
from evidenceforge.graph.state import apply_update, initial_state, validate_state
from evidenceforge.models.fixtures import FixturePlanningModel
from evidenceforge.nodes.manager import manager
from evidenceforge.planning import ModelUnavailable, PlanningContractError, PlanningOptions
from evidenceforge.planning_demo import main
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.services.planning import PlanningService
from evidenceforge.storage.context import InMemoryContextRepository

REQUEST = ResearchRequest(question="Compare solar and wind electricity generation.")


def run_plan(model=None, repository=None, options=None, budget=None, request=REQUEST):
    return asyncio.run(PlanningService(model, repository, options).plan(request, budget))


def draft(question="What is the measured output?"):
    return {"question": question, "acceptance_criteria": ["Comparable primary measurements"]}


def test_parallel_branches_and_all_predecessor_join():
    async def scenario():
        plan_started, context_started = asyncio.Event(), asyncio.Event()
        finished = set()

        class Model(FixturePlanningModel):
            async def plan(self, request, *, max_questions):
                plan_started.set()
                await context_started.wait()
                output = await super().plan(request, max_questions=max_questions)
                finished.add("planner")
                return output

            async def generate_queries(self, request):
                assert finished == {"planner", "context"}
                assert request.context_refs[0].target_id == "document_a"
                assert request.questions
                return await super().generate_queries(request)

        class Repository(InMemoryContextRepository):
            async def select(self, **kwargs):
                context_started.set()
                await plan_started.wait()
                output = await super().select(**kwargs)
                finished.add("context")
                return output

        from evidenceforge.schemas import ContextReference

        reference = ContextReference(
            id="context_a", owner_scope="local", kind="document", target_id="document_a"
        )
        model = Model()
        service = PlanningService(
            model, Repository((reference,)), PlanningOptions(node_timeout_seconds=1.0)
        )
        state = await service.plan(
            ResearchRequest(question=REQUEST.question, document_ids=("document_a",))
        )
        assert state["planning_status"] == "ready"
        assert model.plan_calls == model.query_calls == 1
        assert len(state["initialization_results"]) == 2
        assert {q["source_type"] for q in state["search_queries"]} == {"web", "document"}
        assert [e["kind"] for e in state["events"].values()].count("queries_generated") == 1

    asyncio.run(scenario())


def test_planning_is_fresh_serializable_and_not_completed_research():
    first, second = run_plan(), run_plan()
    assert first["run_id"] != second["run_id"]
    assert first["thread_id"] != second["thread_id"]
    assert first["planning_status"] == "ready"
    assert first["run_status"] == "running"
    assert first["finished_at"] is None
    assert first["iteration_count"] == first["revision_count"] == 0
    assert first["plan_version"] == 1
    assert first["research_questions"] == second["research_questions"]
    assert first["search_queries"] == second["search_queries"]
    assert all(q["research_pass"] == 1 for q in first["search_queries"])
    for channel in (
        "attempted_query_keys",
        "source_records",
        "source_acquisitions",
        "raw_result_refs",
        "evidence_store",
        "reservations",
        "calls",
        "usage",
        "report_claims",
    ):
        assert not first[channel]
    assert first["draft_report"] is first["final_report"] is None
    assert validate_state(json.loads(json.dumps(first))) == first


def test_ids_survive_plan_order_and_normalized_input_but_are_owner_scoped():
    plan = {"questions": [draft("What is solar output?"), draft("What is wind output?")]}
    reordered = deepcopy(plan)
    reordered["questions"].reverse()
    first = run_plan(FixturePlanningModel(plan_output=plan))
    second = run_plan(
        FixturePlanningModel(plan_output=reordered),
        request=ResearchRequest(question="  COMPARE solar and WIND electricity generation.  "),
    )
    assert {q["id"] for q in first["research_questions"]} == {
        q["id"] for q in second["research_questions"]
    }
    other = run_plan(
        FixturePlanningModel(plan_output=plan),
        request=ResearchRequest(question=REQUEST.question, owner_scope="another_owner"),
    )
    assert not {q["id"] for q in first["research_questions"]} & {
        q["id"] for q in other["research_questions"]
    }


@pytest.mark.parametrize(
    "payload",
    [
        "sensitive-provider-value invalid JSON",
        {"questions": []},
        {"questions": [{"question": "Sensitive missing criteria"}]},
        {"questions": [draft(), draft("  WHAT is the measured output?  ")]},
        {"questions": [draft("What is output? What is cost?")]},
        {"questions": [draft("Output\nCost")]},
        {"questions": [{**draft(), "id": "sensitive_model_assigned_id"}]},
        {"questions": [{**draft(), "importance": 0.0}]},
        {"questions": [draft(f"What is item {i}?") for i in range(9)]},
        {"questions": [draft()], "secret": "sensitive-provider-value"},
    ],
)
def test_bad_plan_fails_without_query_call_or_raw_diagnostics(payload):
    model = FixturePlanningModel(plan_output=payload)
    state = run_plan(model)
    assert state["planning_status"] == state["run_status"] == "failed"
    assert state["stop_reason"] == "fatal_error"
    assert state["finished_at"]
    assert state["research_questions"] == state["search_queries"] == []
    assert model.plan_calls == 1 and model.query_calls == 0
    assert {e["category"] for e in state["tool_errors"].values()} == {"schema"}
    assert "sensitive" not in json.dumps(state).casefold()


@pytest.mark.parametrize("kind", ["unavailable", "timeout"])
def test_required_planner_adapter_failure_is_typed_and_sanitized(kind):
    class Model(FixturePlanningModel):
        async def plan(self, request, *, max_questions):
            if kind == "unavailable":
                raise ModelUnavailable("secret-provider-detail")
            await asyncio.Event().wait()

    state = run_plan(Model(), options=PlanningOptions(node_timeout_seconds=0.02))
    assert state["planning_status"] == "failed"
    assert not state["search_queries"]
    categories = {e["category"] for e in state["tool_errors"].values()}
    assert ("provider" if kind == "unavailable" else "timeout") in categories
    assert "secret-provider-detail" not in json.dumps(state)


def test_oversized_response_and_invalid_utf8_are_rejected():
    state = run_plan(
        FixturePlanningModel(plan_output={"questions": [draft("X" * 900)]}),
        options=PlanningOptions(max_response_bytes=300),
    )
    assert state["planning_status"] == "failed"
    state = run_plan(FixturePlanningModel(plan_output='{"questions": "' + chr(0xD800) + '"}'))
    assert state["planning_status"] == "failed"


def test_programming_errors_are_not_disguised_as_partial_success():
    class BrokenModel(FixturePlanningModel):
        async def plan(self, request, *, max_questions):
            raise RuntimeError("intentional programming bug")

    with pytest.raises(RuntimeError, match="intentional programming bug"):
        run_plan(BrokenModel())


def test_small_budgets_and_serial_execution_still_work():
    state = run_plan(
        budget=BudgetLimits(
            max_subquestions=1, max_queries_per_pass=1, max_searches=1, max_concurrency=1
        )
    )
    assert state["planning_status"] == "ready"
    assert len(state["research_questions"]) == len(state["search_queries"]) == 1


def test_manager_rejects_restarting_existing_run():
    state = run_plan()
    with pytest.raises(PlanningContractError, match="fresh run"):
        manager(state)


def test_initialization_snapshot_rejects_false_readiness():
    fresh = initial_state(REQUEST)
    with pytest.raises(ValidationError, match="both initialization"):
        apply_update(fresh, {"planning_status": "ready"})
    with pytest.raises(ValidationError, match="failed run"):
        apply_update(fresh, {"planning_status": "failed"})


def test_live_model_is_rejected_before_calls():
    class LiveModel(FixturePlanningModel):
        is_fixture = False

    model = LiveModel()
    with pytest.raises(ConfigurationError, match="live planning adapter"):
        build_planning_graph(model, InMemoryContextRepository())
    assert model.plan_calls == model.query_calls == 0


def test_cli_explicit_offline_output(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evidenceforge-plan", REQUEST.question])
    assert main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["execution_mode"] == "offline_fixture"
    assert output["planning_status"] == "ready"
    assert output["run_status"] == "running"
    assert output["research_passes_completed"] == 0
    assert output["pending_queries"] and not output["errors"]


def test_cli_configured_live_provider_has_no_silent_fallback(monkeypatch, capsys):
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_ID", "synthetic_model")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_API_KEY", "synthetic_secret")
    monkeypatch.setattr(sys, "argv", ["evidenceforge-plan", REQUEST.question])
    assert main() == 1
    output = capsys.readouterr().out
    assert "requires explicit fixture mode" in output
    assert "synthetic_secret" not in output


def test_cli_invalid_request(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evidenceforge-plan", "   "])
    assert main() == 1
    assert "Invalid research request" in capsys.readouterr().out


def test_manager_rejects_stale_counters_even_without_a_plan():
    state = apply_update(initial_state(REQUEST), {"iteration_count": 1})
    with pytest.raises(PlanningContractError, match="fresh run"):
        manager(state)


@pytest.mark.parametrize("address", [("127.0.0.1", 9), ("203.0.113.1", 443)])
def test_offline_guard_still_blocks_regular_socket_connections(address):
    import socket

    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="Offline tests"):
            connection.connect(address)
