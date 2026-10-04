"""Pure reducers: immutable records conflict; call/reservation lifecycles are explicit."""

from copy import deepcopy
from typing import cast

from pydantic import JsonValue

RecordData = dict[str, JsonValue]
RecordMap = dict[str, RecordData]


def _check_map(records: RecordMap) -> None:
    if not isinstance(records, dict):
        raise ValueError("record channel must be a dictionary")
    for key, record in records.items():
        if not isinstance(key, str) or not isinstance(record, dict) or record.get("id") != key:
            raise ValueError("record map key must match its ID")


def merge_records(left: RecordMap, right: RecordMap) -> RecordMap:
    """Union immutable records by ID, deterministically; never silently overwrite conflicts."""
    _check_map(left)
    _check_map(right)
    result = deepcopy(left)
    for key, record in right.items():
        if record.get("id") != key:
            raise ValueError("record map key must match its ID")
        if key in result and result[key] != record:
            raise ValueError(f"conflicting immutable record: {key}")
        result[key] = deepcopy(record)
    return dict(sorted(result.items()))


def merge_query_keys(left: list[str], right: list[str]) -> list[str]:
    if not isinstance(left, list) or not isinstance(right, list):
        raise ValueError("query-key updates must be lists")
    if not all(isinstance(item, str) for item in [*left, *right]):
        raise ValueError("query keys must be strings")
    return sorted(set(left) | set(right))


def merge_log(left: RecordMap, right: RecordMap) -> RecordMap:
    result = merge_records(left, right)
    if len(result) > 200:
        raise ValueError("checkpoint log limit reached; archive/reset explicitly")
    return result


def merge_calls(left: RecordMap, right: RecordMap) -> RecordMap:
    """Versioned call state; completed responses cannot be silently replaced on replay."""
    _check_map(left)
    _check_map(right)
    result = deepcopy(left)
    transitions = {
        "pending": {"completed", "failed", "ambiguous", "cancelled"},
        "ambiguous": {"completed", "failed", "cancelled"},
    }
    for key, incoming in right.items():
        if incoming.get("id") != key:
            raise ValueError("call map key must match its ID")
        previous = result.get(key)
        if previous is not None and previous != incoming:
            for field in ("id", "request_hash", "provider", "kind", "started_at"):
                if previous.get(field) != incoming.get(field):
                    raise ValueError(f"call identity changed: {key}")
            old_version, new_version = previous.get("revision"), incoming.get("revision")
            if not isinstance(old_version, int) or not isinstance(new_version, int):
                raise ValueError("call revisions must be integers")
            if new_version < old_version:
                continue
            if new_version == old_version:
                raise ValueError(f"conflicting call revision: {key}")
            old_status, new_status = previous.get("status"), incoming.get("status")
            if (
                not isinstance(old_status, str)
                or not isinstance(new_status, str)
                or new_status not in transitions.get(old_status, set())
            ):
                raise ValueError(f"invalid call lifecycle transition: {key}")
        result[key] = deepcopy(incoming)
    return dict(sorted(result.items()))


def merge_reservations(left: RecordMap, right: RecordMap) -> RecordMap:
    """Only reserved -> settled/released; late replay of the reservation is harmless."""
    _check_map(left)
    _check_map(right)
    result = deepcopy(left)
    for key, incoming in right.items():
        if incoming.get("id") != key:
            raise ValueError("reservation map key must match its ID")
        previous = result.get(key)
        if previous is not None and previous != incoming:
            immutable_fields = (
                "id",
                "call_id",
                "searches",
                "model_calls",
                "tokens",
                "estimated_cost_usd",
            )
            if any(previous.get(field) != incoming.get(field) for field in immutable_fields):
                raise ValueError(f"reservation identity changed: {key}")
            old_status, new_status = previous.get("status"), incoming.get("status")
            if old_status in ("settled", "released") and new_status == "reserved":
                continue
            if old_status != "reserved" or new_status not in ("settled", "released"):
                raise ValueError(f"conflicting reservation settlement: {key}")
        result[key] = deepcopy(incoming)
    return dict(sorted(result.items()))


def merge_evidence(left: RecordMap, right: RecordMap) -> RecordMap:
    """Union provenances/question associations while keeping passage identity immutable."""
    _check_map(left)
    _check_map(right)
    result = deepcopy(left)
    for key, incoming in right.items():
        if incoming.get("id") != key:
            raise ValueError("evidence map key must match its ID")
        previous = result.get(key)
        if previous is None:
            result[key] = deepcopy(incoming)
            continue
        mutable = {"acquisition_ids", "question_ids"}
        if {k: v for k, v in previous.items() if k not in mutable} != {
            k: v for k, v in incoming.items() if k not in mutable
        }:
            raise ValueError(f"conflicting evidence payload: {key}")
        merged = deepcopy(previous)
        for field in mutable:
            old_ids, new_ids = previous.get(field), incoming.get(field)
            if not isinstance(old_ids, list) or not isinstance(new_ids, list):
                raise ValueError("evidence associations must be JSON arrays")
            if not all(isinstance(item, str) for item in [*old_ids, *new_ids]):
                raise ValueError("evidence associations must be identifiers")
            merged[field] = cast(
                JsonValue, sorted(set(cast(list[str], old_ids)) | set(cast(list[str], new_ids)))
            )
        result[key] = merged
    return dict(sorted(result.items()))
