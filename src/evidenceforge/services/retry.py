"""Conservative bounded retry policy for explicitly retry-safe adapters."""

import hashlib

from evidenceforge.retrieval.contracts import ErrorCategory, RetrievalAdapter

RETRYABLE = frozenset({"rate_limit", "timeout", "provider"})


def retry_delay(
    category: ErrorCategory,
    attempt: int,
    identity: str,
    adapter: RetrievalAdapter,
    retry_after_seconds: float | None = None,
) -> float | None:
    """Return a bounded backoff, or None when another paid call is unsafe."""
    if category not in RETRYABLE or not (
        getattr(adapter, "retry_safe", False)
        or category in getattr(adapter, "retry_safe_categories", ())
    ):
        return None
    jitter = (
        int.from_bytes(hashlib.sha256(f"{identity}:{attempt}".encode()).digest()[:2], "big") / 65535
    )
    delay = float(min(2.0, 0.1 * 2 ** (attempt - 1)) * (0.75 + 0.5 * jitter))
    if retry_after_seconds is not None:
        if retry_after_seconds < 0 or retry_after_seconds > 60:
            return None
        delay = max(delay, retry_after_seconds)
    return delay
