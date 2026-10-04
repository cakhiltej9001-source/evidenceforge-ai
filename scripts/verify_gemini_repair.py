"""Diagnose repaired coverage and rerun one held-out case under the shared extension cap."""

import argparse
import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path
from time import perf_counter

from evidenceforge.config import load_settings
from evidenceforge.evaluation import load_dataset, retrieval_adapter, score
from evidenceforge.evaluation_extension import FULL_BUDGET
from evidenceforge.evaluation_paid import CountingTransport
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.research import CoverageAssessment, CoverageInput
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

BASE = Path(".evidenceforge/evaluation/phase9_extension")
OUTPUT = Path(".evidenceforge/evaluation/phase9_extension_repair")
DATASET = Path("docs/evaluation/diverse_dataset.json")
CAP = 40


def ledger_count() -> int:
    path = BASE / "global_paid_calls.sqlite"
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0])


async def run(execute: bool) -> dict[str, object]:
    dataset, digest = load_dataset(DATASET)
    case = next(case for case in dataset.cases if case.id == "diverse_13")
    count = ledger_count()
    if not execute:
        return {
            "mode": "dry_run",
            "shared_cap": CAP,
            "used": count,
            "maximum_new_calls": 1 + FULL_BUDGET.max_model_calls,
        }
    settings = load_settings()
    if settings.model_id is None or settings.model_api_key is None:
        raise ValueError("Gemini configuration is required")
    if count + 1 + FULL_BUDGET.max_model_calls > CAP:
        raise ValueError("Shared cap cannot fund this repair verification")
    if (OUTPUT / "result.json").exists():
        raise ValueError("Repair results already exist; inspect them before any new execution")
    files = list((BASE / "full_agent" / case.id / "reports").glob("*/state.json"))
    if len(files) != 1:
        raise ValueError("Expected one retained held-out state")
    state = json.loads(files[0].read_text(encoding="utf-8"))
    source = Path("src/evidenceforge/models/gemini.py")
    manifest = {
        "dataset_sha256": digest,
        "model": settings.model_id,
        "shared_call_cap": CAP,
        "base_calls_reserved": 26,
        "extension_calls_before": count,
        "model_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "original_state_sha256": hashlib.sha256(files[0].read_bytes()).hexdigest(),
        "full_budget": FULL_BUDGET.model_dump(mode="json"),
        "scope": "patched-schema diagnostic, original frozen results retained",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    guard = CountingTransport(BASE, digest, settings.model_id, cap=CAP)
    budget = BudgetLimits(max_model_calls=1, reserved_quality_calls=1, max_total_tokens=100_000)
    model = GeminiResearchModel(settings.model_id, settings.model_api_key, budget, transport=guard)
    model.bind_run(
        OUTPUT / "coverage_receipts",
        "evaluation",
        "coverage_repair_" + state["run_id"],
        budget,
        existing=False,
    )
    outcome: dict[str, object] = {"mode": "patched_schema_diagnostic", "shared_cap": CAP}
    request = CoverageInput.model_validate(
        {
            "questions": state["research_questions"],
            "evidence": list(state["evidence_store"].values()),
        }
    )
    try:
        result = CoverageAssessment.model_validate(await model.evaluate_coverage(request))
        known = {q.id: q for q in request.questions}
        evidence = {e.id: e for e in request.evidence}
        assert len(result.questions) == len(known)
        assert {q.question_id for q in result.questions} == set(known)
        for question in result.questions:
            indices = set()
            for criterion in question.criteria:
                assert criterion.index not in indices
                assert criterion.index < len(known[question.question_id].acceptance_criteria)
                indices.add(criterion.index)
                assert all(
                    eid in evidence and question.question_id in evidence[eid].question_ids
                    for eid in criterion.evidence_ids
                )
        outcome["coverage_diagnostic"] = "validated"
    except Exception as exc:
        outcome.update(
            coverage_diagnostic="failed",
            error_type=type(exc).__name__,
            observations=model.observations,
            extension_calls_reserved=guard.count(),
        )
        (OUTPUT / "result.json").write_text(json.dumps(outcome, indent=2), encoding="utf-8")
        return outcome
    (OUTPUT / "coverage.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    root = OUTPUT / "held_out"
    full_model = GeminiResearchModel(
        settings.model_id, settings.model_api_key, FULL_BUDGET, transport=guard
    )
    retrieval = RetrievalService(root, {SourceType.WEB: retrieval_adapter(case)})
    service = ResearchService(root, model=full_model, retrieval=retrieval)
    started = perf_counter()
    repaired = await service.run(ResearchRequest(question=case.question), FULL_BUDGET)
    outcome.update(
        full_agent=score(repaired, case, perf_counter() - started),
        observations=full_model.observations,
        extension_calls_reserved=guard.count(),
        new_calls=guard.count() - count,
    )
    (OUTPUT / "result.json").write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    return outcome


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.execute)), indent=2))
