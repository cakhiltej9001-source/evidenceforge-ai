"""Validate a Render Blueprint against a locally retained official JSON schema."""

import argparse
import hashlib
import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator


def reject_external_references(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and (not isinstance(item, str) or not item.startswith("#")):
                raise ValueError("External schema references are not permitted")
            reject_external_references(item)
    elif isinstance(value, list):
        for item in value:
            reject_external_references(item)


def validate(blueprint_path: Path, schema_path: Path) -> dict[str, object]:
    if blueprint_path.stat().st_size > 100_000 or schema_path.stat().st_size > 2_000_000:
        raise ValueError("Validation input exceeds the size allowance")
    blueprint_bytes, schema_bytes = blueprint_path.read_bytes(), schema_path.read_bytes()
    blueprint = yaml.safe_load(blueprint_bytes)
    schema = json.loads(schema_bytes)
    reject_external_references(schema)
    Draft7Validator.check_schema(schema)
    problems = sorted(Draft7Validator(schema).iter_errors(blueprint), key=lambda e: str(e.path))
    return {
        "kind": "local_render_schema_validation",
        "valid": not problems,
        "blueprint_sha256": hashlib.sha256(blueprint_bytes).hexdigest(),
        "schema_sha256": hashlib.sha256(schema_bytes).hexdigest(),
        # Paths and violated rules are diagnostic; do not echo environment values.
        "errors": [
            {"path": "/".join(map(str, p.absolute_path)), "rule": str(p.validator)}
            for p in problems
        ],
        "resources_created": 0,
        "hosted_runtime_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, default=Path("render.yaml"))
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.blueprint, args.schema)
    except (OSError, ValueError, yaml.YAMLError):
        print("Blueprint/schema input could not be validated.")
        return 1
    text = json.dumps(result, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
