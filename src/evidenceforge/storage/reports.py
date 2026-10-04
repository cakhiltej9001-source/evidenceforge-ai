"""Generated prior reports are scoped navigation context, never retrieval evidence."""

import sqlite3
from pathlib import Path

from pydantic import AwareDatetime

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.extraction import tokens
from evidenceforge.schemas import Contract, Identifier, Text


class PriorReport(Contract):
    id: Identifier
    owner_scope: Identifier
    run_id: Identifier
    question: Text
    summary: Text
    source_ids: tuple[Identifier, ...]
    evidence_ids: tuple[Identifier, ...]
    saved_at: AwareDatetime
    is_independent_evidence: bool = False


class ReportRepository:
    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "reports.sqlite"
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS reports (owner TEXT, id TEXT, record TEXT, "
                "PRIMARY KEY(owner,id))"
            )

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def save(self, state: ResearchState) -> PriorReport | None:
        s = StateSnapshot.model_validate(state)
        if s.final_report is None or s.finished_at is None:
            return None
        summary = f"Generated report ({s.run_status.value}); context only. " + " ".join(
            c.statement for c in s.report_claims.values()
        )
        record = PriorReport(
            id=stable_id("prior_report", s.owner_scope, s.run_id),
            owner_scope=s.owner_scope,
            run_id=s.run_id,
            question=s.request.question,
            summary=summary[:8000],
            source_ids=s.final_report.source_ids,
            evidence_ids=tuple(
                sorted({eid for c in s.report_claims.values() for eid in c.evidence_ids})
            ),
            saved_at=s.finished_at,
        )
        with self.connect() as conn:
            old = conn.execute(
                "SELECT record FROM reports WHERE owner=? AND id=?", (s.owner_scope, record.id)
            ).fetchone()
            if old is not None and PriorReport.model_validate_json(old[0]) != record:
                raise ValueError("Prior report identity cannot be overwritten.")
            conn.execute(
                "INSERT OR IGNORE INTO reports VALUES (?,?,?)",
                (s.owner_scope, record.id, record.model_dump_json()),
            )
        return record

    def list(
        self, owner: str, limit: int = 32, query: str | None = None
    ) -> tuple[PriorReport, ...]:
        if not 1 <= limit <= 64:
            raise ValueError("Prior report limit exceeded.")
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT record FROM reports WHERE owner=? ORDER BY rowid DESC LIMIT 200", (owner,)
            ).fetchall()
        records = [PriorReport.model_validate_json(row[0]) for row in rows]
        if any(r.owner_scope != owner or r.is_independent_evidence for r in records):
            raise ValueError("Prior report scope or context classification invalid.")
        if query is not None:
            wanted = tokens(query)
            records = sorted(
                (r for r in records if wanted & tokens(r.question + " " + r.summary)),
                key=lambda r: (-len(wanted & tokens(r.question + " " + r.summary)), r.id),
            )
        return tuple(records[:limit])
