"""Remote receipt proof and redaction without any external requests."""

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from evidenceforge.schemas import ResearchRequest
from evidenceforge.services.observability import LangSmithTraceSink, PublicProgress
from evidenceforge.services.research import ResearchService
from evidenceforge.trace_verification import verify_trace_export


class ReceiptClient:
    def __init__(self):
        self.runs = {}
        self.project_id = uuid4()
        self.read_ids = []
        self.corrupt = False
        self.fail = False

    def create_run(self, **kwargs):
        self.runs[kwargs["id"]] = kwargs

    def read_project(self, *, project_name):
        return SimpleNamespace(id=self.project_id)

    def read_run(self, run_id, **kwargs):
        self.read_ids.append(run_id)
        if self.fail:
            raise RuntimeError("private server failure")
        row = dict(self.runs[run_id])
        row.pop("project_name")
        row["session_id"] = self.project_id
        if self.corrupt:
            row["outputs"] = {"private": "SENTINEL"}
        return SimpleNamespace(**row)


PROGRESS = PublicProgress("completed", "sufficient", 1, 0, 1, 2, 0, 2)


def test_receipt_requires_exact_completed_span_and_project():
    client = ReceiptClient()
    sink = LangSmithTraceSink(client, "test-project")
    sink.emit("final", PROGRESS)
    row = next(iter(client.runs.values()))
    assert row["inputs"] == {}
    assert row["outputs"] == PROGRESS.as_dict()
    assert row["end_time"] == row["start_time"]
    client.corrupt = True
    assert sink.verify_delivery()["remote_delivery_verified"] is False
    client.corrupt = False
    assert sink.verify_delivery()["remote_delivery_verified"] is True
    assert set(client.read_ids) == set(client.runs)


def test_receipt_failure_omission_and_bounds_are_honest():
    client = ReceiptClient()
    sink = LangSmithTraceSink(client, "test", max_receipts=1)
    sink.emit("audit", PROGRESS)
    client.fail = True
    result = sink.verify_delivery()
    assert result["unverified_receipts"] == 1
    assert "private" not in json.dumps(result)
    client.fail = False
    sink.emit("final", PROGRESS)
    result = sink.verify_delivery()
    assert result["verified_receipts"] == 1
    assert result["omitted_receipts"] == 1
    assert result["remote_delivery_verified"] is False


@pytest.mark.parametrize(
    "progress",
    [
        replace(PROGRESS, run_status="SENTINEL"),
        replace(PROGRESS, stop_reason="SENTINEL"),
        replace(PROGRESS, evidence_count=-1),
        replace(PROGRESS, evidence_count=True),
    ],
)
def test_counter_export_rejects_nonallowlisted_data(progress):
    client = ReceiptClient()
    with pytest.raises(ValueError):
        LangSmithTraceSink(client, "test").emit("final", progress)
    assert client.runs == {}


def test_service_reports_actual_readback_and_omits_request(tmp_path):
    client = ReceiptClient()
    sink = LangSmithTraceSink(client, "test")
    service = ResearchService(tmp_path, trace_sink=sink)
    state = asyncio.run(
        service.run(ResearchRequest(question="Compare solar and wind electricity output. SENTINEL"))
    )
    result = json.loads(service.report_path(state).with_name("trace_coverage.json").read_text())
    assert result["remote_delivery_verified"] is True
    assert result["verified_receipts"] == result["local_emissions"]["accepted_by_sink"]
    assert "SENTINEL" not in json.dumps(list(client.runs.values()), default=str)


def test_probe_without_credentials_does_not_create_client(tmp_path, monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setattr(
        LangSmithTraceSink,
        "from_api_key",
        lambda *a, **k: pytest.fail("No remote client without explicit credentials."),
    )
    result = verify_trace_export(execute=True, env_file=tmp_path / "missing.env")
    assert result["status"] == "credentials_missing"
    assert result["provider_calls"] == 0


def test_probe_requires_execute_and_uses_fixed_synthetic_payload(tmp_path, monkeypatch):
    client = ReceiptClient()
    sink = LangSmithTraceSink(client, "synthetic")
    monkeypatch.setenv("LANGSMITH_API_KEY", "PRIVATE_KEY_SENTINEL")
    created = []

    def factory(key, project):
        created.append(project)
        return sink

    monkeypatch.setattr(LangSmithTraceSink, "from_api_key", factory)
    dry = verify_trace_export(env_file=tmp_path / "missing.env")
    assert dry["status"] == "ready_requires_execute"
    assert not created
    live = verify_trace_export(execute=True, env_file=tmp_path / "missing.env")
    assert live["remote_delivery_verified"] is True
    assert created == ["evidenceforge-synthetic-verification"]
    assert len(client.runs) == 1
    assert "PRIVATE_KEY_SENTINEL" not in json.dumps(live)
    assert "PRIVATE_KEY_SENTINEL" not in json.dumps(list(client.runs.values()), default=str)


def test_langsmith_private_dotenv_is_accepted_redacted_and_never_enables_export(
    tmp_path, monkeypatch
):
    from evidenceforge.config import load_settings

    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", "fixture")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    env_file = tmp_path / "private.env"
    env_file.write_text(
        "LANGSMITH_API_KEY=KEY_SENTINEL\n"
        "LANGSMITH_PROJECT=PRIVATE_PROJECT_SENTINEL\n"
        "LANGSMITH_ENDPOINT=https://api.smith.langchain.com\n"
        "LANGSMITH_TRACING=true\n",
        encoding="utf-8",
    )
    settings = load_settings(env_file)
    assert settings.langsmith_api_key.get_secret_value() == "KEY_SENTINEL"
    assert settings.langsmith_tracing is True
    assert settings.tracing_enabled is False
    assert "KEY_SENTINEL" not in settings.model_dump_json()
    assert "KEY_SENTINEL" not in repr(settings)
    assert "PRIVATE_PROJECT_SENTINEL" not in settings.model_dump_json()


def test_export_ignores_extra_attributes_and_overridden_serialization():
    class InjectedProgress(PublicProgress):
        def as_dict(self):
            return {"question": "PRIVATE_SENTINEL", "unapproved_counter": 1}

    progress = InjectedProgress(**PROGRESS.as_dict())
    object.__setattr__(progress, "source_text", "PRIVATE_SENTINEL")
    client = ReceiptClient()
    LangSmithTraceSink(client, "test").emit("final", progress)
    row = next(iter(client.runs.values()))
    assert row["outputs"] == PROGRESS.as_dict()
    assert "PRIVATE_SENTINEL" not in json.dumps(row, default=str)


def test_explicit_trace_client_overrides_environment_sampling(monkeypatch):
    import langsmith

    monkeypatch.setenv("LANGSMITH_TRACING_SAMPLING_RATE", "0")
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return ReceiptClient()

    monkeypatch.setattr(langsmith, "Client", factory)
    sink = LangSmithTraceSink.from_api_key("test-key", "test-project")
    sink.emit("final", PROGRESS)
    assert captured["tracing_sampling_rate"] == 1.0
    assert sink.verify_delivery()["remote_delivery_verified"] is True
