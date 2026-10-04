"""Capped live one-shot benchmark and two matched full-agent probes."""

import argparse
import asyncio
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from time import perf_counter

import httpx
from pydantic import Field, StrictBool

from evidenceforge.config import load_settings
from evidenceforge.evaluation import load_dataset, retrieval_adapter, score
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.schemas import BudgetLimits, Contract, ResearchRequest, SourceType, Text
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

PAID_CALL_CAP = 30


class OneShotDraft(Contract):
    claims: tuple[Text, ...] = Field(max_length=8)
    abstained: StrictBool


class CountingTransport(httpx.AsyncBaseTransport):
    def __init__(
        self, root: Path, dataset_hash: str, model: str, *, cap: int = PAID_CALL_CAP
    ) -> None:
        if cap < 1:
            raise ValueError("Paid call cap must be positive.")
        self.cap = cap
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "global_paid_calls.sqlite"
        identity = json.dumps(
            {"dataset_sha256": dataset_hash, "model": model, "cap": self.cap, "version": 1},
            sort_keys=True,
        )
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (identity TEXT NOT NULL)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, status TEXT NOT NULL)"
            )
            row = conn.execute("SELECT identity FROM metadata").fetchone()
            if row is None:
                conn.execute("INSERT INTO metadata VALUES (?)", (identity,))
            elif row[0] != identity:
                raise ValueError(
                    "Paid benchmark identity or limit changed; use a new output directory."
                )

    def count(self) -> int:
        with closing(sqlite3.connect(self.path)) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0])

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != "generativelanguage.googleapis.com":
            raise httpx.TransportError("Benchmark provider host is not allowed.")
        identifier = hashlib.sha256(bytes(request.content)).hexdigest()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM calls WHERE id=?", (identifier,)).fetchone():
                raise httpx.TransportError(
                    "This paid request is already reserved; replay is blocked."
                )
            if conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0] >= self.cap:
                raise httpx.TransportError("Paid benchmark call cap reached.")
            conn.execute("INSERT INTO calls VALUES (?,?)", (identifier, "unconfirmed"))
        status = "unconfirmed"
        try:
            async with httpx.AsyncHTTPTransport() as upstream:
                response = await upstream.handle_async_request(request)
                raw_content = b"".join([chunk async for chunk in response.aiter_raw()])
                status = "http_" + str(response.status_code)
                return httpx.Response(
                    response.status_code,
                    headers=response.headers,
                    content=raw_content,
                    request=request,
                )
        finally:
            with closing(sqlite3.connect(self.path)) as conn, conn:
                conn.execute("UPDATE calls SET status=? WHERE id=?", (status, identifier))


async def run_paid(dataset_path: Path, output: Path) -> dict[str, object]:
    dataset, digest = load_dataset(dataset_path)
    settings = load_settings()
    if settings.model_api_key is None or settings.model_id is None:
        raise ValueError("A configured Gemini model and private key are required.")
    guard = CountingTransport(output, digest, settings.model_id)
    one_shot_budget = BudgetLimits(max_model_calls=PAID_CALL_CAP, max_total_tokens=100_000)
    one_shot = GeminiResearchModel(
        settings.model_id,
        settings.model_api_key,
        one_shot_budget,
        transport=guard,
    )
    one_shot.bind_run(
        output / "model_calls",
        "evaluation",
        "benchmark_v2_" + digest[:24],
        one_shot_budget,
        existing=False,
    )
    result_path = output / "paid_results.json"
    saved = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    if saved and saved.get("dataset_sha256") != digest:
        raise ValueError("Paid results belong to a different frozen dataset.")
    rows: dict[str, dict[str, object]] = saved.get("one_shot", {})
    full_rows: dict[str, dict[str, object]] = saved.get("matched_full_agent", {})

    def save() -> None:
        result_path.write_text(
            json.dumps(
                {
                    "dataset_sha256": digest,
                    "model": settings.model_id,
                    "paid_call_cap": PAID_CALL_CAP,
                    "paid_calls_reserved": guard.count(),
                    "one_shot": rows,
                    "matched_full_agent": full_rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    for case in dataset.cases:
        if case.id in rows:
            continue
        if guard.count() >= PAID_CALL_CAP:
            rows[case.id] = {"status": "missing_call_cap"}
            save()
            continue
        started = perf_counter()
        observations_before = len(one_shot.observations)
        try:
            raw = await one_shot._generate(
                "one_shot_baseline",
                ResearchRequest(question=case.question),
                OneShotDraft,
                "List at most three short factual claims or abstain if you cannot answer reliably.",
            )
            answer = OneShotDraft.model_validate(raw)
            observation = (
                one_shot.observations[-1]
                if len(one_shot.observations) > observations_before
                else {}
            )
            rows[case.id] = {
                "status": "completed",
                "claims": list(answer.claims),
                "abstained": answer.abstained,
                "citation_precision": None,
                "citation_coverage": None,
                "groundedness": None,
                "required_aspect_coverage": None,
                "input_tokens": observation.get("input_tokens"),
                "output_tokens_including_thinking": observation.get(
                    "output_tokens_including_thinking"
                ),
                "total_tokens": observation.get("total_tokens"),
                "latency_seconds": round(perf_counter() - started, 4),
                "cost_usd": None,
            }
        except Exception as exc:
            # Record only the exception class; provider contents and credentials stay private.
            rows[case.id] = {
                "status": "provider_or_schema_failure",
                "claims": [],
                "error_type": type(exc).__name__,
                "latency_seconds": round(perf_counter() - started, 4),
                "input_tokens": None,
                "output_tokens_including_thinking": None,
                "total_tokens": None,
                "cost_usd": None,
            }
            save()
            return {
                "status": "stopped_after_first_new_failure",
                "dataset_sha256": digest,
                "model": settings.model_id,
                "paid_call_cap": PAID_CALL_CAP,
                "paid_calls_reserved": guard.count(),
                "failed_case": case.id,
                "error_type": type(exc).__name__,
                "latency_seconds": round(perf_counter() - started, 4),
                "input_tokens": None,
                "output_tokens_including_thinking": None,
                "total_tokens": None,
                "cost_usd": None,
            }
        save()

    for case in (dataset.cases[0], dataset.cases[12]):
        if case.id in full_rows:
            continue
        if guard.count() >= PAID_CALL_CAP:
            full_rows[case.id] = {"status": "missing_call_cap"}
            save()
            continue
        run_root = output / "matched_full" / case.id
        retrieval = RetrievalService(run_root, {SourceType.WEB: retrieval_adapter(case)})
        budget = BudgetLimits(
            max_subquestions=1, max_research_passes=2, max_rewrites=0, max_model_calls=8
        )
        model = GeminiResearchModel(
            settings.model_id, settings.model_api_key, budget, transport=guard
        )
        service = ResearchService(run_root, model=model, retrieval=retrieval)
        try:
            started = perf_counter()
            state = await service.run(ResearchRequest(question=case.question), budget)
            full_rows[case.id] = score(state, case, perf_counter() - started)
        except Exception:
            full_rows[case.id] = {"status": "provider_or_workflow_failure"}
        save()

    return {
        "dataset_sha256": digest,
        "model": settings.model_id,
        "paid_call_cap": PAID_CALL_CAP,
        "paid_calls_reserved": guard.count(),
        "one_shot_completed": sum(r["status"] == "completed" for r in rows.values()),
        "one_shot_missing_or_failed": sum(r["status"] != "completed" for r in rows.values()),
        "matched_full_agent": {key: value["status"] for key, value in full_rows.items()},
        "cost_usd": None,
        "annotation_status": dataset.annotation_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the capped Gemini evaluation sample.")
    parser.add_argument(
        "--dataset", type=Path, default=Path("docs/evaluation/diverse_dataset.json")
    )
    parser.add_argument("--output", type=Path, default=Path(".evidenceforge/evaluation/phase9"))
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_paid(args.dataset, args.output)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
