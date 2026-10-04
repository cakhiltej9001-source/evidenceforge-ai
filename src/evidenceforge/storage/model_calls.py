"""Durable, scoped paid-call reservations and validated response replay."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal, cast

from evidenceforge.identity import stable_id
from evidenceforge.planning import ModelUnavailable
from evidenceforge.schemas import BudgetLimits, Contract, ResearchRequest


class ModelReceipt(Contract):
    id: str
    observation: dict[str, object]
    status: Literal["pending", "succeeded", "failed"] = "pending"
    result: dict[str, object] | None = None


class ModelCallLedger:
    def __init__(
        self,
        root: Path,
        owner: str,
        run: str,
        model: str,
        budget: BudgetLimits,
        *,
        existing: bool = False,
    ) -> None:
        ResearchRequest(question="Model ledger access", owner_scope=owner)
        self.path = root / (stable_id("model_ledger", owner, run)[-32:] + ".sqlite")
        if existing and not self.path.is_file():
            raise ModelUnavailable("This saved run has no durable model-call ledger.")
        root.mkdir(parents=True, exist_ok=True)
        self.budget = budget
        identity = json.dumps(
            {
                "owner": owner,
                "run": run,
                "model": model,
                "budget": budget.model_dump(mode="json"),
                "version": 1,
            },
            sort_keys=True,
        )
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (identity TEXT NOT NULL)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            row = conn.execute("SELECT identity FROM metadata").fetchone()
            if row is None:
                if existing:
                    raise ModelUnavailable("Model ledger registration is unavailable.")
                conn.execute("INSERT INTO metadata VALUES (?)", (identity,))
            elif row[0] != identity:
                raise ModelUnavailable("Model ledger configuration differs from this run.")

    def records(self) -> list[ModelReceipt]:
        with closing(sqlite3.connect(self.path)) as conn:
            return [
                ModelReceipt.model_validate_json(row[0])
                for row in conn.execute("SELECT payload FROM calls ORDER BY rowid")
            ]

    def reserve(self, identifier: str, observation: dict[str, object]) -> tuple[ModelReceipt, bool]:
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            records = [
                ModelReceipt.model_validate_json(row[0])
                for row in conn.execute("SELECT payload FROM calls ORDER BY rowid")
            ]
            for record in records:
                if record.id == identifier:
                    return record, False
            if any(r.status == "pending" for r in records):
                raise ModelUnavailable(
                    "An earlier Gemini call has unconfirmed usage; automatic retry is blocked."
                )
            reserved = sum(
                cast(int, r.observation.get("total_tokens") or r.observation["reserved_tokens"])
                for r in records
            )
            if (
                len(records) >= self.budget.max_model_calls
                or reserved + cast(int, observation["reserved_tokens"])
                > self.budget.max_total_tokens
            ):
                raise ModelUnavailable("Gemini call or token allowance reached.")
            observation = {**observation, "attempt": len(records) + 1}
            receipt = ModelReceipt(id=identifier, observation=observation)
            conn.execute("INSERT INTO calls VALUES (?,?)", (identifier, receipt.model_dump_json()))
            return receipt, True

    def finish(self, receipt: ModelReceipt) -> None:
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT payload FROM calls WHERE id=?", (receipt.id,)).fetchone()
            if row is None or ModelReceipt.model_validate_json(row[0]).status != "pending":
                raise ModelUnavailable("Model receipt is missing or already completed.")
            conn.execute(
                "UPDATE calls SET payload=? WHERE id=?", (receipt.model_dump_json(), receipt.id)
            )


def model_usage(records: list[ModelReceipt]) -> dict[str, object]:
    """Public counters only; exclude response contents and request hashes."""
    observations = [r.observation for r in records]
    return {
        "provider": "gemini",
        "model": observations[0].get("model") if observations else None,
        "paid_calls": len(records),
        "succeeded_calls": sum(r.status == "succeeded" for r in records),
        "unconfirmed_calls": sum(r.status == "pending" for r in records),
        "input_tokens_known": sum(cast(int, o.get("input_tokens") or 0) for o in observations),
        "output_tokens_known": sum(
            cast(int, o.get("output_tokens_including_thinking") or 0) for o in observations
        ),
        "tokens_used_or_reserved": sum(
            cast(
                int,
                o.get("total_tokens")
                if o.get("total_tokens") is not None
                else o["reserved_tokens"],
            )
            for o in observations
        ),
        "usage_unknown_calls": sum(o.get("total_tokens") is None for o in observations),
        "estimated_cost_usd": None,
    }
