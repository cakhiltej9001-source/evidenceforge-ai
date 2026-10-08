"""Replay integrity-checked public snapshots without search or paid models.

This measures citation/provenance mechanics. It does not independently establish
source truth, semantic correctness, or quality of live model reasoning.
"""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import cast

from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievalOptions, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.storage.artifacts import ArtifactStore


class RetainedPublicAdapter(FixtureRetrievalAdapter):
    """A replay adapter never performs network requests."""

    name = "retained_public_replay"
    is_live = False


def load_retained_public_sources(state_path: Path) -> tuple[tuple[RetrievedSource, ...], str]:
    """Verify retained hashes and scope before admitting only public web/API text."""
    raw = state_path.read_bytes()
    state = StateSnapshot.model_validate_json(raw)
    artifacts = ArtifactStore(
        state_path.parents[2] / "artifacts", state.owner_scope, state.run_id, 16_000_000
    )
    sources: dict[str, RetrievedSource] = {}
    for acquisition in state.source_acquisitions.values():
        source = state.source_records[acquisition.source_id]
        if (
            source.source_type not in {SourceType.WEB, SourceType.API}
            or source.owner_scope is not None
            or source.document_id is not None
            or source.url is None
            or source.provider == "fixture"
            or source.access_status != "available"
        ):
            continue
        snapshot = state.raw_result_refs[acquisition.snapshot_id]
        text = artifacts.read(snapshot)
        if source.content_hash != snapshot.content_hash:
            raise ValueError("Source hash does not match its retained snapshot.")
        sources[source.id] = RetrievedSource(
            title=source.title,
            url=source.url,
            content=text,
            source_type=source.source_type,
            publisher=source.publisher,
            publication_date=source.publication_date,
            source_family=source.source_family,
        )
    if not sources:
        raise ValueError("No integrity-checked public full-text source snapshots were found.")
    return tuple(sources[key] for key in sorted(sources)), hashlib.sha256(raw).hexdigest()


async def replay_public_case(
    sources: tuple[RetrievedSource, ...],
    output: Path,
    *,
    question: str = "What do the retained sources say about solar and wind electricity output?",
    criteria: tuple[str, ...] = ("solar", "wind"),
) -> dict[str, object]:
    model = FixtureResearchModel(
        plan_output={"questions": [{"question": question, "acceptance_criteria": list(criteria)}]}
    )
    adapter = RetainedPublicAdapter(RetrievalBatch(results=sources))
    service = ResearchService(
        output,
        model=model,
        retrieval=RetrievalService(
            output,
            {SourceType.WEB: adapter},
            # Keep repeated inputs inside the response contract so the duplicate
            # control exercises deduplication rather than schema rejection.
            RetrievalOptions(max_results=max(5, len(sources))),
        ),
    )
    started = perf_counter()
    state = await service.run(
        ResearchRequest(question=question),
        BudgetLimits(
            max_research_passes=1,
            max_rewrites=0,
            max_subquestions=1,
            max_queries_per_pass=1,
            max_searches=1,
            max_model_calls=8,
        ),
    )
    facts = [row for row in state["report_claims"].values() if row["kind"] == "fact"]
    audits = {row["claim_id"]: row for row in state["citation_audit"]}
    cited = [row for row in facts if row["evidence_ids"]]
    supported = [
        row
        for row in cited
        if row["id"] in audits
        and audits[row["id"]]["structural_valid"]
        and audits[row["id"]]["support"] == "supported"
    ]
    snapshot = StateSnapshot.model_validate(state)
    replay_store = ArtifactStore(
        output / "artifacts", snapshot.owner_scope, snapshot.run_id, 16_000_000
    )
    exact_locators = 0
    for evidence in snapshot.evidence_store.values():
        locator = evidence.locator
        text = replay_store.read(snapshot.raw_result_refs[locator.snapshot_id])
        if text[locator.start_offset : locator.end_offset] == evidence.passage:
            exact_locators += 1
    contradictions = sum(
        row["relationship"] == "contradicts" for row in state["comparisons"].values()
    )
    return {
        "input_results": len(sources),
        "run_status": state["run_status"],
        "stop_reason": state["stop_reason"],
        "claims": len(facts),
        "sources": len(snapshot.source_records),
        "evidence": len(snapshot.evidence_store),
        "exact_locator_passages": exact_locators,
        "citation_precision_against_retained_text": len(supported) / len(cited) if cited else None,
        "citation_coverage": len(cited) / len(facts) if facts else None,
        "gaps": len(state["gaps"]),
        "quantitative_conflicts_reported": contradictions,
        "provider_calls": 0,
        "scripted_model_stages": state["planning_attempts"] + state["quality_attempts"],
        "latency_seconds": round(perf_counter() - started, 4),
        "independent_semantic_validation": False,
    }


async def run_retained_public_evaluation(state_path: Path, output: Path) -> dict[str, object]:
    sources, digest = load_retained_public_sources(state_path)
    # Respect the existing bounded retrieval contract for repeatable runs.
    sources = sources[:5]
    controls = {
        "available_snapshots": (sources, ("solar", "wind")),
        "duplicate_snapshot_control": (sources + sources[:1], ("solar", "wind")),
        "missing_aspect_control": (sources, ("solar", "plutonium exports")),
        "empty_corpus_control": ((), ("solar", "wind")),
    }
    rows = {}
    for case_id, (corpus, criteria) in controls.items():
        question = (
            "What do the retained sources say about solar electricity output and plutonium exports?"
            if case_id == "missing_aspect_control"
            else "What do the retained sources say about solar and wind electricity output?"
        )
        rows[case_id] = await replay_public_case(
            corpus, output / "runs" / case_id, question=question, criteria=criteria
        )
    baseline, duplicate = rows["available_snapshots"], rows["duplicate_snapshot_control"]
    result: dict[str, object] = {
        "evaluation": "retained_public_snapshot_mechanical_replay",
        "input_state_sha256": digest,
        "corpus_sources": len(sources),
        "corpus": [
            {
                "title": source.title,
                "url": str(source.url),
                "snapshot_sha256": hashlib.sha256(source.content.encode("utf-8")).hexdigest(),
            }
            for source in sources
        ],
        "source_truth_verified": False,
        "independent_human_review": False,
        "model": "scripted scoped fixture reasoning over real retained text",
        "provider_calls": 0,
        "cases": rows,
        "checks": {
            "available_has_supported_citations": cast(int, baseline["claims"]) > 0
            and baseline["citation_precision_against_retained_text"] == 1.0,
            "duplicates_do_not_inflate_evidence": baseline["sources"] == duplicate["sources"]
            and baseline["evidence"] == duplicate["evidence"]
            and baseline["claims"] == duplicate["claims"],
            "missing_aspect_is_not_completed": rows["missing_aspect_control"]["run_status"]
            != "completed",
            "empty_has_no_claims": rows["empty_corpus_control"]["claims"] == 0
            and rows["empty_corpus_control"]["run_status"] != "completed",
            "all_locators_exact": all(
                row["evidence"] == row["exact_locator_passages"] for row in rows.values()
            ),
        },
        "scope": "one energy corpus; controlled replay; no live search or LLM comparison",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(".evidenceforge/evaluation/retained-public")
    )
    args = parser.parse_args()
    result = asyncio.run(run_retained_public_evaluation(args.state, args.output))
    print(json.dumps(result, indent=2))
    return 0 if all(cast(dict[str, bool], result["checks"]).values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
