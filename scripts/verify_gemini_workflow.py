"""Verify one fresh Gemini workflow under the existing 40-call extension ledger."""

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
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

BASE = Path(".evidenceforge/evaluation/phase9_extension")
OUTPUT = Path(".evidenceforge/evaluation/phase9_workflow_repair")
CAP = 40


async def run(execute: bool) -> dict[str, object]:
    dataset, digest = load_dataset(Path("docs/evaluation/diverse_dataset.json"))
    case = next(case for case in dataset.cases if case.id == "diverse_14")
    with sqlite3.connect(
        (BASE / "global_paid_calls.sqlite").resolve().as_uri() + "?mode=ro", uri=True
    ) as conn:
        count = int(conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0])
    plan: dict[str, object] = {
        "case": case.id,
        "used": count,
        "shared_cap": CAP,
        "maximum_new_calls": FULL_BUDGET.max_model_calls,
        "scope": "post-repair diagnostic; frozen original outcomes retained",
    }
    if not execute:
        return plan
    if count + FULL_BUDGET.max_model_calls > CAP:
        raise ValueError("Insufficient shared allowance for the workflow verification")
    if (OUTPUT / "result.json").exists():
        raise ValueError("Verification outcome already exists; do not silently rerun")
    settings = load_settings()
    if settings.model_id is None or settings.model_api_key is None:
        raise ValueError("Gemini configuration is required")
    original = json.loads((BASE / "extension_manifest.json").read_text(encoding="utf-8"))
    if settings.model_id != original["model"]:
        raise ValueError("Model must match the extension")
    manifest = {
        **plan,
        "dataset_sha256": digest,
        "model": settings.model_id,
        "budget": FULL_BUDGET.model_dump(mode="json"),
        "model_source_sha256": hashlib.sha256(
            Path("src/evidenceforge/models/gemini.py").read_bytes()
        ).hexdigest(),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    guard = CountingTransport(BASE, digest, settings.model_id, cap=CAP)
    model = GeminiResearchModel(
        settings.model_id, settings.model_api_key, FULL_BUDGET, transport=guard
    )
    retrieval = RetrievalService(OUTPUT, {SourceType.WEB: retrieval_adapter(case)})
    service = ResearchService(OUTPUT, model=model, retrieval=retrieval)
    started = perf_counter()
    state = await service.run(ResearchRequest(question=case.question), FULL_BUDGET)
    result = {
        **manifest,
        "row": score(state, case, perf_counter() - started),
        "observations": model.observations,
        "extension_calls_reserved": guard.count(),
        "new_calls": guard.count() - count,
    }
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.execute)), indent=2))
