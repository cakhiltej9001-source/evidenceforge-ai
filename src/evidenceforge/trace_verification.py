"""Explicit counters-only LangSmith probe, with no research or provider calls."""

import argparse
import json
import os
from pathlib import Path
from time import sleep

from dotenv import dotenv_values

from evidenceforge.services.observability import LangSmithTraceSink, PublicProgress


def verify_trace_export(
    *, execute: bool = False, env_file: Path | None = Path(".env")
) -> dict[str, object]:
    values = dict(dotenv_values(env_file)) if env_file is not None else {}
    values.update(os.environ)
    key = values.get("LANGSMITH_API_KEY") or ""
    result: dict[str, object] = {
        "payload_mode": "synthetic_allowlisted_counters_only",
        "research_payload_uploaded": False,
        "provider_calls": 0,
        "credentials_configured": bool(key.strip()),
        "remote_delivery_verified": False,
    }
    if not key.strip():
        return {**result, "status": "credentials_missing"}
    if not execute:
        return {**result, "status": "ready_requires_execute"}
    sink: LangSmithTraceSink | None = None
    try:
        # A fixed project name cannot contain question, user, source, or document data.
        sink = LangSmithTraceSink.from_api_key(key, "evidenceforge-synthetic-verification")
        sink.emit("final", PublicProgress("completed", "sufficient", 1, 0, 1, 1, 0, 1))
        delivery: dict[str, int | bool] = {}
        for attempt in range(3):
            delivery = sink.verify_delivery(max_readbacks=1)
            if delivery["remote_delivery_verified"]:
                break
            if attempt < 2:
                sleep(0.2)
        return {
            **result,
            **delivery,
            "status": "verified" if delivery["remote_delivery_verified"] else "unverified",
        }
    except Exception as exc:
        return {**result, "status": "export_failed", "error_type": type(exc).__name__}
    finally:
        if sink is not None:
            try:
                sink.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Upload one synthetic counter span.")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_trace_export(execute=args.execute, env_file=args.env_file)
    serialized = json.dumps(result, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 1 if args.execute and not result["remote_delivery_verified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
