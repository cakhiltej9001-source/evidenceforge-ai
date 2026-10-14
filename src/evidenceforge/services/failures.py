"""Fixed public diagnostics: never forward provider bodies or exception messages."""

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.storage.model_calls import ModelReceipt

STAGES = {
    "input_guardrail": "Question review",
    "planner": "Research planning",
    "context_manager": "Document/context lookup",
    "query_generator": "Search preparation",
    "coverage_evaluator": "Evidence coverage",
    "coverage": "Evidence coverage",
    "synthesis": "Report drafting",
    "critic": "Report review",
    "citation_checker": "Citation checks",
}

CATEGORIES = {
    "authentication": "Provider credentials were rejected. Ask the app owner to check them.",
    "rate_limit": "The provider rate or quota limit was reached. Wait before starting a new run.",
    "timeout": "The request timed out. A response was not confirmed; usage may still count.",
    "schema": "The model response did not match the required structure.",
    "parse": "The returned source could not be parsed.",
    "provider": "The provider could not complete this stage.",
    "budget": "This run reached a configured allowance.",
    "cancelled": "The operation was cancelled.",
    "internal": "The operation could not be completed.",
}


def public_failures(state: ResearchState) -> list[dict[str, str]]:
    snapshot = StateSnapshot.model_validate(state)
    return [
        {
            "stage": STAGES.get(error.provider, "Source or workflow step"),
            "category": error.category,
            "message": CATEGORIES.get(error.category, CATEGORIES["internal"]),
        }
        for error in snapshot.tool_errors.values()
    ]


def model_failures(records: list[ModelReceipt]) -> list[dict[str, str | int]]:
    result: list[dict[str, str | int]] = []
    for receipt in records:
        if receipt.status == "succeeded":
            continue
        observation = receipt.observation
        row: dict[str, str | int] = {
            "stage": STAGES.get(str(observation.get("role")), "Gemini generation"),
            "message": CATEGORIES["provider"],
        }
        status = observation.get("status")
        if isinstance(status, str) and status.startswith("http_"):
            code = status.removeprefix("http_")
            if code.isascii() and code.isdigit() and 100 <= int(code) <= 599:
                number = int(code)
                row["http_status"] = number
                row["message"] = (
                    CATEGORIES["authentication"]
                    if number in {401, 403}
                    else CATEGORIES["rate_limit"]
                    if number == 429
                    else "Gemini is temporarily unavailable. Wait before starting a new run."
                    if number >= 500
                    else "Gemini rejected the configured model or request settings."
                )
        elif observation.get("validation_errors"):
            row["message"] = CATEGORIES["schema"]
        elif status == "timeout":
            row["message"] = CATEGORIES["timeout"]
        elif status == "incomplete":
            row["message"] = "Gemini did not return a complete structured answer."
        if receipt.status == "pending":
            row["message"] = (
                "The Gemini call is unconfirmed. Automatic retry is blocked; usage may count."
            )
        result.append(row)
    return result
