"""Conservative usage summaries and configurable dated price tables."""

from dataclasses import dataclass
from datetime import date
from math import isfinite

from evidenceforge.graph.state import ResearchState, StateSnapshot


@dataclass(frozen=True)
class PriceTable:
    effective_date: date
    search_credit_usd: dict[str, float]
    model_input_million_usd: dict[str, float]
    model_output_million_usd: dict[str, float]

    def __post_init__(self) -> None:
        for values in (
            self.search_credit_usd,
            self.model_input_million_usd,
            self.model_output_million_usd,
        ):
            if any(not isfinite(value) or value < 0 for value in values.values()):
                raise ValueError("Prices must be nonnegative")


def usage_summary(state: ResearchState, prices: PriceTable | None = None) -> dict[str, object]:
    s = StateSnapshot.model_validate(state)
    input_known = sum(u.input_tokens or 0 for u in s.usage.values())
    output_known = sum(u.output_tokens or 0 for u in s.usage.values())
    credits_known = sum(u.search_credits or 0 for u in s.usage.values())
    unknown_tokens = sum(
        u.input_tokens is None or u.output_tokens is None
        for u in s.usage.values()
        if s.calls[u.call_id].kind == "model"
    )
    unknown_credits = sum(
        u.search_credits is None for u in s.usage.values() if s.calls[u.call_id].kind == "search"
    )
    unrecorded_model_attempts = max(
        0,
        s.quality_attempts + s.planning_attempts - sum(c.kind == "model" for c in s.calls.values()),
    )
    known_cost = 0.0
    unknown_cost = unrecorded_model_attempts > 0
    for usage in s.usage.values():
        if usage.estimated_cost_usd is not None:
            known_cost += usage.estimated_cost_usd
        elif prices and s.calls[usage.call_id].kind == "search":
            rate = prices.search_credit_usd.get(usage.provider)
            if rate is None or usage.search_credits is None:
                unknown_cost = True
            else:
                known_cost += rate * usage.search_credits
        elif prices and s.calls[usage.call_id].kind == "model":
            key = f"{usage.provider}:{usage.model}"
            input_rate = prices.model_input_million_usd.get(key)
            output_rate = prices.model_output_million_usd.get(key)
            if (
                input_rate is None
                or output_rate is None
                or usage.input_tokens is None
                or usage.output_tokens is None
            ):
                unknown_cost = True
            else:
                known_cost += (
                    input_rate * usage.input_tokens + output_rate * usage.output_tokens
                ) / 1_000_000
        else:
            unknown_cost = True
    return {
        "search_reservations": sum(
            r.searches for r in s.reservations.values() if r.status != "released"
        ),
        "model_attempts": s.quality_attempts + s.planning_attempts,
        "planning_model_attempts": s.planning_attempts,
        "quality_model_attempts": s.quality_attempts,
        "input_tokens_known": input_known,
        "output_tokens_known": output_known,
        "token_usage_unknown_records": unknown_tokens + unrecorded_model_attempts,
        "search_credits_known": credits_known,
        "search_credit_unknown_records": unknown_credits,
        "estimated_cost_usd": None if unknown_cost else round(known_cost, 8),
        "known_cost_lower_bound_usd": round(known_cost, 8),
        "price_table_date": prices.effective_date.isoformat() if prices else None,
        "cost_complete": not unknown_cost,
    }
