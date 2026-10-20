"""Bounded structured assessment, drafting, criticism and quote verification."""

import asyncio
import re
from collections.abc import Awaitable
from typing import TypeVar, cast

from pydantic import JsonValue, ValidationError

from evidenceforge.evidence.deduplication import WorkingEvidence, working_evidence
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, blocked_model_patch, checked_patch, record_data
from evidenceforge.nodes.quality_common import quality_error, quality_event
from evidenceforge.planning import (
    ModelBudgetExceeded,
    ModelUnavailable,
    PlanningContractError,
    parse_response,
)
from evidenceforge.presentation import display_issues
from evidenceforge.research import (
    CompactQuoteSelectionModel,
    ConstrainedQuoteSelectionModel,
    CoverageAssessment,
    CoverageInput,
    CriticAssessment,
    CriticInput,
    DraftClaim,
    QuoteCriticModel,
    QuoteSelectionDraft,
    QuoteSelectionModel,
    ReportDraft,
    ResearchModel,
    ResearchOptions,
    SynthesisInput,
)
from evidenceforge.retrieval.contracts import ArtifactFailure
from evidenceforge.schemas import (
    CitationAuditItem,
    Claim,
    ClaimEvidenceLink,
    Contract,
    CriticVerdict,
    QuestionCoverage,
    QuestionCoverageStatus,
    Relationship,
    Report,
    ReportSection,
    ResearchGap,
    SourceType,
    SupportVerdict,
    utc_now,
)
from evidenceforge.storage.artifacts import ArtifactStore

T = TypeVar("T", bound=Contract)


def quality_remaining(s: StateSnapshot) -> int:
    return s.budget.max_model_calls - s.quality_attempts - s.planning_attempts


def research_stop(s: StateSnapshot) -> str | None:
    if s.stage_error:
        return s.stop_reason.value if s.stop_reason else "fatal_error"
    if s.coverage_status == "sufficient":
        return "sufficient"
    if (utc_now() - s.started_at).total_seconds() >= s.budget.max_elapsed_seconds:
        return "time_limit"
    if s.iteration_count >= s.budget.max_research_passes:
        return "pass_limit"
    searches = sum(r.searches for r in s.reservations.values() if r.status != "released")
    if searches >= s.budget.max_searches:
        return "search_limit"
    if (
        len(s.evidence_store) >= s.budget.max_evidence_count
        or sum(len(e.passage.encode()) for e in s.evidence_store.values())
        >= s.budget.max_evidence_bytes
    ):
        return "evidence_limit"
    if s.no_progress_count >= 2:
        return "no_progress"
    if quality_remaining(s) <= max(2, s.budget.reserved_quality_calls):
        return "model_call_limit"
    return None


class QualityNode:
    def __init__(self, model: ResearchModel, options: ResearchOptions) -> None:
        self.model = model
        self.options = options

    def working(self, s: StateSnapshot, *, ranked: bool = False) -> WorkingEvidence:
        scores = {sid: ranking.score for sid, ranking in s.source_quality.items()} if ranked else {}
        evidence = [
            item
            for item in s.evidence_store.values()
            if self.options.production_policy_version < 6
            or not display_issues(
                item.passage, year=s.started_at.year, request=s.request.question, editorial=False
            )
        ]
        if self.options.quality_input_version == 1:
            if ranked:
                evidence.sort(key=lambda item: (-scores.get(item.source_id, 0.5), item.id))
            return WorkingEvidence(evidence=tuple(evidence), duplicates=())
        return working_evidence(evidence, scores)

    async def response(self, task: Awaitable[object], schema: type[T]) -> T:
        payload = await asyncio.wait_for(task, self.options.node_timeout_seconds)
        return parse_response(payload, schema, self.options.max_response_bytes)

    def failure(self, state: ResearchState, role: str, exc: Exception) -> Update:
        if isinstance(exc, ModelBudgetExceeded):
            return blocked_model_patch(
                state,
                role,
                exc.reason,
                quality_error(state, role, "budget", state["quality_attempts"] + 1),
            )
        category = (
            "timeout"
            if isinstance(exc, TimeoutError)
            else ("provider" if isinstance(exc, ModelUnavailable) else "schema")
        )
        return quality_error(state, role, category, state["quality_attempts"] + 1)


class CoverageEvaluator(QualityNode):
    async def __call__(self, state: ResearchState) -> Update:
        s = StateSnapshot.model_validate(state)
        if s.run_status != "running":
            return {}
        if s.last_coverage_pass == s.iteration_count:
            return checked_patch(state, {"stop_reason": "no_progress"})
        if quality_remaining(s) <= 2:
            return quality_error(state, "coverage", "budget", s.quality_attempts)
        try:
            working = self.working(s)
            result = await self.response(
                self.model.evaluate_coverage(
                    CoverageInput(
                        questions=s.research_questions,
                        evidence=working.evidence,
                        duplicate_evidence=working.duplicates,
                    )
                ),
                CoverageAssessment,
            )
            known = {q.id: q for q in s.research_questions}
            if len(result.questions) != len(known) or {
                q.question_id for q in result.questions
            } != set(known):
                raise PlanningContractError("coverage question mismatch")
            coverage = {}
            gaps = []
            signature = []
            for assessment in result.questions:
                q = known[assessment.question_id]
                indices = set()
                missing_percent_indices = set()
                evidence_ids: set[str] = set()
                for criterion in assessment.criteria:
                    if criterion.index in indices or criterion.index >= len(q.acceptance_criteria):
                        raise PlanningContractError("invalid criterion")
                    for eid in criterion.evidence_ids:
                        if (
                            eid not in s.evidence_store
                            or q.id not in s.evidence_store[eid].question_ids
                        ):
                            raise PlanningContractError("invalid coverage evidence")
                    criterion_text = q.acceptance_criteria[criterion.index]
                    requires_number = re.search(r"\bpercent(?:age|ages|s)?\b", criterion_text, re.I)
                    asks_for_absence = re.search(
                        r"\b(?:missing|unavailable|absent|unreported|not provided|not reported)\b",
                        criterion_text,
                        re.I,
                    )
                    has_percentage = any(
                        re.search(
                            r"\d+(?:\.\d+)?\s*(?:%|\bpercent\b)",
                            s.evidence_store[eid].passage,
                            re.I,
                        )
                        for eid in criterion.evidence_ids
                    )
                    if (
                        self.options.quality_input_version == 2
                        and requires_number
                        and not asks_for_absence
                        and not has_percentage
                    ):
                        missing_percent_indices.add(criterion.index)
                        continue
                    indices.add(criterion.index)
                    evidence_ids.update(criterion.evidence_ids)
                    signature.append(
                        [
                            q.id,
                            criterion.index,
                            sorted(
                                {
                                    stable_id(
                                        "retained_text",
                                        " ".join(s.evidence_store[eid].passage.casefold().split()),
                                    )
                                    for eid in criterion.evidence_ids
                                }
                            ),
                        ]
                    )
                complete = len(indices) == len(q.acceptance_criteria)
                status = "sufficient" if complete else "partial" if indices else "missing"
                coverage[q.id] = record_data(
                    QuestionCoverage(
                        question_id=q.id,
                        status=QuestionCoverageStatus(status),
                        evidence_ids=tuple(sorted(evidence_ids)),
                        rationale=(
                            f"Structured assessment supported {len(indices)} of "
                            f"{len(q.acceptance_criteria)} criteria; "
                            "source truth is not independently verified."
                        ),
                    )
                )
                for index, text in enumerate(q.acceptance_criteria):
                    if index not in indices:
                        missing = (
                            "Numeric percentages are absent from linked retained evidence for: "
                            + text
                            if index in missing_percent_indices
                            else text
                        )
                        gaps.append(
                            record_data(
                                ResearchGap(
                                    id=stable_id("gap", q.id, index),
                                    question_id=q.id,
                                    missing_aspect=missing,
                                    needed_source_types=(SourceType.WEB,),
                                    recommended_query=(
                                        f"{text} supporting evidence "
                                        f"research pass {s.iteration_count + 1}"
                                    ),
                                )
                            )
                        )
            # Numeric disputes override lexical sufficiency and share search limits.
            dispute_gaps = []
            for qid in sorted(known):
                conflicts = [
                    c
                    for c in s.comparisons.values()
                    if c.relationship == "contradicts" and qid in c.question_ids
                ]
                if not conflicts and not s.analysis_limited:
                    continue
                existing = QuestionCoverage.model_validate(coverage[qid])
                coverage[qid] = record_data(
                    QuestionCoverage(
                        question_id=qid,
                        status=QuestionCoverageStatus.DISPUTED
                        if conflicts
                        else QuestionCoverageStatus.PARTIAL,
                        evidence_ids=existing.evidence_ids,
                        rationale="Unresolved comparable numeric disagreement."
                        if conflicts
                        else "Comparison coverage is incomplete after reaching an analysis cap.",
                    )
                )
                if conflicts:
                    c = sorted(conflicts, key=lambda c: c.id)[0]
                    p = s.propositions[c.left_id]
                    scope = (
                        f"{p.entity} {p.metric} in {p.timeframe} "
                        f"for {p.population} under {p.conditions}"
                    )
                    aspect = (
                        f"Reconcile retained values {c.normalized_left} versus "
                        f"{c.normalized_right} {c.canonical_unit}: {scope}"
                    )
                else:
                    scope = known[qid].question
                    aspect = "Incomplete numeric comparison coverage: " + scope
                source_types = tuple(
                    sorted(
                        {source.source_type for source in s.source_records.values()},
                        key=lambda k: k.value,
                    )
                ) or (SourceType.WEB,)
                for purpose, prefix in (
                    ("primary_source", "Find primary-source measurements and definitions for "),
                    ("counter_evidence", "Find counter-evidence or corrections that reconcile "),
                ):
                    dispute_gaps.append(
                        record_data(
                            ResearchGap(
                                id=stable_id("gap", qid, purpose, scope),
                                question_id=qid,
                                purpose=purpose,
                                missing_aspect=aspect,
                                needed_source_types=source_types,
                                recommended_query=prefix + scope,
                            )
                        )
                    )
            gaps = dispute_gaps + gaps
            signature.append(["analysis", s.analysis_signature or "none"])
            digest = stable_id("coverage", cast(JsonValue, sorted(signature)))
            return checked_patch(
                state,
                {
                    "coverage_by_question": coverage,
                    "coverage_status": "missing" if gaps else "sufficient",
                    "gaps": gaps,
                    "coverage_signature": digest,
                    "last_coverage_pass": s.iteration_count,
                    "no_progress_count": s.no_progress_count + 1
                    if digest == s.coverage_signature
                    else 0,
                    "quality_attempts": s.quality_attempts + 1,
                    **quality_event(
                        state,
                        "coverage",
                        "Assessed question acceptance criteria against retained evidence.",
                    ),
                },
            )
        except (ValidationError, PlanningContractError, TimeoutError, ModelUnavailable) as exc:
            return self.failure(state, "coverage", exc)


class Synthesis(QualityNode):
    async def __call__(self, state: ResearchState) -> Update:
        s = StateSnapshot.model_validate(state)
        if quality_remaining(s) <= 0:
            return quality_error(state, "synthesis", "budget", s.quality_attempts)
        try:
            version = s.revision_count + 1
            working = self.working(s, ranked=True)
            request = SynthesisInput(
                reference_date=s.started_at.date()
                if self.options.production_policy_version >= 5
                else None,
                request=s.request,
                questions=s.research_questions,
                evidence=working.evidence,
                duplicate_evidence=working.duplicates,
                source_quality=tuple(s.source_quality.values()),
                propositions=tuple(s.propositions.values()),
                comparisons=tuple(s.comparisons.values()),
                gaps=s.gaps,
                revision_brief=s.revision_brief,
                draft_version=version,
            )
            if (
                self.options.quality_input_version == 2
                and self.options.quote_selection_version in (1, 2, 3, 4, 5, 6)
                and isinstance(self.model, QuoteSelectionModel)
            ):
                selection = await self.response(
                    self.model.select_quotes_compact(request)
                    if self.options.quote_selection_version >= 4
                    and isinstance(self.model, CompactQuoteSelectionModel)
                    else self.model.select_quotes_constrained(request)
                    if self.options.quote_selection_version >= 3
                    and isinstance(self.model, ConstrainedQuoteSelectionModel)
                    else self.model.select_quotes(request),
                    QuoteSelectionDraft,
                )
                supplied = {item.id: item for item in working.evidence}
                known_questions = {question.id for question in s.research_questions}
                projected = []
                seen_selected = set()
                for selected_quote in selection.claims:
                    item = supplied.get(selected_quote.evidence_id)
                    if (
                        item is None
                        or not set(selected_quote.question_ids).issubset(known_questions)
                        or not set(selected_quote.question_ids).issubset(item.question_ids)
                    ):
                        raise PlanningContractError("invalid selected quote reference")
                    selected_key = (
                        selected_quote.evidence_id,
                        tuple(sorted(selected_quote.question_ids)),
                    )
                    if self.options.quote_selection_version >= 2 and selected_key in seen_selected:
                        continue
                    seen_selected.add(selected_key)
                    projected.append(
                        DraftClaim(
                            statement=item.passage,
                            question_ids=selected_quote.question_ids,
                            evidence_ids=(item.id,),
                            section=selected_quote.section,
                        )
                    )
                result = ReportDraft(claims=tuple(projected))
            else:
                result = await self.response(self.model.synthesize(request), ReportDraft)
            claims = {}
            placed: dict[str, list[str]] = {"summary": [], "key_findings": []}
            sources: set[str] = set()
            questions = {q.id for q in s.research_questions}
            for index, draft in enumerate(result.claims):
                if not set(draft.question_ids).issubset(questions) or not set(
                    draft.evidence_ids
                ).issubset(s.evidence_store):
                    raise PlanningContractError("unknown draft reference")
                evidence_ids = set(draft.evidence_ids)
                # Add only independently auditable exact-copy occurrences. Containment
                # alone never licenses citing a source missing the full quotation.
                for item in (
                    s.evidence_store.values() if self.options.quality_input_version == 2 else ()
                ):
                    if (
                        any(
                            s.evidence_store[eid].passage == item.passage
                            for eid in draft.evidence_ids
                        )
                        and draft.statement == item.passage
                        and set(draft.question_ids).issubset(item.question_ids)
                    ):
                        evidence_ids.add(item.id)
                claim = Claim(
                    id=stable_id("claim", s.run_id, version, index),
                    **draft.model_dump(exclude={"section", "evidence_ids"}),
                    evidence_ids=tuple(sorted(evidence_ids)),
                )
                claims[claim.id] = record_data(claim)
                placed.setdefault(draft.section, []).append(claim.id)
                sources.update(s.evidence_store[eid].source_id for eid in claim.evidence_ids)
            if self.options.quality_input_version == 1:
                if not placed["summary"]:
                    placed["summary"] = [next(iter(claims))]
            else:
                if not placed["key_findings"]:
                    placed["key_findings"] = [
                        cid for cid, claim in claims.items() if claim["kind"] == "fact"
                    ]
                if len(placed["summary"]) < 2:
                    placed["summary"] = list(
                        dict.fromkeys(placed["summary"] + placed["key_findings"] + list(claims))
                    )[:3]
            report = Report(
                id=stable_id("report", s.run_id, version),
                draft_version=version,
                sections=tuple(
                    ReportSection(name=name, claim_ids=tuple(ids)) for name, ids in placed.items()
                ),
                source_ids=tuple(sorted(sources)),
            )
            return checked_patch(
                state,
                {
                    "report_claims": claims,
                    "draft_report": record_data(report),
                    "claim_evidence_map": {},
                    "critic_verdict": None,
                    "citation_audit": [],
                    "quality_attempts": s.quality_attempts + 1,
                    **quality_event(
                        state,
                        "synthesis",
                        "Prepared structured claims for criticism and citation audit.",
                    ),
                },
            )
        except (ValidationError, PlanningContractError, TimeoutError, ModelUnavailable) as exc:
            return self.failure(state, "synthesis", exc)


def compact_critic_input(s: StateSnapshot, *, dated: bool = False) -> CriticInput:
    """Review complete cited/coverage evidence and numeric counter-evidence."""
    assert s.draft_report is not None
    required = {eid for claim in s.report_claims.values() for eid in claim.evidence_ids}
    required.update(
        eid for coverage in s.coverage_by_question.values() for eid in coverage.evidence_ids
    )
    # Do not hide retained conflicting measurements just because synthesis omitted them.
    for comparison in s.comparisons.values():
        if comparison.relationship == "contradicts":
            required.update(
                s.propositions[pid].evidence_id for pid in (comparison.left_id, comparison.right_id)
            )
    if not required.issubset(s.evidence_store):
        raise PlanningContractError("Missing review evidence reference.")
    return CriticInput(
        reference_date=s.started_at.date() if dated else None,
        request=s.request,
        questions=s.research_questions,
        report=s.draft_report,
        claims=tuple(s.report_claims.values()),
        # Include every referenced raw record, including duplicate provenance IDs.
        evidence=tuple(item for item in s.evidence_store.values() if item.id in required),
        coverage=tuple(s.coverage_by_question.values()),
    )


class Critic(QualityNode):
    async def __call__(self, state: ResearchState) -> Update:
        s = StateSnapshot.model_validate(state)
        if s.draft_report is None:
            return {}
        if quality_remaining(s) <= 0:
            return quality_error(state, "critic", "budget", s.quality_attempts)
        try:
            if self.options.production_policy_version >= 4:
                request = compact_critic_input(s, dated=self.options.production_policy_version >= 5)
            else:
                working = self.working(s)
                request = CriticInput(
                    report=s.draft_report,
                    claims=tuple(s.report_claims.values()),
                    evidence=working.evidence,
                    duplicate_evidence=working.duplicates,
                    coverage=tuple(s.coverage_by_question.values()),
                )
            task = (
                self.model.critique_quotes(request)
                if self.options.quality_input_version == 2
                and self.options.quote_selection_version >= 2
                and isinstance(self.model, QuoteCriticModel)
                else self.model.critique(request)
            )
            result = await self.response(task, CriticAssessment)
            verdict = CriticVerdict(
                draft_version=s.draft_report.draft_version,
                decision=result.decision,
                revision_brief=result.revision_brief,
            )
            return checked_patch(
                state,
                {
                    "critic_verdict": record_data(verdict),
                    "quality_attempts": s.quality_attempts + 1,
                    **quality_event(state, "critic", "Reviewed the current structured draft."),
                },
            )
        except (ValidationError, PlanningContractError, TimeoutError, ModelUnavailable) as exc:
            return self.failure(state, "critic", exc)


class CitationChecker:
    def __init__(self, artifacts: ArtifactStore) -> None:
        self.artifacts = artifacts

    def __call__(self, state: ResearchState) -> Update:
        s = StateSnapshot.model_validate(state)
        if s.draft_report is None:
            return {}
        audits = []
        links = {}
        for claim in s.report_claims.values():
            structural = bool(claim.evidence_ids) and bool(claim.question_ids)
            supported = structural and all(q in claim.statement for q in claim.qualifiers)
            for eid in claim.evidence_ids:
                item = s.evidence_store[eid]
                structural = structural and set(claim.question_ids).issubset(item.question_ids)
                try:
                    content = self.artifacts.read(s.raw_result_refs[item.locator.snapshot_id])
                    authentic = (
                        content[item.locator.start_offset : item.locator.end_offset] == item.passage
                    )
                except ArtifactFailure:
                    authentic = False
                match = authentic and claim.statement == item.passage
                supported = supported and match
                link = ClaimEvidenceLink(
                    id=stable_id("link", claim.id, eid),
                    claim_id=claim.id,
                    evidence_id=eid,
                    relationship=Relationship.SUPPORTS if match else Relationship.UNCERTAIN,
                    rationale="Exact retained passage match."
                    if match
                    else "The retained passage does not exactly support this claim.",
                    verifier="offline_exact_quote",
                )
                links[link.id] = record_data(link)
            passed = structural and supported
            audit = CitationAuditItem(
                id=stable_id("audit", claim.id, s.draft_report.draft_version),
                draft_version=s.draft_report.draft_version,
                claim_id=claim.id,
                evidence_ids=claim.evidence_ids,
                structural_valid=structural,
                support=SupportVerdict.SUPPORTED if passed else SupportVerdict.UNSUPPORTED,
                rationale=(
                    "Exact quote and retained snapshot verified; "
                    "source truth was not independently verified."
                )
                if passed
                else "Citation or retained passage support failed.",
                repair_action=None
                if passed
                else "Replace with an exact supported retained passage and valid references.",
            )
            audits.append(record_data(audit))
        # Separate numeric comparison links from exact-quote authentication.
        for claim in s.report_claims.values():
            authentic_ids = {
                eid
                for eid in claim.evidence_ids
                if claim.statement == s.evidence_store[eid].passage
            }
            for comparison in s.comparisons.values():
                if comparison.relationship != "contradicts":
                    continue
                left = s.propositions[comparison.left_id].evidence_id
                right = s.propositions[comparison.right_id].evidence_id
                for cited, opposing in ((left, right), (right, left)):
                    if cited in authentic_ids and opposing not in claim.evidence_ids:
                        link = ClaimEvidenceLink(
                            id=stable_id("link", claim.id, opposing, "contradicts"),
                            claim_id=claim.id,
                            evidence_id=opposing,
                            relationship=Relationship.CONTRADICTS,
                            rationale=comparison.rationale,
                            verifier="scoped_numeric_v1",
                        )
                        links[link.id] = record_data(link)
        return checked_patch(
            state,
            {
                "citation_audit": audits,
                "claim_evidence_map": links,
                **quality_event(
                    state, "citations", "Audited every claim against its retained source snapshot."
                ),
            },
        )


def can_rewrite(s: StateSnapshot) -> bool:
    return (
        not s.stage_error and s.revision_count < s.budget.max_rewrites and quality_remaining(s) >= 2
    )


def reserve_rewrite(state: ResearchState) -> Update:
    s = StateSnapshot.model_validate(state)
    if not can_rewrite(s):
        raise ValueError("rewrite allowance unavailable")
    brief = (
        s.critic_verdict.revision_brief
        if s.critic_verdict and s.critic_verdict.decision == "revise"
        else ("Repair unsupported claims using exact retained quotations and valid evidence IDs.",)
    )
    return checked_patch(
        state,
        {
            "revision_count": s.revision_count + 1,
            "revision_brief": list(brief),
            **quality_event(state, "rewrite", "Reserved one shared critic/citation rewrite."),
        },
    )
