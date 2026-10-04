"""Read a bounded local exported state and inspect a selected finding."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from evidenceforge.evidence.projection import project, render_inspection
from evidenceforge.graph.state import validate_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect stored claim links, exact passages, and disputes."
    )
    parser.add_argument("state", type=Path)
    parser.add_argument("--claim")
    parser.add_argument("--owner", default="local")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    args = parser.parse_args()
    try:
        with args.state.open("rb") as stream:
            content = stream.read(16_000_001)
        if len(content) > 16_000_000:
            raise ValueError("Exported state exceeds inspection size limit.")
        state = validate_state(json.loads(content))
        if state["owner_scope"] != args.owner:
            raise ValueError("Owner scope differs from the exported state.")
        output = (
            json.dumps(
                project(state, args.claim).model_dump(mode="json"), ensure_ascii=False, indent=2
            )
            if args.format == "json"
            else render_inspection(state, args.claim)
        )
    except (OSError, ValueError, ValidationError):
        print("Inspection failed: check the state file, owner scope, and claim ID.")
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
