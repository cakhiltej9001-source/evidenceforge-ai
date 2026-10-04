"""Approval, restart, scopes, safe exports and service-backed UI checks."""

import asyncio
import json

import pytest

from evidenceforge.exports import report_export
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import PlanDraft
from evidenceforge.research import ResearchOptions
from evidenceforge.schemas import ResearchRequest
from evidenceforge.services.research import ResearchService
from evidenceforge.storage.checkpoints import CheckpointFailure, CheckpointRepository
from evidenceforge.workbench import LocalWorkbench

QUESTION = "Compare solar and wind electricity output."


def service(path, model=None):
    return ResearchService(path, model=model, options=ResearchOptions(require_plan_approval=True))


def test_approval_blocks_calls_and_survives_fresh_service(tmp_path):
    model = FixtureResearchModel()
    paused = asyncio.run(service(tmp_path, model).run(ResearchRequest(question=QUESTION)))
    assert paused["approval_status"] == "awaiting_approval"
    assert paused["iteration_count"] == 0 and not paused["calls"] and not paused["search_queries"]
    assert model.plan_calls == 1 and model.query_calls == 0
    snapshot = asyncio.run(service(tmp_path).snapshot(paused["thread_id"]))
    assert snapshot == paused
    # Reconnect without a decision must not bypass the interrupt.
    still_paused = asyncio.run(service(tmp_path).resume(paused["thread_id"]))
    assert still_paused["approval_status"] == "awaiting_approval"
    final = asyncio.run(
        service(tmp_path).resume(
            paused["thread_id"],
            decision=PlanDecision(approved=True, plan_version=paused["plan_version"]),
        )
    )
    assert final["run_status"] == "completed" and final["approval_status"] == "approved"
    assert final["planning_attempts"] == 2  # one plan plus one query batch
    with pytest.raises(CheckpointFailure):
        asyncio.run(
            service(tmp_path).resume(
                paused["thread_id"], decision=PlanDecision(approved=True, plan_version=1)
            )
        )


def test_rejection_and_cancel_before_approval_make_no_retrieval_calls(tmp_path):
    for reject in (True, False):
        s = service(tmp_path)
        paused = asyncio.run(s.run(ResearchRequest(question=QUESTION)))
        if not reject:
            s.cancel(paused["thread_id"])
        final = asyncio.run(
            s.resume(
                paused["thread_id"],
                decision=PlanDecision(approved=False, plan_version=1) if reject else None,
            )
        )
        assert final["run_status"] == "cancelled" and not final["calls"]
        assert final["iteration_count"] == 0


def test_stale_and_foreign_approval_do_not_change_checkpoint(tmp_path):
    s = service(tmp_path)
    paused = asyncio.run(s.run(ResearchRequest(question=QUESTION, owner_scope="alice")))
    with pytest.raises(CheckpointFailure):
        asyncio.run(
            s.resume(
                paused["thread_id"], "alice", decision=PlanDecision(approved=True, plan_version=2)
            )
        )
    with pytest.raises(CheckpointFailure):
        asyncio.run(s.snapshot(paused["thread_id"], "bob"))
    with pytest.raises(CheckpointFailure):
        asyncio.run(
            s.resume(
                paused["thread_id"], "bob", decision=PlanDecision(approved=True, plan_version=1)
            )
        )
    assert asyncio.run(s.snapshot(paused["thread_id"], "alice")) == paused
    assert CheckpointRepository(tmp_path / "checkpoints", "bob").threads() == []


def test_json_export_excludes_internal_context_and_logs(tmp_path):
    s = service(tmp_path)
    paused = asyncio.run(s.run(ResearchRequest(question=QUESTION)))
    with pytest.raises(ValueError):
        report_export(paused)
    final = asyncio.run(
        s.resume(paused["thread_id"], decision=PlanDecision(approved=True, plan_version=1))
    )
    final["messages"] = {}  # Exports explicitly omit diagnostic fields.
    data = json.loads(report_export(final))
    assert data["progress"]["run_status"] == "completed"
    assert data["graph"]["nodes"] and data["evidence_mode"] == "synthetic_fixture"
    assert (
        not {"context_refs", "events", "messages", "request", "raw_result_refs", "budget"}
        & data.keys()
    )
    assert (s.report_path(final).with_name("report.json")).is_file()


def test_workbench_runs_real_service_and_reconnects(tmp_path):
    app = LocalWorkbench(tmp_path)
    try:
        key = app.start(ResearchRequest(question=QUESTION), "second-pass")
        paused = app.jobs[("local", key)].result(timeout=60)
        assert paused["thread_id"] in app.threads("local")
        assert app.snapshot("local", paused["thread_id"])["approval_status"] == "awaiting_approval"
        key = app.resume("local", paused["thread_id"], PlanDecision(approved=True, plan_version=1))
        final = app.jobs[("local", key)].result(timeout=60)
        assert final["iteration_count"] == 2 and final["run_status"] == "completed"
        assert app.result("bob", key) is None
    finally:
        app.close()


def test_decision_bool_is_strict():
    with pytest.raises(ValueError):
        PlanDecision(approved="false", plan_version=1)


def test_failed_planning_does_not_wait_for_approval_or_report_insufficiency(tmp_path):
    model = FixtureResearchModel(plan_output={"questions": []})
    final = asyncio.run(service(tmp_path, model).run(ResearchRequest(question=QUESTION)))
    assert final["run_status"] == "failed"
    assert final["approval_status"] == "not_required"
    assert model.query_calls == 0 and not final["calls"]
    assert json.loads(report_export(final))["progress"]["run_status"] == "failed"


def test_edited_plan_reopens_approval_without_replaying_calls(tmp_path):
    model = FixtureResearchModel()
    s = service(tmp_path, model)
    paused = asyncio.run(s.run(ResearchRequest(question=QUESTION)))
    plan = PlanDraft.model_validate(
        {
            "questions": [
                {
                    "question": "What determines solar electricity output?",
                    "acceptance_criteria": ["solar electricity output"],
                },
                {
                    "question": "What determines wind electricity output?",
                    "acceptance_criteria": ["wind electricity output"],
                },
            ]
        }
    )
    edited = asyncio.run(s.edit_plan(paused["thread_id"], plan, 1))
    assert edited["plan_version"] == 2 and edited["approval_status"] == "awaiting_approval"
    assert model.plan_calls == 1 and model.query_calls == 0 and not edited["calls"]
    assert [q["question"] for q in edited["research_questions"]] == [
        q.question for q in plan.questions
    ]
    with pytest.raises(CheckpointFailure):
        asyncio.run(
            s.resume(paused["thread_id"], decision=PlanDecision(approved=True, plan_version=1))
        )
    with pytest.raises(CheckpointFailure):
        asyncio.run(s.edit_plan(paused["thread_id"], plan, 1))
    final = asyncio.run(
        s.resume(paused["thread_id"], decision=PlanDecision(approved=True, plan_version=2))
    )
    assert final["run_status"] == "completed" and model.plan_calls == 1
    assert {q["id"] for q in edited["research_questions"]} == {
        q["id"] for q in final["research_questions"]
    }
    with pytest.raises(CheckpointFailure):
        asyncio.run(s.edit_plan(paused["thread_id"], plan, 2))


def test_edit_limits_and_scoped_timeline_exports(tmp_path):
    from evidenceforge.schemas import BudgetLimits
    from evidenceforge.services.observability import public_timeline

    s = service(tmp_path)
    paused = asyncio.run(
        s.run(
            ResearchRequest(question=QUESTION, owner_scope="alice"),
            BudgetLimits(max_subquestions=1),
        )
    )
    plan = PlanDraft.model_validate(
        {
            "questions": [
                {"question": "Solar output?", "acceptance_criteria": ["solar"]},
                {"question": "Wind output?", "acceptance_criteria": ["wind"]},
            ]
        }
    )
    with pytest.raises(CheckpointFailure):
        asyncio.run(s.edit_plan(paused["thread_id"], plan, 1, "alice"))
    assert asyncio.run(s.snapshot(paused["thread_id"], "alice")) == paused
    paused["events"]["event_private"] = {
        "id": "event_private",
        "kind": "plan_created",
        "message": "PRIVATE_SECRET_CANARY",
        "occurred_at": "2026-10-02T00:00:00Z",
    }
    assert "PRIVATE_SECRET_CANARY" not in json.dumps(public_timeline(paused))
    app = LocalWorkbench(tmp_path)
    try:
        with pytest.raises(CheckpointFailure):
            app.timeline("bob", paused["thread_id"])
        with pytest.raises(CheckpointFailure):
            app.export("bob", paused["thread_id"])
    finally:
        app.close()


def test_paid_human_controls_check_owner_before_provider_work(tmp_path):
    import httpx
    from pydantic import SecretStr

    from evidenceforge.models.gemini import GeminiResearchModel
    from evidenceforge.schemas import BudgetLimits

    adapter = GeminiResearchModel(
        "gemini-3.8-flash",
        SecretStr("synthetic-control-secret"),
        BudgetLimits(),
        transport=httpx.MockTransport(lambda request: pytest.fail("No paid call allowed")),
    )
    s = service(tmp_path, adapter)
    plan = PlanDraft.model_validate(
        {"questions": [{"question": "Solar output?", "acceptance_criteria": ["solar"]}]}
    )
    with pytest.raises(CheckpointFailure):
        asyncio.run(s.resume("thread_fake"))
    with pytest.raises(CheckpointFailure):
        asyncio.run(s.edit_plan("thread_fake", plan, 1))
    assert not adapter.observations
