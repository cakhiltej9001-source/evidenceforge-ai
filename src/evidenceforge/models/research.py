"""Quote-backed synthetic assessment templates; not semantic model reasoning."""

from copy import deepcopy

from evidenceforge.models.fixtures import FixturePlanningModel
from evidenceforge.nodes.extraction import tokens
from evidenceforge.planning import QueryGenerationRequest
from evidenceforge.research import CoverageInput, CriticInput, SynthesisInput
from evidenceforge.schemas import ResearchRequest


class FixtureResearchModel(FixturePlanningModel):
    def __init__(
        self,
        *,
        coverage_output: object = None,
        synthesis_output: object = None,
        critic_output: object = None,
        plan_output: object = None,
        query_output: object = None,
    ) -> None:
        super().__init__(plan_output=plan_output, query_output=query_output)
        self.coverage_output, self.synthesis_output, self.critic_output = (
            coverage_output,
            synthesis_output,
            critic_output,
        )
        self.coverage_calls = self.synthesis_calls = self.critic_calls = 0

    async def plan(self, request: ResearchRequest, *, max_questions: int) -> object:
        if self.plan_output is not None:
            return await super().plan(request, max_questions=max_questions)
        self.plan_calls += 1
        if {"solar", "wind"}.issubset(tokens(request.question)):
            if max_questions == 1:
                return {
                    "questions": [
                        {
                            "question": request.question,
                            "acceptance_criteria": [
                                "solar electricity output",
                                "wind electricity output",
                            ],
                        }
                    ]
                }
            return {
                "questions": [
                    {
                        "question": "What determines solar electricity output?",
                        "acceptance_criteria": ["solar electricity output"],
                    },
                    {
                        "question": "What determines wind electricity output?",
                        "acceptance_criteria": ["wind electricity output"],
                    },
                ]
            }
        return {
            "questions": [
                {
                    "question": " ".join(request.question.split()),
                    "acceptance_criteria": [" ".join(sorted(tokens(request.question))) or "answer"],
                }
            ]
        }

    async def generate_queries(self, request: QueryGenerationRequest) -> object:
        if not request.gaps or self.query_output is not None:
            return await super().generate_queries(request)
        self.query_calls += 1
        return {
            "queries": [
                {
                    "question_ids": [gap.question_id],
                    "text": gap.recommended_query,
                    "source_type": request.available_source_types[0].value,
                    "purpose": gap.purpose,
                }
                for gap in request.gaps[: request.max_queries]
            ]
        }

    async def evaluate_coverage(self, request: CoverageInput) -> object:
        self.coverage_calls += 1
        if self.coverage_output is not None:
            return deepcopy(self.coverage_output)
        questions = []
        for question in request.questions:
            criteria = []
            for index, criterion in enumerate(question.acceptance_criteria):
                needed = tokens(criterion)
                matches = [
                    e.id
                    for e in request.evidence
                    if question.id in e.question_ids
                    and needed
                    and needed.issubset(tokens(e.passage))
                ]
                if matches:
                    criteria.append({"index": index, "evidence_ids": matches})
            questions.append({"question_id": question.id, "criteria": criteria})
        return {"questions": questions}

    async def synthesize(self, request: SynthesisInput) -> object:
        self.synthesis_calls += 1
        if self.synthesis_output is not None:
            return deepcopy(self.synthesis_output)
        propositions = {p.id: p for p in request.propositions}
        disputed = {
            propositions[pid].evidence_id
            for c in request.comparisons
            if c.relationship == "contradicts"
            for pid in (c.left_id, c.right_id)
        }
        return {
            "claims": [
                {
                    "statement": evidence.passage,
                    "question_ids": list(evidence.question_ids),
                    "evidence_ids": [evidence.id],
                    "section": "disagreements" if evidence.id in disputed else "key_findings",
                    "kind": "fact",
                }
                for evidence in request.evidence[:64]
            ]
        }

    async def critique(self, request: CriticInput) -> object:
        self.critic_calls += 1
        if self.critic_output is not None:
            return deepcopy(self.critic_output)
        return {"decision": "approved", "revision_brief": []}
