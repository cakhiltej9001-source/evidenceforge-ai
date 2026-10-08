"""Durable offline job metadata for cooperating workers on one local filesystem."""

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from evidenceforge.guardrails import require_research_request
from evidenceforge.schemas import BudgetLimits, ResearchRequest


class JobQueueFailure(ValueError):
    """A scoped job cannot be claimed or transitioned."""


class JobQueue:
    """SQLite transactions prevent two workers from claiming the same job.

    Lease expiry requires explicit recovery. It never automatically repeats work.
    Scope names are local storage boundaries, not authenticated identities.
    """

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "offline_jobs.sqlite3"
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, payload TEXT NOT NULL,
                action TEXT NOT NULL, status TEXT NOT NULL, worker TEXT,
                lease_until REAL, thread TEXT, error TEXT,
                created REAL NOT NULL, updated REAL NOT NULL)"""
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, request: ResearchRequest, demo: str, budget: BudgetLimits) -> str:
        request = require_research_request(request)
        if demo not in {"immediate", "second-pass", "empty", "dispute"}:
            raise JobQueueFailure("Only offline scenarios may be queued.")
        payload = json.dumps(
            {
                "request": request.model_dump(mode="json"),
                "budget": budget.model_dump(mode="json"),
                "demo": demo,
            }
        )
        if len(payload.encode("utf-8")) > 120_000:
            raise JobQueueFailure("Job metadata exceeds the local allowance.")
        job = "job_" + uuid4().hex
        now = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('queued','running')"
            ).fetchone()[0]
            if count >= 100:
                raise JobQueueFailure("The local queue already has 100 outstanding jobs.")
            db.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, 'start', 'queued', NULL, NULL, "
                "NULL, NULL, ?, ?)",
                (job, request.owner_scope, payload, now, now),
            )
        return job

    def get(self, job: str, owner: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=? AND owner=?", (job, owner)).fetchone()
        if row is None:
            raise JobQueueFailure("Job is unavailable in this scope.")
        return dict(row)

    def claim(self, owner: str, worker: str, *, lease_seconds: float = 60) -> dict[str, Any] | None:
        if not 2 <= lease_seconds <= 3600:
            raise JobQueueFailure("Lease duration must be between 2 and 3600 seconds.")
        now = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE jobs SET status='interrupted', error='worker_lease_expired', "
                "worker=NULL, lease_until=NULL, updated=? WHERE status='running' "
                "AND lease_until<? AND owner=?",
                (now, now, owner),
            )
            row = db.execute(
                "SELECT * FROM jobs WHERE owner=? AND status='queued' ORDER BY created,id LIMIT 1",
                (owner,),
            ).fetchone()
            if row is None:
                return None
            db.execute(
                "UPDATE jobs SET status='running', worker=?, lease_until=?, updated=? WHERE id=?",
                (worker, now + lease_seconds, now, row["id"]),
            )
            result = dict(row)
            result.update(status="running", worker=worker, lease_until=now + lease_seconds)
            return result

    def renew(self, job: str, worker: str, lease_seconds: float = 60) -> None:
        if not 2 <= lease_seconds <= 3600:
            raise JobQueueFailure("Lease duration must be between 2 and 3600 seconds.")
        now = time.time()
        with self.connection() as db:
            changed = db.execute(
                "UPDATE jobs SET lease_until=?, updated=? WHERE id=? AND worker=? "
                "AND status='running' AND lease_until>=?",
                (now + lease_seconds, now, job, worker, now),
            ).rowcount
        if not changed:
            raise JobQueueFailure("Worker lease was lost; inspect saved checkpoints.")

    def set_thread(self, job: str, worker: str, thread: str) -> None:
        with self.connection() as db:
            changed = db.execute(
                "UPDATE jobs SET thread=?, updated=? WHERE id=? AND worker=? "
                "AND status='running' AND lease_until>=?",
                (thread, time.time(), job, worker, time.time()),
            ).rowcount
        if not changed:
            raise JobQueueFailure("Worker lease was lost.")

    def finish(self, job: str, worker: str, status: str, error: str | None = None) -> None:
        if status not in {
            "awaiting_approval",
            "completed",
            "partial",
            "insufficient_evidence",
            "failed",
            "cancelled",
            "interrupted",
        }:
            raise JobQueueFailure("Unknown terminal job status.")
        with self.connection() as db:
            changed = db.execute(
                "UPDATE jobs SET status=?, error=?, worker=NULL, lease_until=NULL, updated=? "
                "WHERE id=? AND worker=? AND status='running' AND lease_until>=?",
                (status, error, time.time(), job, worker, time.time()),
            ).rowcount
        if not changed:
            raise JobQueueFailure("Worker lease was lost.")

    def continue_job(self, job: str, owner: str, *, plan_version: int | None = None) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE id=? AND owner=?", (job, owner)).fetchone()
            if row is None or row["status"] not in {"awaiting_approval", "interrupted"}:
                raise JobQueueFailure("Only pending or interrupted jobs can be continued.")
            if not row["thread"]:
                raise JobQueueFailure(
                    "No checkpoint is attached; inspect before enqueuing fresh work."
                )
            if row["status"] == "awaiting_approval" and (plan_version is None or plan_version < 1):
                raise JobQueueFailure("Approval requires the reviewed plan version.")
            payload = json.loads(row["payload"])
            payload["plan_version"] = plan_version
            db.execute(
                "UPDATE jobs SET action='resume', status='queued', payload=?, "
                "error=NULL, updated=? "
                "WHERE id=?",
                (json.dumps(payload), time.time(), job),
            )
