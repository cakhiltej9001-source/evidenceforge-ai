"""Check citation mechanics and absent-aspect handling across retained corpora.

This runner admits only integrity-checked public snapshots and performs no search
or live model calls. Distinct snapshots are not independent source verification.
"""

import argparse
import asyncio
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import cast

from evidenceforge.evaluation_retained import load_retained_public_sources, replay_public_case
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.nodes.extraction import tokens
from evidenceforge.retrieval.contracts import RetrievedSource
from evidenceforge.schemas import SourceType
from evidenceforge.storage.artifacts import ArtifactStore


def load_corpus(path: Path, *, include_excerpts: bool) -> tuple[tuple[RetrievedSource, ...], str]:
    """Explicit excerpt mode preserves acquisition scope and retained byte hashes."""
    if not include_excerpts:
        return load_retained_public_sources(path)
    raw = path.read_bytes()
    state = StateSnapshot.model_validate_json(raw)
    artifacts = ArtifactStore(
        path.parents[2] / "artifacts", state.owner_scope, state.run_id, 16_000_000
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
            or source.access_status not in {"available", "excerpt_only"}
        ):
            continue
        scope = "full_text" if source.access_status == "available" else "search_excerpt"
        if acquisition.content_scope != scope:
            raise ValueError("Source access and acquisition content scopes differ.")
        snapshot = state.raw_result_refs[acquisition.snapshot_id]
        content = artifacts.read(snapshot)
        if source.content_hash != snapshot.content_hash:
            raise ValueError("Source hash does not match its retained snapshot.")
        sources[source.id] = RetrievedSource(
            title=source.title,
            url=source.url,
            content=content,
            source_type=source.source_type,
            publisher=source.publisher,
            publication_date=source.publication_date,
            source_family=source.source_family,
            content_scope=scope,
        )
    if not sources:
        raise ValueError("No admitted integrity-checked public snapshots were found.")
    return tuple(sources[key] for key in sorted(sources)), hashlib.sha256(raw).hexdigest()


async def evaluate(
    state_paths: list[Path], output: Path, *, include_excerpts: bool = False
) -> dict[str, object]:
    """Replay the same two-aspect request in each unchanged retained corpus."""
    if len(state_paths) < 2:
        raise ValueError("At least two saved corpora are required.")
    rows: list[dict[str, object]] = []
    digests: list[str] = []
    hash_sets: list[set[str]] = []
    for index, path in enumerate(state_paths, 1):
        sources, digest = load_corpus(path, include_excerpts=include_excerpts)
        sources = sources[:5]
        hashes = {hashlib.sha256(source.content.encode("utf-8")).hexdigest() for source in sources}
        present = set().union(*(tokens(source.content) for source in sources))
        absent = sorted({"solar", "wind"} - present)
        case_output = output / "runs" / f"corpus_{index}"
        row = await replay_public_case(sources, case_output)
        replay_path = max(
            (case_output / "reports").glob("*/state.json"), key=lambda p: p.stat().st_mtime_ns
        )
        replay = StateSnapshot.model_validate_json(replay_path.read_bytes())
        scopes = {source.access_status for source in replay.source_records.values()}
        expected_scopes = {
            "available" if source.content_scope == "full_text" else "excerpt_only"
            for source in sources
        }
        row["source_access_scope_preserved"] = scopes == expected_scopes
        row["claims_stay_within_corpus_snapshots"] = {
            source.content_hash for source in replay.source_records.values()
        }.issubset(hashes)
        row.update(
            {
                "corpus_id": f"corpus_{index}",
                "input_state_sha256": digest,
                "retained_snapshots": len(hashes),
                "full_text_sources": sum(s.content_scope == "full_text" for s in sources),
                "search_excerpt_sources": sum(s.content_scope == "search_excerpt" for s in sources),
                "source_family_signals": len(
                    {source.source_family for source in sources if source.source_family}
                ),
                "absent_whole_word_aspects": absent,
                "substring_only_wind_occurrences": sum(
                    source.content.lower().count("wind") for source in sources
                )
                if "wind" in absent
                else 0,
                "corpus": [
                    {
                        "title": source.title,
                        "url": str(source.url),
                        "snapshot_sha256": hashlib.sha256(
                            source.content.encode("utf-8")
                        ).hexdigest(),
                    }
                    for source in sources
                ],
            }
        )
        rows.append(row)
        digests.append(digest)
        hash_sets.append(hashes)
    checks = {
        "distinct_saved_states": len(set(digests)) == len(digests),
        "snapshot_sets_disjoint": all(
            not left.intersection(right) for left, right in combinations(hash_sets, 2)
        ),
        "all_exact_locators": all(row["evidence"] == row["exact_locator_passages"] for row in rows),
        "all_cited_claims_supported": all(
            row["citation_precision_against_retained_text"] == 1.0
            and row["citation_coverage"] == 1.0
            for row in rows
            if cast(int, row["claims"]) > 0
        ),
        "actual_absent_aspect_exercised": any(row["absent_whole_word_aspects"] for row in rows),
        "absent_aspect_not_completed": all(
            row["run_status"] != "completed"
            and cast(int, row["gaps"]) >= len(cast(list[str], row["absent_whole_word_aspects"]))
            for row in rows
            if row["absent_whole_word_aspects"]
        ),
        "source_access_scope_preserved": all(row["source_access_scope_preserved"] for row in rows),
        "corpora_do_not_mix": all(row["claims_stay_within_corpus_snapshots"] for row in rows),
        "no_provider_calls": all(row["provider_calls"] == 0 for row in rows),
    }
    result: dict[str, object] = {
        "evaluation": "retained_distinct_corpora_mechanical_check",
        "question": "What do the retained sources say about solar and wind electricity output?",
        "criteria": ["solar", "wind"],
        "cases": rows,
        "checks": checks,
        "provider_calls": 0,
        "source_truth_verified": False,
        "independent_semantic_validation": False,
        "independent_human_review": False,
        "scope": (
            "two energy-related corpora; scripted reasoning; no topical accuracy generalization"
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", action="append", type=Path, required=True)
    parser.add_argument("--include-excerpts", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path(".evidenceforge/evaluation/retained-corpora")
    )
    args = parser.parse_args()
    result = asyncio.run(evaluate(args.state, args.output, include_excerpts=args.include_excerpts))
    print(json.dumps(result, indent=2))
    return 0 if all(cast(dict[str, bool], result["checks"]).values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
