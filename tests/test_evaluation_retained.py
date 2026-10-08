"""Mechanical retained-source replay and scope/integrity admission."""

import asyncio
import json

import pytest
from pydantic import HttpUrl

from evidenceforge.evaluation_retained import load_retained_public_sources, replay_public_case
from evidenceforge.retrieval.contracts import ArtifactFailure, RetrievedSource

TEST_SOURCE = RetrievedSource(
    title="Test retained text (not a live factual assertion)",
    url=HttpUrl("https://www.eia.gov/energyexplained/electricity/"),
    content="Solar electricity output increased. Wind electricity output decreased.",
)


def test_real_text_replay_checks_citations_partial_and_empty(tmp_path):
    available = asyncio.run(replay_public_case((TEST_SOURCE,), tmp_path / "available"))
    assert available["run_status"] == "completed"
    assert available["citation_precision_against_retained_text"] == 1.0
    assert available["evidence"] == available["exact_locator_passages"]
    partial = asyncio.run(
        replay_public_case(
            (TEST_SOURCE,),
            tmp_path / "partial",
            question="What do sources say about solar output and plutonium exports?",
            criteria=("solar", "plutonium exports"),
        )
    )
    assert partial["run_status"] != "completed"
    assert partial["claims"] > 0
    empty = asyncio.run(replay_public_case((), tmp_path / "empty"))
    assert empty["claims"] == 0
    assert empty["citation_precision_against_retained_text"] is None
    assert available["provider_calls"] == partial["provider_calls"] == empty["provider_calls"] == 0


def test_loader_checks_source_snapshot_hash_and_never_reads_new_network(tmp_path):
    output = tmp_path / "retained"
    asyncio.run(replay_public_case((TEST_SOURCE,), output))
    state_path = next((output / "reports").glob("*/state.json"))
    sources, digest = load_retained_public_sources(state_path)
    assert len(sources) == 1
    assert sources[0].content == TEST_SOURCE.content
    assert len(digest) == 64
    state = json.loads(state_path.read_text(encoding="utf-8"))
    acquisition = next(iter(state["source_acquisitions"].values()))
    reference = state["raw_result_refs"][acquisition["snapshot_id"]]
    artifact = output / "artifacts" / reference["storage_key"]
    artifact.write_text("changed retained bytes", encoding="utf-8")
    with pytest.raises(ArtifactFailure):
        load_retained_public_sources(state_path)


def test_duplicate_control_admits_six_results_and_deduplicates(tmp_path_factory):
    # SQLite journals require a short absolute path on Windows.
    tmp_path = tmp_path_factory.mktemp("dup")
    from evidenceforge.evaluation_retained import run_retained_public_evaluation

    sources = tuple(
        TEST_SOURCE.model_copy(
            update={"url": HttpUrl(f"https://www.eia.gov/energyexplained/electricity/{i}/")}
        )
        for i in range(5)
    )
    retained = tmp_path / "retained"
    asyncio.run(replay_public_case(sources, retained))
    state_path = next((retained / "reports").glob("*/state.json"))
    result = asyncio.run(run_retained_public_evaluation(state_path, tmp_path / "evaluation"))
    duplicate = result["cases"]["duplicate_snapshot_control"]
    assert duplicate["input_results"] == 6
    assert duplicate["sources"] == 5
    assert duplicate["run_status"] == "completed"
    assert all(result["checks"].values())
