"""Durable offline workers cooperate and stop before unreviewed recovery."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.storage.job_queue import JobQueue, JobQueueFailure


def test_two_workers_claim_exactly_once_and_scope_isolation(tmp_path):
    first = JobQueue(tmp_path)
    job = first.enqueue(
        ResearchRequest(question="Compare solar and wind output."), "second-pass", BudgetLimits()
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(
            pool.map(lambda worker: JobQueue(tmp_path).claim("local", worker), ["a", "b"])
        )
    assert sum(claim is not None for claim in claims) == 1
    assert next(claim["id"] for claim in claims if claim) == job
    with pytest.raises(JobQueueFailure):
        first.get(job, "another_owner")
    assert JobQueue(tmp_path).claim("another_owner", "c") is None


def test_expired_worker_requires_explicit_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr("evidenceforge.storage.job_queue.time.time", lambda: 100)
    queue = JobQueue(tmp_path)
    job = queue.enqueue(
        ResearchRequest(question="Compare solar and wind output."), "empty", BudgetLimits()
    )
    queue.claim("local", "first", lease_seconds=2)
    queue.set_thread(job, "first", "thread_example")
    monkeypatch.setattr("evidenceforge.storage.job_queue.time.time", lambda: 103)
    assert queue.claim("local", "second") is None
    assert queue.get(job, "local")["status"] == "interrupted"
    with pytest.raises(JobQueueFailure):
        queue.finish(job, "first", "completed")
    queue.continue_job(job, "local")
    assert queue.claim("local", "second")["action"] == "resume"


def test_fresh_processes_plan_approve_and_export(tmp_path):
    def cli(*args):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "evidenceforge.offline_jobs",
                "--data-dir",
                str(tmp_path),
                "--owner",
                "alice",
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=True,
        )
        return json.loads(completed.stdout)

    job = cli("enqueue", "Compare solar and wind electricity output.")["job"]
    assert cli("worker")["job"] == job
    planned = cli("status", job)
    assert planned["status"] == "awaiting_approval"
    cli("approve", job, "--plan-version", "999")
    cli("worker")
    assert cli("status", job)["status"] == "interrupted"
    cli("approve", job, "--plan-version", "1")
    assert cli("worker")["job"] == job
    completed = cli("status", job)
    assert completed["status"] == "completed"
    assert completed["thread"] == planned["thread"]
    assert cli("worker")["job"] is None


def test_other_scope_cannot_expire_a_worker(tmp_path, monkeypatch):
    monkeypatch.setattr("evidenceforge.storage.job_queue.time.time", lambda: 100)
    queue = JobQueue(tmp_path)
    job = queue.enqueue(
        ResearchRequest(question="Compare solar and wind output.", owner_scope="alice"),
        "empty",
        BudgetLimits(),
    )
    queue.claim("alice", "first", lease_seconds=2)
    monkeypatch.setattr("evidenceforge.storage.job_queue.time.time", lambda: 103)
    assert queue.claim("bob", "second") is None
    assert queue.get(job, "alice")["status"] == "running"


@pytest.mark.parametrize(
    "model,live",
    [
        ("evidenceforge.models.gemini.GeminiResearchModel", False),
        ("evidenceforge.models.fixtures.FixtureResearchModel", True),
    ],
)
def test_resume_rejects_paid_or_live_profiles_before_service_creation(
    tmp_path, monkeypatch, model, live
):
    from types import SimpleNamespace

    from evidenceforge.services.job_worker import process_one

    queue = JobQueue(tmp_path / "jobs")
    job = queue.enqueue(
        ResearchRequest(question="Compare solar and wind output."), "second-pass", BudgetLimits()
    )
    queue.claim("local", "initial")
    queue.set_thread(job, "initial", "thread_example")
    queue.finish(job, "initial", "awaiting_approval")
    queue.continue_job(job, "local", plan_version=1)
    called = []

    def forbidden_service(*args):
        called.append(True)
        raise AssertionError("Unsafe profile reached service creation")

    monkeypatch.setattr(
        "evidenceforge.services.job_worker.LocalWorkbench",
        lambda path: SimpleNamespace(registered_service=forbidden_service, close=lambda: None),
    )
    monkeypatch.setattr(
        "evidenceforge.services.job_worker.CheckpointRepository.load",
        lambda *args: SimpleNamespace(
            profile=json.dumps(
                {"model": model, "research_options": {"live_web": live, "live_energy": False}}
            )
        ),
    )
    assert process_one(tmp_path) == job
    assert called == []
    assert queue.get(job, "local")["status"] == "interrupted"


def test_constructor_failure_stops_heartbeat_and_records_interruption(tmp_path, monkeypatch):
    from threading import enumerate as active_threads

    from evidenceforge.services.job_worker import process_one

    queue = JobQueue(tmp_path / "jobs")
    job = queue.enqueue(
        ResearchRequest(question="Compare solar and wind output."), "second-pass", BudgetLimits()
    )

    def fail_constructor(path):
        raise RuntimeError("private-error-details")

    monkeypatch.setattr("evidenceforge.services.job_worker.LocalWorkbench", fail_constructor)
    assert process_one(tmp_path) == job
    saved = queue.get(job, "local")
    assert saved["status"] == "interrupted"
    assert saved["error"] == "worker_operation_failed"
    assert "private-error-details" not in str(saved)
    assert not any(thread.name == "offline-job-lease" for thread in active_threads())
