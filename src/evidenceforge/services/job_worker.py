"""Execute explicitly queued fixture jobs; live providers cannot be selected."""

import asyncio
import json
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4

from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.storage.checkpoints import CheckpointRepository
from evidenceforge.storage.job_queue import JobQueue, JobQueueFailure
from evidenceforge.workbench import LocalWorkbench


def process_one(directory: Path, owner: str = "local") -> str | None:
    """Claim one durable job, preserve its checkpoint and record its outcome."""
    queue = JobQueue(directory / "jobs")
    worker = "worker_" + uuid4().hex
    job = queue.claim(owner, worker)
    if job is None:
        return None
    job_id = str(job["id"])
    stop = Event()
    lost = Event()

    def heartbeat() -> None:
        while not stop.wait(10):
            try:
                queue.renew(job_id, worker)
            except Exception:
                lost.set()
                return

    renewal = Thread(target=heartbeat, name="offline-job-lease", daemon=True)
    renewal.start()
    app: LocalWorkbench | None = None
    try:
        app = LocalWorkbench(directory)
        payload = json.loads(job["payload"])
        request = ResearchRequest.model_validate(payload["request"])
        if request.owner_scope != owner:
            raise JobQueueFailure("Job request scope mismatch.")
        if job["action"] == "start":
            service = app.service(str(payload["demo"]), gemini=False)
            # Persist the thread before model/retrieval stages. If interrupted,
            # recovery remains explicit and never silently creates a new run.
            state = asyncio.run(
                service.run(
                    request, BudgetLimits.model_validate(payload["budget"]), pause_after="manager"
                )
            )
            thread = str(state["thread_id"])
            queue.set_thread(job_id, worker, thread)
        else:
            thread = str(job["thread"])
            registration = CheckpointRepository(directory / "checkpoints", owner).load(thread)
            profile = json.loads(registration.profile)
            if not str(profile["model"]).endswith(".FixtureResearchModel"):
                raise JobQueueFailure("Paid research is forbidden in the offline job worker.")
            options = profile["research_options"]
            if options.get("live_web") or options.get("live_energy"):
                raise JobQueueFailure("Live sources are forbidden in the offline job worker.")
            service = app.registered_service(owner, thread)
        if lost.is_set():
            raise JobQueueFailure("Worker lease was lost.")
        version = payload.get("plan_version")
        decision = PlanDecision(approved=True, plan_version=version) if version else None
        state = asyncio.run(service.resume(thread, owner, decision=decision))
        status = (
            "awaiting_approval"
            if state["approval_status"] == "awaiting_approval"
            else str(state["run_status"])
        )
        queue.finish(job_id, worker, status)
    except Exception:
        # Exceptions and request text can contain private data; metadata omits them.
        try:
            queue.finish(job_id, worker, "interrupted", "worker_operation_failed")
        except JobQueueFailure:
            pass
    finally:
        stop.set()
        renewal.join(timeout=2)
        if app is not None:
            app.close()
    return job_id
