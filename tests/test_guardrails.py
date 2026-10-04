"""Basic input review blocks ambiguous work before model or search calls."""

import asyncio

import pytest

from evidenceforge.config import load_settings
from evidenceforge.guardrails import InputReviewRequired, assess_input, require_research_request
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import InputStatus, ResearchRequest, SourceType
from evidenceforge.services.planning import PlanningService
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


@pytest.mark.parametrize("question", ["hi", " Hello!!! ", "help", "research this", "???", "..."])
def test_vague_or_punctuation_input_needs_clarification(question):
    decision = assess_input({"question": question})
    assert decision.status == InputStatus.NEEDS_CLARIFICATION
    assert "topic" in decision.reason


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"question": ""},
        {"question": "x" * 10001},
        {"question": "topic", "unexpected": "PRIVATE_SENTINEL"},
    ],
)
def test_invalid_input_is_rejected_without_echoing_it(value):
    decision = assess_input(value)
    assert decision.status == InputStatus.REJECTED
    with pytest.raises(InputReviewRequired) as error:
        require_research_request(value)
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert len(str(error.value)) < 200


@pytest.mark.parametrize(
    "question",
    [
        "Photosynthesis",
        "Compare solar and wind electricity output.",
        "How is hello world implemented in Python?",
        "解释太阳能发电的原理",
    ],
)
def test_topic_and_substantive_questions_preserve_input(question):
    request = ResearchRequest(question=question)
    assert assess_input(request).status == InputStatus.ACCEPTED
    assert require_research_request(request) == request


def test_ambiguous_research_never_registers_run_or_calls_a_model(tmp_path):
    model = FixtureResearchModel()
    adapter = FixtureRetrievalAdapter()
    service = ResearchService(
        tmp_path,
        model=model,
        retrieval=RetrievalService(tmp_path, {SourceType.WEB: adapter}),
    )
    with pytest.raises(InputReviewRequired):
        asyncio.run(service.run(ResearchRequest(question="help")))
    assert model.plan_calls == model.query_calls == adapter.calls == 0
    assert not (tmp_path / "checkpoints").exists()


def test_ambiguous_planning_never_calls_model():
    model = FixtureResearchModel()
    service = PlanningService(model=model)
    with pytest.raises(InputReviewRequired):
        asyncio.run(service.plan(ResearchRequest(question="research this")))
    assert model.plan_calls == model.query_calls == 0


def test_default_test_configuration_shadows_private_dotenv(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "EVIDENCEFORGE_MODEL_PROVIDER=gemini\n"
        "EVIDENCEFORGE_MODEL_ID=private-model\n"
        "EVIDENCEFORGE_MODEL_API_KEY=PRIVATE_SENTINEL\n"
        "EVIDENCEFORGE_TAVILY_API_KEY=PRIVATE_SENTINEL\n",
        encoding="utf-8",
    )
    settings = load_settings(path)
    assert settings.model_provider == "fixture"
    assert settings.model_id is None
    assert settings.model_api_key is settings.tavily_api_key is None
