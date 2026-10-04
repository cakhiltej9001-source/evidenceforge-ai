"""Public synthetic records. Default checks cannot connect to the network."""

import hashlib
import os
import socket
from contextvars import ContextVar

import pytest

from evidenceforge.graph.state import apply_update, initial_state
from evidenceforge.schemas import (
    ArtifactReference,
    EvidenceItem,
    EvidenceLocator,
    ResearchQuestion,
    ResearchRequest,
    SearchQuery,
    SourceAcquisition,
    SourceRecord,
)


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("EVIDENCEFORGE_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    # Test defaults override private .env values in the current project directory.
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", "fixture")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_ID", "")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_API_KEY", "")
    monkeypatch.setenv("EVIDENCEFORGE_TAVILY_API_KEY", "")

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests must not make network calls")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    # Windows asyncio creates its self-pipe with the stdlib socketpair fallback.
    # Permit connect only inside that synchronous routine, on this execution context.
    # Other loopback and external connections remain blocked, including other threads.
    pair_setup = ContextVar("offline_socketpair_setup", default=False)
    original_pair, original_connect = socket.socketpair, socket.socket.connect

    def internal_socketpair(*args, **kwargs):
        token = pair_setup.set(True)
        try:
            return original_pair(*args, **kwargs)
        finally:
            pair_setup.reset(token)

    def guarded_connect(sock, address):
        if pair_setup.get():
            return original_connect(sock, address)
        return forbidden(sock, address)

    monkeypatch.setattr(socket, "socketpair", internal_socketpair)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def populated_state():
    question = ResearchQuestion(
        id="q_1", question="What does the fixture say?", acceptance_criteria=("Exact support",)
    )
    query = SearchQuery(
        id="query_1",
        question_ids=("q_1",),
        text="fixture facts",
        source_type="web",
        research_pass=1,
    )
    passage = "  Synthetic evidence: café.\n"
    digest = hashlib.sha256(passage.encode()).hexdigest()
    artifact = ArtifactReference(
        id="snapshot_1",
        content_hash=digest,
        storage_key="snapshots/public.txt",
        parser_version="fixture_1",
        byte_count=len(passage.encode()),
    )
    source = SourceRecord(
        id="source_1",
        title="Public fixture",
        source_type="web",
        provider="fixture",
        content_hash=digest,
        url="https://example.org/fixture",
    )
    acquisition = SourceAcquisition(
        id="acquisition_1",
        source_id=source.id,
        query_id=query.id,
        snapshot_id=artifact.id,
        retrieved_at="2026-09-30T00:00:00Z",
        content_scope="full_text",
    )
    evidence = EvidenceItem(
        id="evidence_1",
        source_id=source.id,
        owner_scope="local",
        acquisition_ids=(acquisition.id,),
        question_ids=(question.id,),
        passage=passage,
        locator=EvidenceLocator(snapshot_id=artifact.id, start_offset=0, end_offset=len(passage)),
        relevance=0.9,
        relevance_rationale="Direct synthetic support",
    )

    def data(record):
        return record.model_dump(mode="json")

    return apply_update(
        initial_state(ResearchRequest(question=question.question)),
        {
            "research_questions": [data(question)],
            "plan_version": 1,
            "search_queries": [data(query)],
            "query_records": {query.id: data(query)},
            "raw_result_refs": {artifact.id: data(artifact)},
            "source_records": {source.id: data(source)},
            "source_acquisitions": {acquisition.id: data(acquisition)},
            "evidence_store": {evidence.id: data(evidence)},
        },
    )
