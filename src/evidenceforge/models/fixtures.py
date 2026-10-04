"""Deterministic fixture templates/scripted outputs, not live LLM intelligence."""

from copy import deepcopy

from evidenceforge.planning import QueryGenerationRequest
from evidenceforge.schemas import ResearchRequest, SourceType


class FixturePlanningModel:
    is_fixture = True

    def __init__(self, *, plan_output: object = None, query_output: object = None) -> None:
        self.plan_output = plan_output
        self.query_output = query_output
        self.plan_calls = 0
        self.query_calls = 0

    async def plan(self, request: ResearchRequest, *, max_questions: int) -> object:
        self.plan_calls += 1
        if self.plan_output is not None:
            return deepcopy(self.plan_output)
        topic = " ".join(request.question.split()).replace("?", "")[:500].rstrip(".!")
        questions = [
            {
                "question": f"Which definitions set the scope of {topic}?",
                "acceptance_criteria": ["Relevant definitions with source scope and date"],
                "importance": 1.0,
            },
            {
                "question": f"What primary evidence addresses {topic}?",
                "acceptance_criteria": [
                    "Primary passages addressing the requested comparison or facts"
                ],
                "importance": 1.0,
            },
            {
                "question": f"What limitations affect conclusions about {topic}?",
                "acceptance_criteria": ["Explicit assumptions, constraints and unresolved aspects"],
                "importance": 0.8,
            },
        ]
        return {"questions": questions[:max_questions]}

    async def generate_queries(self, request: QueryGenerationRequest) -> object:
        self.query_calls += 1
        if self.query_output is not None:
            return deepcopy(self.query_output)
        candidates = []
        for index, question in enumerate(request.questions[: request.max_queries]):
            source = request.available_source_types[index % len(request.available_source_types)]
            if source == SourceType.WEB:
                text = f"{question.question.rstrip('?')} primary sources"
            elif source == SourceType.DOCUMENT:
                text = f"{question.question.rstrip('?')} relevant passage"
            else:
                text = question.question
            candidates.append(
                {
                    "question_ids": [question.id],
                    "text": text,
                    "source_type": source.value,
                    "purpose": "primary_source",
                }
            )
        return {"queries": candidates}
