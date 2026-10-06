"""Reproducible synthetic fixture evaluation with explicit review status."""

import argparse
import asyncio
import hashlib
import json
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Literal, cast

from pydantic import Field, HttpUrl, model_validator

from evidenceforge.graph.state import ResearchState
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievalOptions, RetrievedSource
from evidenceforge.retrieval.fixtures import (
    DisputeFixture,
    FixtureRetrievalAdapter,
    SecondPassFixture,
)
from evidenceforge.schemas import BudgetLimits, Contract, ResearchRequest, SearchQuery, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


class EvaluationCase(Contract):
    id: str
    split: Literal["development", "held_out"]
    question: str
    scenario: Literal["immediate", "second_pass", "dispute", "empty", "custom_two_pass"]
    reference_passages: tuple[str, ...] = ()
    corpus_passages: tuple[str, ...] = ()
    expected_dispute: bool = False
    expected_abstention: bool = False


class EvaluationDataset(Contract):
    version: Literal[1, 2] = 1
    annotation_status: Literal["draft_requires_human_review", "human_reviewed", "ai_reviewed"]
    annotation_author: str
    reviewed_by: str | None = None
    reviewed_at: date | None = None
    cases: tuple[EvaluationCase, ...] = Field(min_length=20, max_length=30)

    @model_validator(mode="after")
    def require_review_record(self) -> "EvaluationDataset":
        if self.annotation_status in {"human_reviewed", "ai_reviewed"} and not (
            self.reviewed_by and self.reviewed_by.strip() and self.reviewed_at
        ):
            raise ValueError("Human-reviewed labels require reviewer and review date.")
        return self


class FrozenPassageAdapter(FixtureRetrievalAdapter):
    def __init__(self, case: EvaluationCase) -> None:
        super().__init__()
        self.case = case

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> RetrievalBatch:
        self.calls += 1
        index = min(query.research_pass - 1, len(self.case.corpus_passages) - 1)
        return RetrievalBatch(
            results=(
                RetrievedSource(
                    title=f"Synthetic {self.case.id} passage {index + 1}",
                    url=HttpUrl(
                        f"https://example.org/fixtures/evaluation/{self.case.id}/{index + 1}"
                    ),
                    content=self.case.corpus_passages[index],
                ),
            )
        )


class EvaluationFixtureModel(FixtureResearchModel):
    async def plan(self, request: ResearchRequest, *, max_questions: int) -> object:
        prefix, suffix = "Compare ", " outputs."
        if request.question.startswith(prefix) and request.question.endswith(suffix):
            core = request.question[len(prefix) : -len(suffix)]
            if " and " in core:
                left, right = core.split(" and ", 1)
                self.plan_calls += 1
                return {
                    "questions": [
                        {
                            "question": f"What determines {topic} output?",
                            "acceptance_criteria": [f"{topic} output"],
                        }
                        for topic in (left, right)[:max_questions]
                    ]
                }
        return await super().plan(request, max_questions=max_questions)


def retrieval_adapter(case: EvaluationCase) -> FixtureRetrievalAdapter:
    if case.scenario == "custom_two_pass":
        if len(case.corpus_passages) != 2:
            raise ValueError("A custom two-pass case needs exactly two source passages.")
        return FrozenPassageAdapter(case)
    if case.scenario == "second_pass":
        return SecondPassFixture()
    if case.scenario == "dispute":
        return DisputeFixture()
    if case.scenario == "empty":
        return FixtureRetrievalAdapter(RetrievalBatch(results=()))
    return FixtureRetrievalAdapter()


def load_dataset(path: Path) -> tuple[EvaluationDataset, str]:
    raw = path.read_bytes()
    dataset = EvaluationDataset.model_validate_json(raw)
    ids = [case.id for case in dataset.cases]
    if len(set(ids)) != len(ids) or not {"development", "held_out"}.issubset(
        {case.split for case in dataset.cases}
    ):
        raise ValueError("Evaluation cases need unique IDs and both partitions.")
    return dataset, hashlib.sha256(raw).hexdigest()


def score(state: ResearchState, case: EvaluationCase, elapsed_seconds: float) -> dict[str, object]:
    factual = [c for c in state["report_claims"].values() if c["kind"] == "fact"]
    audits = {a["claim_id"]: a for a in state["citation_audit"]}
    supported = {
        c["id"]
        for c in factual
        if c["evidence_ids"]
        and c["id"] in audits
        and audits[c["id"]]["structural_valid"]
        and audits[c["id"]]["support"] == "supported"
    }
    cited = [c for c in factual if c["evidence_ids"]]
    statements = {c["statement"] for c in factual}
    references = set(case.reference_passages)
    disputes = [c for c in state["comparisons"].values() if c["relationship"] == "contradicts"]
    usage = list(state["usage"].values())
    return {
        "case_id": case.id,
        "split": case.split,
        "run_id": state["run_id"],
        "status": state["run_status"],
        "stop_reason": state["stop_reason"],
        "citation_precision": len(supported) / len(cited) if cited else None,
        "citation_coverage": len(cited) / len(factual) if factual else None,
        "groundedness_against_admitted_evidence": len(supported) / len(factual)
        if factual
        else None,
        "required_aspect_coverage": len(references & statements) / len(references)
        if references
        else None,
        "predicted_dispute": bool(disputes),
        "expected_dispute": case.expected_dispute,
        "expected_abstention": case.expected_abstention,
        "abstained_without_claims": state["run_status"] in {"insufficient_evidence", "partial"}
        and not factual,
        "claims": len(factual),
        "retrieval_passes": state["iteration_count"],
        "model_stages": state["planning_attempts"] + state["quality_attempts"],
        "input_tokens_known": sum(cast(int, u["input_tokens"] or 0) for u in usage),
        "output_tokens_known": sum(cast(int, u["output_tokens"] or 0) for u in usage),
        "token_usage_unknown_records": sum(
            u["input_tokens"] is None or u["output_tokens"] is None for u in usage
        ),
        "cost_usd": None,
        "latency_seconds": round(elapsed_seconds, 4),
    }


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    def mean(field: str) -> float | None:
        values = [float(cast(int | float, row[field])) for row in rows if row[field] is not None]
        return round(sum(values) / len(values), 4) if values else None

    tp = sum(bool(r["predicted_dispute"]) and bool(r["expected_dispute"]) for r in rows)
    predicted = sum(bool(r["predicted_dispute"]) for r in rows)
    expected = sum(bool(r["expected_dispute"]) for r in rows)
    abstention = [r for r in rows if r["expected_abstention"]]
    return {
        "cases": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "missing_runs": 0,
        "noncompleted_runs": sum(r["status"] != "completed" for r in rows),
        "citation_precision": mean("citation_precision"),
        "citation_coverage": mean("citation_coverage"),
        "groundedness_against_admitted_evidence": mean("groundedness_against_admitted_evidence"),
        "required_aspect_coverage": mean("required_aspect_coverage"),
        "dispute_precision": round(tp / predicted, 4) if predicted else None,
        "dispute_recall": round(tp / expected, 4) if expected else None,
        "abstention_success": (
            round(sum(bool(r["abstained_without_claims"]) for r in abstention) / len(abstention), 4)
            if abstention
            else None
        ),
        "latency_seconds_mean": mean("latency_seconds"),
        "model_stages_total": sum(cast(int, r["model_stages"]) for r in rows),
        "cost_usd": None,
    }


async def run_fixture_case(
    case: EvaluationCase, output: Path, *, max_passes: int
) -> dict[str, object]:
    adapter = retrieval_adapter(case)
    store = output / "runs" / case.id / f"passes_{max_passes}"
    service = ResearchService(
        store,
        model=EvaluationFixtureModel() if case.scenario == "custom_two_pass" else None,
        retrieval=RetrievalService(store, {SourceType.WEB: adapter}),
    )
    budget = BudgetLimits(
        max_research_passes=max_passes, max_rewrites=0, max_model_calls=12, max_searches=8
    )
    started = perf_counter()
    state = await service.run(ResearchRequest(question=case.question), budget)
    return score(state, case, perf_counter() - started)


async def run_fixture_benchmark(dataset_path: Path, output: Path) -> dict[str, object]:
    dataset, digest = load_dataset(dataset_path)
    output.mkdir(parents=True, exist_ok=True)
    results: dict[str, list[dict[str, object]]] = {"one_pass": [], "full_agent": []}
    for case in dataset.cases:
        for name, passes in (("one_pass", 1), ("full_agent", 3)):
            row = await run_fixture_case(case, output, max_passes=passes)
            results[name].append(row)
            (output / "results.json").write_text(
                json.dumps({"dataset_sha256": digest, "rows": results}, indent=2), encoding="utf-8"
            )
    summary: dict[str, object] = {
        "dataset_sha256": digest,
        "annotation_status": dataset.annotation_status,
        "model": "FixtureResearchModel (scripted, no LLM)",
        "source": "synthetic frozen fixtures",
        "budgets": {"max_model_calls_per_run": 12, "max_searches_per_run": 8},
        "development": {
            name: aggregate([r for r in rows if r["split"] == "development"])
            for name, rows in results.items()
        },
        "held_out": {
            name: aggregate([r for r in rows if r["split"] == "held_out"])
            for name, rows in results.items()
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen synthetic research benchmark.")
    parser.add_argument(
        "--dataset", type=Path, default=Path("docs/evaluation/diverse_dataset.json")
    )
    parser.add_argument("--output", type=Path, default=Path(".evidenceforge/evaluation/phase9"))
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_fixture_benchmark(args.dataset, args.output)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
