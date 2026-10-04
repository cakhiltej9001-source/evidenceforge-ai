"""Owner-scoped thread metadata and process-released single-writer locks."""

import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from evidenceforge.graph.state import ResearchState, validate_state
from evidenceforge.identity import stable_id
from evidenceforge.schemas import Contract, Identifier, ResearchRequest


class CheckpointFailure(ValueError):
    """Missing, foreign, incompatible or concurrently active workflow thread."""


class RunRegistration(Contract):
    owner_scope: Identifier
    thread_id: Identifier
    initial_state: dict[str, object]
    profile: str


class CheckpointRepository:
    def __init__(self, root: Path, owner: str) -> None:
        ResearchRequest(question="Checkpoint access", owner_scope=owner)
        self.owner = owner
        self.directory = root / stable_id("owner", owner)[-32:]
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "workflow.sqlite"
        self.registry = self.directory / "runs.sqlite"
        with sqlite3.connect(self.registry) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS runs (thread TEXT PRIMARY KEY, record TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS cancellations (thread TEXT PRIMARY KEY)")

    def register(self, state: ResearchState, profile: str) -> None:
        state = validate_state(state)
        if state["owner_scope"] != self.owner:
            raise CheckpointFailure("Checkpoint owner scope mismatch.")
        record = RunRegistration(
            owner_scope=self.owner,
            thread_id=state["thread_id"],
            initial_state=dict(state),
            profile=profile,
        )
        with sqlite3.connect(self.registry) as conn:
            conn.execute(
                "INSERT INTO runs VALUES (?,?)", (record.thread_id, record.model_dump_json())
            )

    def load(self, thread: str) -> RunRegistration:
        with sqlite3.connect(self.registry) as conn:
            row = conn.execute("SELECT record FROM runs WHERE thread=?", (thread,)).fetchone()
        if row is None:
            raise CheckpointFailure("Thread is unavailable in this owner scope.")
        record = RunRegistration.model_validate_json(row[0])
        state = validate_state(record.initial_state)
        if (
            record.owner_scope != self.owner
            or record.thread_id != thread
            or state["owner_scope"] != self.owner
            or state["thread_id"] != thread
        ):
            raise CheckpointFailure("Checkpoint registration integrity failed.")
        return record

    def threads(self, limit: int = 50) -> list[str]:
        """Bounded owner-scoped reconnect inventory, newest registrations first."""
        if not 1 <= limit <= 100:
            raise ValueError("Invalid reconnect limit.")
        with sqlite3.connect(self.registry) as conn:
            rows = conn.execute(
                "SELECT thread FROM runs ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self.load(row[0]).thread_id for row in rows]

    def request_cancel(self, thread: str) -> None:
        self.load(thread)
        with sqlite3.connect(self.registry) as conn:
            conn.execute("INSERT OR IGNORE INTO cancellations VALUES (?)", (thread,))

    def cancellation_requested(self, thread: str) -> bool:
        with sqlite3.connect(self.registry) as conn:
            return (
                conn.execute("SELECT 1 FROM cancellations WHERE thread=?", (thread,)).fetchone()
                is not None
            )

    @contextmanager
    def exclusive(self, thread: str) -> Iterator[None]:
        path = self.directory / (stable_id("lock", thread)[-32:] + ".lock")
        with path.open("a+b") as stream:
            if path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise CheckpointFailure(
                    "Thread is already active; one writer per thread is supported."
                ) from exc
            try:
                yield
            finally:
                stream.seek(0)
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
