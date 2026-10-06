"""Equal-corpus comparison. Dry-run by default; paid execution has its own hard cap."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from time import perf_counter

from pydantic import Field

from evidenceforge.config import load_settings
from evidenceforge.evaluation import load_dataset, retrieval_adapter, score
from evidenceforge.evaluation_paid import CountingTransport
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievalOptions
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import (
    BudgetLimits,
    Contract,
    ResearchRequest,
    SearchQuery,
    SourceType,
    Text,
)
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

CAP = 140
DATASET = Path("docs/evaluation/dataset_v2.json")


class SourceText(Contract):
    id: str
    text: Text


class BaselineInput(Contract):
    case_id: str
    question: Text
    sources: tuple[SourceText, ...]


class BaselineClaim(Contract):
    statement: Text
    source_ids: tuple[str, ...] = Field(min_length=1)


class BaselineAnswer(Contract):
    claims: tuple[BaselineClaim, ...] = Field(max_length=8)
    abstained: bool
    dispute: bool


async def corpus(case):
    adapter = retrieval_adapter(case)
    results = {}
    for i in (1, 2):
        batch = await adapter.search(
            SearchQuery(
                id="query_benchmark",
                question_ids=("question_benchmark",),
                text=case.question,
                source_type=SourceType.WEB,
                research_pass=i,
            ),
            RetrievalOptions(),
        )
        for item in batch.results:
            results[str(item.url)] = item
    return RetrievalBatch(results=tuple(results.values()))


def source_hashes():
    files = sorted(Path("src/evidenceforge").rglob("*.py")) + [Path(__file__), DATASET]
    return {
        str(p.relative_to(Path.cwd())) if p.is_absolute() else str(p): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in files
    }


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def score_baseline(answer, sources, case):
    lookup = {s.id: s.text for s in sources}
    support = [
        bool(c.source_ids) and all(s in lookup and c.statement in lookup[s] for s in c.source_ids)
        for c in answer.claims
    ]
    statements = {c.statement for c in answer.claims}
    return {
        "claims": len(answer.claims),
        "citation_support": sum(support) / len(support) if support else None,
        "aspect_coverage": len(set(case.reference_passages) & statements)
        / len(case.reference_passages)
        if case.reference_passages
        else None,
        "dispute": answer.dispute,
        "abstained": answer.abstained and not answer.claims,
        "answer": answer.model_dump(mode="json"),
    }


async def run(output, mode, execute):
    dataset, digest = load_dataset(DATASET)
    settings = load_settings()
    manifest = {
        "dataset_sha256": digest,
        "mode": mode,
        "model": settings.model_id if mode == "gemini" else "fixture",
        "source_hashes": source_hashes(),
        "case_count": len(dataset.cases),
        "maximum_provider_calls": CAP if mode == "gemini" else 0,
        "protocol": (
            "same complete frozen corpus; one response versus "
            "six-stage one-pass workflow; AI-reviewed synthetic "
            "scope; no blind held-out claim"
        ),
    }
    if not execute:
        print(json.dumps(manifest, indent=2))
        return
    target = output / "manifest.json"
    if target.exists() and json.loads(target.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Frozen benchmark identity changed; preserve this run.")
    if not target.exists() and output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory for a new comparison.")
    write(target, manifest)
    guard = (
        CountingTransport(output, digest, settings.model_id, cap=CAP) if mode == "gemini" else None
    )
    result_path = output / "results.json"
    rows = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    for case in dataset.cases:
        batch = await corpus(case)
        sources = tuple(
            SourceText(id=f"source_{i}", text=r.content) for i, r in enumerate(batch.results)
        )
        for variant in ("single_response", "workflow"):
            key = case.id + ":" + variant
            if key in rows:
                continue
            case_dir = output / case.id / variant
            # Never silently repeat a possibly paid interrupted case.
            marker = case_dir / "started.json"
            if marker.exists():
                rows[key] = {"status": "interrupted_requires_review"}
                write(result_path, rows)
                continue
            write(marker, {"case": case.id, "variant": variant})
            started = perf_counter()
            budget = BudgetLimits(
                max_research_passes=1,
                max_rewrites=0,
                max_subquestions=1,
                max_queries_per_pass=1,
                max_searches=1,
                max_model_calls=6,
                max_total_tokens=100_000,
                max_attempts_per_call=1,
            )
            model = (
                GeminiResearchModel(
                    settings.model_id, settings.model_api_key, budget, transport=guard
                )
                if mode == "gemini"
                else None
            )
            try:
                if variant == "single_response":
                    if model:
                        model.bind_run(
                            case_dir / "model_calls", "evaluation", case.id, budget, existing=False
                        )
                        raw = await model._generate(
                            "controlled_baseline",
                            BaselineInput(case_id=case.id, question=case.question, sources=sources),
                            BaselineAnswer,
                            (
                                "Use only these sources. Answer by quoting the minimal "
                                "complete source sentences exactly, including "
                                "qualifications. Attach source IDs to every claim. "
                                "Cover every requested aspect. Mark dispute only for "
                                "conflicting values for the same entity, metric, date "
                                "and scope. Do not resolve conflicts by guessing. If no "
                                "sources support an answer, return no claims and "
                                "abstained=true."
                            ),
                        )
                        answer = BaselineAnswer.model_validate(raw)
                    else:
                        answer = BaselineAnswer(
                            claims=tuple(
                                BaselineClaim(statement=s.text, source_ids=(s.id,)) for s in sources
                            ),
                            abstained=not sources,
                            dispute=case.expected_dispute,
                        )
                    result = score_baseline(answer, sources, case)
                    result["status"] = "completed"
                else:
                    if model is None:
                        model = FixtureResearchModel(
                            plan_output={
                                "questions": [
                                    {
                                        "question": case.question,
                                        "acceptance_criteria": list(case.reference_passages)
                                        or ["source-backed answer"],
                                    }
                                ]
                            }
                        )
                    service = ResearchService(
                        case_dir,
                        model=model,
                        retrieval=RetrievalService(
                            case_dir, {SourceType.WEB: FixtureRetrievalAdapter(batch)}
                        ),
                        options=ResearchOptions(production_policy_version=1),
                    )
                    state = await service.run(
                        ResearchRequest(question=case.question, owner_scope="evaluation"), budget
                    )
                    result = score(state, case, perf_counter() - started)
                    result["answer"] = {
                        "claims": [
                            {"statement": c["statement"], "evidence_ids": c["evidence_ids"]}
                            for c in state["report_claims"].values()
                        ]
                    }
                result.update(
                    case_id=case.id,
                    variant=variant,
                    elapsed_seconds=round(perf_counter() - started, 3),
                    observations=getattr(model, "observations", []),
                )
                rows[key] = result
            except Exception as exc:
                rows[key] = {
                    "case_id": case.id,
                    "variant": variant,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "elapsed_seconds": round(perf_counter() - started, 3),
                    "observations": getattr(model, "observations", []),
                }
            write(result_path, rows)
            print(
                json.dumps(
                    {
                        "case": case.id,
                        "variant": variant,
                        "status": rows[key]["status"],
                        "reserved_calls": guard.count() if guard else 0,
                    }
                ),
                flush=True,
            )
    write(
        output / "summary.json",
        {
            "dataset_sha256": digest,
            "rows": len(rows),
            "reserved_calls": guard.count() if guard else 0,
            "cap": CAP if guard else 0,
            "statuses": {
                status: sum(r["status"] == status for r in rows.values())
                for status in sorted({r["status"] for r in rows.values()})
            },
            "semantic_assessment": (
                "Review per-case saved answers against the versioned "
                "rubric; no source-truth score is inferred."
            ),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("fixture", "gemini"), default="fixture")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.output, args.mode, args.execute))
