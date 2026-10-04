"""Durable retrieval receipts; reserve search capacity atomically before adapter calls."""

import sqlite3
from contextlib import closing
from pathlib import Path

from evidenceforge.identity import stable_id
from evidenceforge.retrieval.contracts import CallReceipt, RetrievalFailure
from evidenceforge.schemas import BudgetLimits


class CallLedger:
    def __init__(self, root: Path, owner_scope: str, run_id: str) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.owner_scope, self.run_id = owner_scope, run_id
        self.path = root / f"{stable_id('ledger', owner_scope, run_id)}.sqlite"
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def records(self) -> dict[str, CallReceipt]:
        with closing(sqlite3.connect(self.path)) as db:
            return {
                identifier: self._validate(payload)
                for identifier, payload in db.execute("SELECT id, payload FROM calls")
            }

    def _validate(self, payload: str) -> CallReceipt:
        receipt = CallReceipt.model_validate_json(payload)
        if receipt.owner_scope != self.owner_scope or receipt.run_id != self.run_id:
            raise ValueError("receipt scope mismatch")
        return receipt

    def reserve(
        self,
        receipt: CallReceipt,
        budget: BudgetLimits,
        extra_searches: int = 0,
    ) -> tuple[CallReceipt, bool]:
        receipt = self._validate(receipt.model_dump_json())
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            rows = dict(db.execute("SELECT id, payload FROM calls"))
            if receipt.call.id in rows:
                previous = self._validate(rows[receipt.call.id])
                if previous.call.request_hash != receipt.call.request_hash:
                    raise ValueError("call request identity changed")
                return previous, False
            searches = sum(
                r.reservation.searches
                for r in map(self._validate, rows.values())
                if r.reservation.status != "released"
            )
            if searches + extra_searches + receipt.reservation.searches > budget.max_searches:
                raise RetrievalFailure("budget")
            db.execute(
                "INSERT INTO calls VALUES (?, ?)",
                (
                    receipt.call.id,
                    receipt.model_dump_json(),
                ),
            )
        return receipt, True

    def finish(self, receipt: CallReceipt) -> None:
        from evidenceforge.graph.reducers import merge_calls, merge_reservations
        from evidenceforge.nodes.common import record_data

        receipt = self._validate(receipt.model_dump_json())
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM calls WHERE id=?", (receipt.call.id,)).fetchone()
            if row is None:
                raise ValueError("call must be reserved before settlement")
            old = self._validate(row[0])
            merged = merge_calls(
                {old.call.id: record_data(old.call)},
                {receipt.call.id: record_data(receipt.call)},
            )
            if merged[receipt.call.id] != record_data(receipt.call):
                raise ValueError("call receipt cannot roll back")
            if old.usage is not None and old.usage != receipt.usage:
                raise ValueError("recorded usage cannot be replaced")
            settled = merge_reservations(
                {old.reservation.id: record_data(old.reservation)},
                {receipt.reservation.id: record_data(receipt.reservation)},
            )
            if settled[receipt.reservation.id] != record_data(receipt.reservation):
                raise ValueError("reservation cannot roll back")
            db.execute(
                "UPDATE calls SET payload=? WHERE id=?",
                (
                    receipt.model_dump_json(),
                    receipt.call.id,
                ),
            )
