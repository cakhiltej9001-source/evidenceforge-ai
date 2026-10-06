"""Bounded local node timing and optional content tracing; no remote export."""

import inspect
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evidenceforge.graph.state import ResearchState


class NodeTrace:
    def __init__(self, path: Path, *, payloads: bool = False, max_bytes: int = 4_000_000) -> None:
        self.path, self.payloads, self.max_bytes = path, payloads, max_bytes
        self.written = self.failed = self.omitted = 0

    def wrap(self, name: str, action: Callable[..., Any]) -> Callable[..., Any]:
        async def measured(state: ResearchState) -> Any:
            started = time.perf_counter()
            status = "completed"
            result: Any = None
            try:
                result = action(state)
                if inspect.isawaitable(result):
                    result = await result
                return result
            except BaseException:
                status = "interrupted_or_failed"
                raise
            finally:
                record: dict[str, Any] = {
                    "node": name,
                    "at": datetime.now(UTC).isoformat(),
                    "duration_seconds": round(time.perf_counter() - started, 6),
                    "status": status,
                    "run_id": state["run_id"],
                    "pass": state["iteration_count"],
                    "rewrite": state["revision_count"],
                    "model_attempts_before": state["planning_attempts"] + state["quality_attempts"],
                }
                if self.payloads:
                    record["input_state"] = state
                    record["output_update"] = result
                try:
                    raw = (
                        json.dumps(
                            record,
                            default=lambda value: getattr(
                                value, "value", str(type(value).__name__)
                            ),
                        )
                        + "\n"
                    ).encode()
                    if (
                        len(raw) + (self.path.stat().st_size if self.path.exists() else 0)
                        > self.max_bytes
                    ):
                        self.omitted += 1
                    else:
                        self.path.parent.mkdir(parents=True, exist_ok=True)
                        with self.path.open("ab") as stream:
                            stream.write(raw)
                        self.written += 1
                except (OSError, ValueError, TypeError):
                    self.failed += 1

        return measured
