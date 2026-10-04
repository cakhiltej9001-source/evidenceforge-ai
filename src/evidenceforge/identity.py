"""Stable content identities; fresh execution identities are intentionally separate."""

import hashlib
import json
import re
from uuid import uuid4

from pydantic import JsonValue


def stable_id(namespace: str, *parts: JsonValue) -> str:
    """Hash canonical JSON. Include owner scope for private records in the supplied parts."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", namespace):
        raise ValueError("namespace must be a lowercase identifier")
    encoded = json.dumps(
        parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return f"{namespace}_{hashlib.sha256(encoded).hexdigest()}"


def new_id(namespace: str) -> str:
    """Create a fresh run/thread identity, not a content-deduplication key."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", namespace):
        raise ValueError("namespace must be a lowercase identifier")
    return f"{namespace}_{uuid4().hex}"
