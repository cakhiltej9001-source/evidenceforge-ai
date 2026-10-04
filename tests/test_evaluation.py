"""Evaluation denominator semantics, frozen partitions and aggregate paid cap."""

import asyncio
import sqlite3

import httpx
import pytest

from evidenceforge.evaluation import EvaluationCase, EvaluationDataset, load_dataset, score
from evidenceforge.evaluation_paid import PAID_CALL_CAP, CountingTransport
from evidenceforge.graph.state import initial_state
from evidenceforge.schemas import ResearchRequest


def test_dataset_is_frozen_and_partitioned():
    from pathlib import Path

    dataset, digest = load_dataset(Path("docs/evaluation/diverse_dataset.json"))
    assert len(dataset.cases) == 20
    assert sum(c.split == "held_out" for c in dataset.cases) == 8
    assert len(digest) == 64
    assert dataset.annotation_status == "draft_requires_human_review"


def test_zero_denominators_are_not_scored_as_zero():
    case = EvaluationCase(id="empty", split="development", question="Unknown?", scenario="empty")
    state = initial_state(ResearchRequest(question="Unknown?"))
    metrics = score(state, case, 0.01)
    assert metrics["citation_precision"] is None
    assert metrics["citation_coverage"] is None
    assert metrics["groundedness_against_admitted_evidence"] is None
    assert metrics["required_aspect_coverage"] is None


def test_global_cap_stops_before_network(tmp_path):
    guard = CountingTransport(tmp_path, "dataset-hash", "gemini-3.5-flash-lite")
    with sqlite3.connect(guard.path) as conn:
        conn.executemany(
            "INSERT INTO calls VALUES (?,?)",
            [(f"synthetic_{i}", "unconfirmed") for i in range(PAID_CALL_CAP)],
        )
    request = httpx.Request(
        "POST",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
        content=b"synthetic request",
    )
    with pytest.raises(httpx.TransportError, match="cap reached"):
        asyncio.run(guard.handle_async_request(request))
    assert guard.count() == PAID_CALL_CAP


def test_counting_transport_preserves_compressed_response(tmp_path, monkeypatch):
    import gzip

    compressed = gzip.compress(b'{"ok": true}')
    upstream = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-encoding": "gzip"}, stream=httpx.ByteStream(compressed)
        )
    )
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", lambda: upstream)
    guard = CountingTransport(tmp_path, "compressed-test", "gemini-3.5-flash-lite")

    async def run():
        async with httpx.AsyncClient(transport=guard) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
                content=b"request",
            )
            return response.json()

    assert asyncio.run(run()) == {"ok": True}
    assert guard.count() == 1


def test_human_review_status_requires_reviewer_metadata():
    from pathlib import Path

    dataset, _ = load_dataset(Path("docs/evaluation/diverse_dataset.json"))
    payload = dataset.model_dump()
    payload["annotation_status"] = "human_reviewed"
    with pytest.raises(ValueError, match="reviewer and review date"):
        EvaluationDataset.model_validate(payload)
    payload["reviewed_by"] = "Independent reviewer"
    payload["reviewed_at"] = "2026-10-03"
    assert EvaluationDataset.model_validate(payload).annotation_status == "human_reviewed"


def test_uncited_audit_cannot_inflate_citation_precision():
    case = EvaluationCase(id="audit", split="development", question="Audit?", scenario="empty")
    state = initial_state(ResearchRequest(question="Audit?"))
    state["report_claims"] = {
        "uncited": {"id": "uncited", "kind": "fact", "statement": "A", "evidence_ids": []},
        "cited": {"id": "cited", "kind": "fact", "statement": "B", "evidence_ids": ["e"]},
    }
    state["citation_audit"] = [
        {"claim_id": "uncited", "structural_valid": True, "support": "supported"},
        {"claim_id": "cited", "structural_valid": True, "support": "unsupported"},
    ]
    metrics = score(state, case, 0.01)
    assert metrics["citation_precision"] == 0.0
    assert metrics["citation_coverage"] == 0.5
    assert metrics["groundedness_against_admitted_evidence"] == 0.0


def test_paid_cap_identity_cannot_change_in_place(tmp_path):
    CountingTransport(tmp_path, "dataset-hash", "gemini-3.5-flash-lite")
    with pytest.raises(ValueError, match="identity or limit changed"):
        CountingTransport(tmp_path, "dataset-hash", "gemini-3.5-flash-lite", cap=40)


def test_extension_plan_reads_only_frozen_base(tmp_path):
    import json
    from pathlib import Path

    from evidenceforge.evaluation_extension import extension_plan

    dataset, digest = load_dataset(Path("docs/evaluation/diverse_dataset.json"))
    base = tmp_path / "base"
    base.mkdir()
    rows = {
        case.id: {"status": "provider_or_schema_failure" if index < 8 else "completed"}
        for index, case in enumerate(dataset.cases)
    }
    (base / "paid_results.json").write_text(
        json.dumps(
            {
                "dataset_sha256": digest,
                "paid_call_cap": 30,
                "paid_calls_reserved": 26,
                "one_shot": rows,
            }
        ),
        encoding="utf-8",
    )
    with sqlite3.connect(base / "global_paid_calls.sqlite") as conn:
        conn.execute("CREATE TABLE calls (id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO calls VALUES (?, ?)",
            [(f"call_{index}", "http_200") for index in range(26)],
        )
    plan = extension_plan(Path("docs/evaluation/diverse_dataset.json"), base, 40)
    assert plan["missing_one_shot_case_ids"] == [case.id for case in dataset.cases[:8]]
    assert plan["planned_max_attempts"] == 32
    assert plan["base_calls_reserved"] == 26
    assert not (tmp_path / "global_paid_calls.sqlite").exists()


def test_extension_missing_ledger_does_not_create_database(tmp_path):
    import json
    from pathlib import Path

    from evidenceforge.evaluation_extension import extension_plan

    _, digest = load_dataset(Path("docs/evaluation/diverse_dataset.json"))
    (tmp_path / "paid_results.json").write_text(
        json.dumps({"dataset_sha256": digest, "paid_call_cap": 30}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="ledger is missing"):
        extension_plan(Path("docs/evaluation/diverse_dataset.json"), tmp_path, 40)
    assert not (tmp_path / "global_paid_calls.sqlite").exists()


def test_extension_rejects_original_output_before_provider_work(tmp_path):
    from pathlib import Path

    from evidenceforge.evaluation_extension import run_extension

    with pytest.raises(ValueError, match="output must differ"):
        asyncio.run(run_extension(Path("missing.json"), tmp_path, tmp_path, 40))
    assert list(tmp_path.iterdir()) == []
