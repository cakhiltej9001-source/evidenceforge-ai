"""Optional Phase 9 Gemini extension with a separate, explicit paid cap."""

import argparse
import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict, cast

from evidenceforge.config import load_settings
from evidenceforge.evaluation import load_dataset, retrieval_adapter, score
from evidenceforge.evaluation_paid import CountingTransport, OneShotDraft
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

FULL_BUDGET = BudgetLimits(
    max_research_passes=3, max_rewrites=0, max_model_calls=12, max_searches=8
)
FULL_CASE_INDICES = (0, 12)


class ExtensionPlan(TypedDict):
    dataset_sha256: str
    base_calls_reserved: int
    additional_call_cap: int
    missing_one_shot_case_ids: list[str]
    full_agent_case_ids: list[str]
    full_agent_budget: dict[str, Any]
    planned_max_attempts: int
    execution_requires_separate_user_authorization: bool


def extension_plan(dataset_path: Path, base_output: Path, additional_cap: int) -> ExtensionPlan:
    if additional_cap < 1:
        raise ValueError("Additional paid call cap must be positive.")
    dataset, digest = load_dataset(dataset_path)
    base = json.loads((base_output / "paid_results.json").read_text(encoding="utf-8"))
    if base["dataset_sha256"] != digest or base["paid_call_cap"] != 30:
        raise ValueError("Base benchmark identity does not match the frozen Phase 9 dataset.")
    base_ledger = base_output / "global_paid_calls.sqlite"
    if not base_ledger.is_file():
        raise ValueError("Base paid-call ledger is missing.")
    with sqlite3.connect(base_ledger.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        base_calls = int(conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0])
    if base_calls > 30 or base_calls != base["paid_calls_reserved"]:
        raise ValueError("Base paid-call ledger and results do not agree.")
    missing = [
        case.id for case in dataset.cases if base["one_shot"][case.id]["status"] != "completed"
    ]
    return {
        "dataset_sha256": digest,
        "base_calls_reserved": base_calls,
        "additional_call_cap": additional_cap,
        "missing_one_shot_case_ids": missing,
        "full_agent_case_ids": [dataset.cases[i].id for i in FULL_CASE_INDICES],
        "full_agent_budget": FULL_BUDGET.model_dump(mode="json"),
        "planned_max_attempts": len(missing) + len(FULL_CASE_INDICES) * FULL_BUDGET.max_model_calls,
        "execution_requires_separate_user_authorization": True,
    }


async def run_extension(
    dataset_path: Path, base_output: Path, output: Path, additional_cap: int
) -> dict[str, object]:
    if output.resolve() == base_output.resolve():
        raise ValueError("Extension output must differ from the original benchmark.")
    plan = extension_plan(dataset_path, base_output, additional_cap)
    if additional_cap < plan["planned_max_attempts"]:
        raise ValueError("The extension cap cannot fund the planned maximum attempts.")
    dataset, digest = load_dataset(dataset_path)
    settings = load_settings()
    if settings.model_api_key is None or settings.model_id is None:
        raise ValueError("A configured Gemini model and private key are required.")
    base = json.loads((base_output / "paid_results.json").read_text(encoding="utf-8"))
    if settings.model_id != base["model"]:
        raise ValueError("The Gemini model must match the base benchmark.")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "extension_manifest.json"
    manifest = {
        **plan,
        "model": settings.model_id,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "base_results_sha256": hashlib.sha256(
            (base_output / "paid_results.json").read_bytes()
        ).hexdigest(),
        "source_sha256": {
            name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in (
                "evaluation.py",
                "evaluation_paid.py",
                "evaluation_extension.py",
                "models/gemini.py",
                "models/research.py",
                "retrieval/fixtures.py",
                "services/research.py",
                "graph/research.py",
            )
        },
    }
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Extension configuration changed; use a new output directory.")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    guard = CountingTransport(output, digest, settings.model_id, cap=additional_cap)
    result_path = output / "extension_results.json"
    saved = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    if saved and saved.get("dataset_sha256") != digest:
        raise ValueError("Extension results belong to a different dataset.")
    one_shot: dict[str, dict[str, object]] = saved.get("one_shot", {})
    full_agent: dict[str, dict[str, object]] = saved.get("full_agent", {})

    def save() -> None:
        result_path.write_text(
            json.dumps(
                {
                    "dataset_sha256": digest,
                    "model": settings.model_id,
                    "additional_call_cap": additional_cap,
                    "additional_calls_reserved": guard.count(),
                    "base_calls_reserved": plan["base_calls_reserved"],
                    "one_shot": one_shot,
                    "full_agent": full_agent,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    one_shot_budget = BudgetLimits(max_model_calls=additional_cap, max_total_tokens=100_000)
    model = GeminiResearchModel(
        settings.model_id, settings.model_api_key, one_shot_budget, transport=guard
    )
    model.bind_run(
        output / "model_calls",
        "evaluation",
        "extension_" + digest[:24],
        one_shot_budget,
        existing=False,
    )
    cases = {case.id: case for case in dataset.cases}
    for case_id in plan["missing_one_shot_case_ids"]:
        if case_id in one_shot:
            continue
        if guard.count() >= additional_cap:
            one_shot[case_id] = {"status": "missing_call_cap"}
            save()
            continue
        started = perf_counter()
        before = len(model.observations)
        try:
            raw = await model._generate(
                "one_shot_baseline",
                ResearchRequest(question=cases[case_id].question),
                OneShotDraft,
                "List at most three short factual claims or abstain if you cannot answer reliably.",
            )
            answer = OneShotDraft.model_validate(raw)
            observation = model.observations[-1] if len(model.observations) > before else {}
            one_shot[case_id] = {
                "status": "completed",
                "claims": list(answer.claims),
                "abstained": answer.abstained,
                "input_tokens": observation.get("input_tokens"),
                "output_tokens_including_thinking": observation.get(
                    "output_tokens_including_thinking"
                ),
                "total_tokens": observation.get("total_tokens"),
                "latency_seconds": round(perf_counter() - started, 4),
                "cost_usd": None,
            }
        except Exception as exc:
            one_shot[case_id] = {
                "status": "provider_or_schema_failure",
                "error_type": type(exc).__name__,
                "latency_seconds": round(perf_counter() - started, 4),
                "cost_usd": None,
            }
            save()
            return {
                "status": "stopped_after_failure",
                "case_id": case_id,
                "additional_calls_reserved": guard.count(),
            }
        save()

    for case_id in plan["full_agent_case_ids"]:
        if case_id in full_agent:
            continue
        if guard.count() >= additional_cap:
            full_agent[case_id] = {"status": "missing_call_cap"}
            save()
            continue
        case = cases[case_id]
        run_root = output / "full_agent" / case_id
        retrieval = RetrievalService(run_root, {SourceType.WEB: retrieval_adapter(case)})
        full_model = GeminiResearchModel(
            settings.model_id, settings.model_api_key, FULL_BUDGET, transport=guard
        )
        service = ResearchService(run_root, model=full_model, retrieval=retrieval)
        started = perf_counter()
        try:
            state = await service.run(ResearchRequest(question=case.question), FULL_BUDGET)
            row = score(state, case, perf_counter() - started)
        except Exception as exc:
            row = {
                "status": "provider_or_workflow_failure",
                "error_type": type(exc).__name__,
                "latency_seconds": round(perf_counter() - started, 4),
            }
        row.update(
            gemini_paid_calls=len(full_model.observations),
            gemini_input_tokens_known=sum(
                cast(int, o.get("input_tokens") or 0) for o in full_model.observations
            ),
            gemini_output_tokens_known=sum(
                cast(int, o.get("output_tokens_including_thinking") or 0)
                for o in full_model.observations
            ),
            gemini_usage_unknown_calls=sum(
                o.get("total_tokens") is None for o in full_model.observations
            ),
        )
        full_agent[case_id] = row
        save()

    return {
        "status": "finished_with_recorded_outcomes",
        "dataset_sha256": digest,
        "additional_call_cap": additional_cap,
        "additional_calls_reserved": guard.count(),
        "base_calls_reserved": plan["base_calls_reserved"],
        "one_shot_completed": sum(r["status"] == "completed" for r in one_shot.values()),
        "full_agent": {key: value["status"] for key, value in full_agent.items()},
        "cost_usd": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan or execute a separately capped Phase 9 Gemini extension."
    )
    parser.add_argument(
        "--dataset", type=Path, default=Path("docs/evaluation/diverse_dataset.json")
    )
    parser.add_argument(
        "--base-output", type=Path, default=Path(".evidenceforge/evaluation/phase9_diverse")
    )
    parser.add_argument(
        "--output", type=Path, default=Path(".evidenceforge/evaluation/phase9_extension")
    )
    parser.add_argument("--additional-call-cap", type=int, required=True)
    parser.add_argument(
        "--execute", action="store_true", help="Issue paid Gemini calls under the supplied cap."
    )
    args = parser.parse_args()
    result: dict[str, object] | ExtensionPlan
    if args.execute:
        result = asyncio.run(
            run_extension(args.dataset, args.base_output, args.output, args.additional_call_cap)
        )
    else:
        result = extension_plan(args.dataset, args.base_output, args.additional_call_cap)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
