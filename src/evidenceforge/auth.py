"""Single-owner hosted login with password hashing and shared attempt throttling."""

import hashlib
import hmac
import os
import secrets
import threading
import time

from evidenceforge.config import ConfigurationError, Settings

ITERATIONS = 600_000


def password_hash(password: str, *, salt: str | None = None) -> str:
    if len(password) < 16 or len(password) > 1024:
        raise ValueError("Use a password of 16 to 1024 characters.")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$")
        if (
            scheme != "pbkdf2_sha256"
            or int(rounds) != ITERATIONS
            or len(password) > 1024
            or len(salt) != 32
            or len(expected) != 64
        ):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), ITERATIONS
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class LoginGate:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.failures: list[float] = []

    def check(self, username: str, password: str, settings: Settings) -> bool:
        with self.lock:
            now = time.monotonic()
            self.failures = [t for t in self.failures if now - t < 60]
            if len(self.failures) >= 5:
                return False
            valid = verify_password(
                password,
                settings.auth_password_hash.get_secret_value()
                if settings.auth_password_hash
                else "",
            )
            valid = valid and hmac.compare_digest(
                username.encode(), settings.auth_username.encode()
            )
            if valid:
                self.failures.clear()
            else:
                self.failures.append(now)
            return valid


def required(settings: Settings) -> bool:
    return settings.auth_required or os.environ.get("RENDER", "").lower() == "true"


def fingerprint(settings: Settings) -> str:
    if not settings.auth_password_hash:
        raise ConfigurationError("Hosted login requires EVIDENCEFORGE_AUTH_PASSWORD_HASH.")
    return hashlib.sha256(
        (settings.auth_username + settings.auth_password_hash.get_secret_value()).encode()
    ).hexdigest()
