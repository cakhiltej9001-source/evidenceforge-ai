"""CLI for Gemini/local evidence and checkpointed offline research."""

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.evidence.contracts import AnalysisOptions, RankingProfile
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import PlanDraft
from evidenceforge.reporting import render_report
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import (
    ArtifactFailure,
    RetrievalBatch,
)
from evidenceforge.retrieval.fixtures import (
    DisputeFixture,
    FixtureRetrievalAdapter,
    SecondPassFixture,
)
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.storage.checkpoints import CheckpointFailure, CheckpointRepository
from evidenceforge.storage.documents import DocumentFailure


async def execute(
    question: str | None,
    directory: Path | None,
    demo: str | None,
    *,
    owner: str = "local",
    documents: tuple[str, ...] = (),
    resume: str | None = None,
    pause_after: str | None = None,
    ranking_profile: RankingProfile | None = None,
    offline: bool = False,
    live_web: bool = False,
    live_energy: bool = False,
    require_approval: bool = False,
    decision: PlanDecision | None = None,
    edited_plan: PlanDraft | None = None,
    expected_version: int | None = None,
) -> tuple[str, Path, str]:
    if (live_web or live_energy) and (offline or demo is not None):
        raise ConfigurationError("Live sources cannot be combined with --offline or --demo.")
    settings = load_settings()
    data_dir = directory if directory is not None else settings.data_dir
    stored_profile = None
    if resume is not None:
        registration = CheckpointRepository(data_dir / "checkpoints", owner).load(resume)
        stored_profile = json.loads(registration.profile)
    provider = "fixture" if offline else settings.model_provider
    if stored_profile is not None:
        saved_gemini = str(stored_profile["model"]).endswith(".GeminiResearchModel")
        if offline and saved_gemini:
            raise ConfigurationError("A Gemini workflow cannot resume with offline reasoning.")
        provider = "gemini" if saved_gemini else "fixture"
    model = None
    if provider == "gemini":
        if resume is None and not documents and demo is None and not (live_web or live_energy):
            raise ConfigurationError(
                "Gemini requires --document DOCUMENT_ID or an explicit --demo. "
                "Alternatively explicitly enable --live-web or --energy-api."
            )
        if settings.model_api_key is None:
            raise ConfigurationError("Configure the Gemini API key before resuming this workflow.")
        model_id = str(stored_profile["model_id"]) if stored_profile else settings.model_id
        assert model_id is not None
        try:
            model = GeminiResearchModel(model_id, settings.model_api_key, settings.budget)
        except ValueError:
            raise ConfigurationError(
                "Invalid Gemini model ID or unsupported dollar cap; use call and token caps."
            ) from None
    elif provider != "fixture":
        raise ConfigurationError("This research CLI supports fixture or Gemini models.")
    options = ResearchOptions(
        analysis=AnalysisOptions(ranking_profile=ranking_profile or "general"),
        require_plan_approval=require_approval,
        live_web=live_web,
        live_energy=live_energy,
    )
    if resume is not None:
        registration = CheckpointRepository(data_dir / "checkpoints", owner).load(resume)
        profile = json.loads(registration.profile)
        if ranking_profile is None:
            options = ResearchOptions.model_validate(profile["research_options"])
        adapters = profile["adapters"]
        demo = demo or (
            "dispute"
            if any(name.endswith(".DisputeFixture") for name in adapters.values())
            else "second-pass"
            if any(name.endswith(".SecondPassFixture") for name in adapters.values())
            else "empty"
            if profile.get("fixture_empty", {}).get("web")
            else "immediate"
        )
    if offline and (options.live_web or options.live_energy):
        raise ConfigurationError("A saved live-source workflow cannot resume with --offline.")
    retrieval = None
    if not (options.live_web or options.live_energy) and demo in {
        "second-pass",
        "empty",
        "dispute",
    }:
        adapter = (
            DisputeFixture()
            if demo == "dispute"
            else SecondPassFixture()
            if demo == "second-pass"
            else FixtureRetrievalAdapter(RetrievalBatch(results=()))
        )
        retrieval = RetrievalService(data_dir, {SourceType.WEB: adapter})
    service = ResearchService(data_dir, model=model, retrieval=retrieval, options=options)
    if resume is not None:
        if edited_plan is not None:
            if expected_version is None:
                raise ConfigurationError("Plan editing requires the current plan version.")
            state = await service.edit_plan(resume, edited_plan, expected_version, owner)
        else:
            state = await service.resume(resume, owner, decision=decision)
    else:
        if question is None:
            raise ConfigurationError("Supply a research question or --resume THREAD_ID.")
        state = await service.run(
            ResearchRequest(question=question, owner_scope=owner, document_ids=documents),
            settings.budget,
            pause_after=pause_after,
        )
    if state["run_status"] == "running":
        boundary = (
            "awaiting_approval" if state["approval_status"] == "awaiting_approval" else pause_after
        )
        output = (
            f"Workflow paused: {boundary}. SQLite checkpoint saved.\n"
            f"Thread: {state['thread_id']}\nOwner: {owner}\n"
            f"Completed retrieval passes: {state['iteration_count']}\n"
            f"Resume: uv run --locked evidenceforge-research "
            f"--resume {state['thread_id']} --owner {owner}"
        )
        if state["approval_status"] == "awaiting_approval":
            output += "\n\nPlan version: " + str(state["plan_version"])
            for question_record in state["research_questions"]:
                output += "\n- " + str(question_record["question"])
                output += "\n  Criteria: " + json.dumps(question_record["acceptance_criteria"])
            output += (
                f"\nApprove: uv run --locked evidenceforge-research "
                f"--resume {state['thread_id']} --owner {owner} "
                f"--approve-plan {state['plan_version']}"
            )
    else:
        output = render_report(state)
    return output, service.report_path(state), state["run_status"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a cited local-evidence report with bounded research."
    )
    parser.add_argument("question", nargs="?")
    parser.add_argument(
        "--offline", action="store_true", help="Use fixture reasoning without model calls."
    )
    parser.add_argument(
        "--live-web",
        action="store_true",
        help="Use configured Tavily search; consumes search credits.",
    )
    parser.add_argument(
        "--energy-api",
        action="store_true",
        help="Include public GB half-hour generation shares from NESO.",
    )
    parser.add_argument("--owner", default="local")
    parser.add_argument("--document", action="append", default=[])
    parser.add_argument("--resume")
    parser.add_argument("--require-approval", action="store_true")
    parser.add_argument("--edit-plan", type=Path, metavar="PLAN_JSON")
    parser.add_argument("--plan-version", type=int)
    decisions = parser.add_mutually_exclusive_group()
    decisions.add_argument("--approve-plan", type=int, metavar="VERSION")
    decisions.add_argument("--reject-plan", type=int, metavar="VERSION")
    parser.add_argument("--cancel", metavar="THREAD_ID")
    parser.add_argument(
        "--pause-after", choices=("query_generator", "source_processor", "evidence_extractor")
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument(
        "--demo", choices=("immediate", "second-pass", "empty", "dispute"), default=None
    )
    parser.add_argument("--ranking-profile", choices=("general", "current", "historical"))
    args = parser.parse_args()
    if (args.approve_plan is not None or args.reject_plan is not None) and not args.resume:
        parser.error("Plan decisions require --resume THREAD_ID.")
    if args.edit_plan and (not args.resume or args.plan_version is None):
        parser.error("--edit-plan requires --resume THREAD_ID and --plan-version VERSION.")
    if args.edit_plan and (args.approve_plan is not None or args.reject_plan is not None):
        parser.error("Save the edited plan before approving or rejecting its new version.")
    if args.require_approval and args.resume:
        parser.error("--require-approval is set when starting a new run.")
    if args.cancel:
        if args.question or args.document or args.pause_after or args.resume or args.demo:
            parser.error("--cancel uses only THREAD_ID, --owner and --data-dir.")
        try:
            settings = load_settings()
            ResearchService(args.data_dir or settings.data_dir).cancel(args.cancel, args.owner)
        except (ConfigurationError, CheckpointFailure, OSError, sqlite3.Error) as exc:
            print(str(exc))
            return 1
        print(
            f"Cancellation requested for thread {args.cancel}. Resume a paused run to finalize it."
        )
        return 0
    if args.resume and (args.question or args.document or args.pause_after):
        parser.error(
            "--resume uses the stored request; omit question, --document and --pause-after."
        )
    if args.document and args.demo is not None:
        parser.error("--document uses local document retrieval; omit --demo.")
    try:
        edited_plan = None
        if args.edit_plan:
            if args.edit_plan.stat().st_size > 100_000:
                raise ConfigurationError("Edited plan file exceeds the size allowance.")
            edited_plan = PlanDraft.model_validate_json(args.edit_plan.read_text(encoding="utf-8"))
        markdown, path, status = asyncio.run(
            execute(
                args.question,
                args.data_dir,
                args.demo,
                owner=args.owner,
                documents=tuple(args.document),
                resume=args.resume,
                pause_after=args.pause_after,
                ranking_profile=args.ranking_profile,
                offline=args.offline,
                live_web=args.live_web,
                live_energy=args.energy_api,
                require_approval=args.require_approval,
                edited_plan=edited_plan,
                expected_version=args.plan_version,
                decision=PlanDecision(
                    approved=args.approve_plan is not None,
                    plan_version=args.approve_plan or args.reject_plan,
                )
                if args.approve_plan is not None or args.reject_plan is not None
                else None,
            )
        )
    except (ConfigurationError, CheckpointFailure, DocumentFailure) as exc:
        print(str(exc))
        return 1
    except (ValidationError, ArtifactFailure, OSError, sqlite3.Error):
        print(
            "Research configuration or local report storage failed; "
            "successful delivery is unconfirmed."
        )
        return 1
    print(markdown)
    if status != "running":
        print(f"Saved report: {path.resolve()}")
        print(f"Saved JSON report: {path.with_name('report.json').resolve()}")
        print(f"Saved state: {path.with_name('state.json').resolve()}")
        print(f"Saved graph: {path.with_name('graph.json').resolve()}")
        print(f"Saved audit: {path.with_name('audit.json').resolve()}")
        print(f"Saved inspection: {path.with_name('inspection.md').resolve()}")
        print(f"Saved usage: {path.with_name('usage.json').resolve()}")
        print(f"Saved progress: {path.with_name('progress.json').resolve()}")
        print(f"Saved trace coverage: {path.with_name('trace_coverage.json').resolve()}")
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
