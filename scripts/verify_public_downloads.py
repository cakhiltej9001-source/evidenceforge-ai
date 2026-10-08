"""Verify one fixture-only public demo run with real Chromium downloads.

The URL and question are fixed. No login, secrets, provider APIs, storage state,
network traces, or raw report artifacts are recorded.
Playwright APIs: https://playwright.dev/python/docs/downloads
CI setup: https://playwright.dev/python/docs/ci
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Frame, Locator, Page

PUBLIC_URL = "https://evidenceforge-ai-akhiltej.streamlit.app/"
QUESTION = "Compare solar and wind electricity output."
TITLE = "EvidenceForge research workbench"
DISCLOSURE = "Try the workflow with offline synthetic examples."
FIXTURE_DISCLOSURE = "Offline synthetic fixture demonstration"
MAX_DOWNLOAD_BYTES = 2_000_000


class VerificationFailure(ValueError):
    """A fixed check code without browser transport or session details."""


def check(condition: bool, code: str) -> None:
    if not condition:
        raise VerificationFailure(code)


def wait_enabled(page: Frame, button: Locator, *, timeout: float) -> None:
    """Allow the Streamlit fragment to finish its bounded background operation."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if button.is_visible() and button.is_enabled():
            return
        refresh = page.get_by_role("button", name="Refresh UI", exact=True)
        if refresh.is_visible() and refresh.is_enabled():
            refresh.click(timeout=5_000)
        page.wait_for_timeout(2_000)
    raise TimeoutError("workflow_control_not_ready")


def open_demo(page: Page) -> Frame:
    """Bound cold-start retries before any workflow is created."""
    page.goto(PUBLIC_URL, wait_until="domcontentloaded", timeout=45_000)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        # Community Cloud can put the app inside a hosting-shell iframe.
        # Select only a uniquely observed app surface with the actual UI controls.
        candidates = [
            frame
            for frame in page.frames
            if frame.get_by_role("heading", name=TITLE, exact=True).is_visible()
            and frame.get_by_role("button", name="Create plan", exact=True).is_visible()
        ]
        check(len(candidates) <= 1, "ambiguous_app_frame")
        if candidates:
            return candidates[0]
        wake = page.get_by_role("button", name="Yes, get this app back up!", exact=True)
        if wake.is_visible() and wake.is_enabled():
            wake.click(timeout=5_000)
        refresh = page.get_by_role("button", name="Refresh UI", exact=True)
        if refresh.is_visible() and refresh.is_enabled():
            refresh.click(timeout=5_000)
        page.wait_for_timeout(2_000)
    raise TimeoutError("public_demo_not_ready")


def check_fixture_controls(page: Frame) -> None:
    check(page.get_by_text(DISCLOSURE, exact=False).is_visible(), "fixture_banner_missing")
    check(
        page.get_by_text("No Gemini calls or search credits are used.", exact=False).is_visible(),
        "zero_provider_banner_missing",
    )
    provider = page.get_by_role("combobox", name="Reasoning provider", exact=True)
    check(provider.is_visible(), "provider_control_missing")
    # BaseWeb exposes an input as the combobox; its inner text is empty.
    # The selected value is rendered in the surrounding labeled Streamlit field.
    field = provider.locator('xpath=ancestor::*[@data-testid="stSelectbox"][1]')
    check(field.get_by_text("Offline", exact=True).is_visible(), "provider_is_not_offline")
    check(page.get_by_role("checkbox").count() == 0, "live_controls_present")
    check(page.locator('input[type="file"]').count() == 0, "upload_control_present")


def sanitized_screenshot(page: Page, path: Path) -> None:
    """Mask session identifiers and source locator panels in synthetic screenshots."""
    masks = []
    for frame in page.frames:
        masks.extend(
            [
                frame.locator('[data-testid="stSidebar"]'),
                frame.locator('[data-testid="stJson"]'),
                frame.locator('[data-testid="stCodeBlock"]'),
                frame.get_by_text(re.compile(r"^Thread: ")),
                frame.get_by_text(
                    re.compile(
                        r"\b(?:run|thread|visitor|source|evidence|artifact|question|claim)"
                        r"_[a-z0-9]+\b"
                    )
                ),
            ]
        )
    page.screenshot(path=str(path), full_page=True, mask=masks, timeout=15_000)


def download_report(page: Page, frame: Frame, label: str, filename: str, directory: Path) -> bytes:
    with page.expect_download(timeout=30_000) as pending:
        frame.get_by_role("button", name=label, exact=True).click(timeout=10_000)
    download = pending.value
    check(download.suggested_filename == filename, "download_filename_mismatch")
    destination = directory / filename
    download.save_as(str(destination))
    check(download.failure() is None, "download_failed")
    check(destination.is_file(), "download_file_missing")
    size = destination.stat().st_size
    check(0 < size <= MAX_DOWNLOAD_BYTES, "download_size_out_of_bounds")
    return destination.read_bytes()


def verify(output: Path, result: dict[str, Any]) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, timeout=30_000)
        result["browser_version"] = browser.version
        result["playwright_version"] = version("playwright")
        first = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 900})
        try:
            page = first.new_page()
            page.set_default_timeout(15_000)
            result["stage"] = "public_demo_ready"
            frame = open_demo(page)
            check_fixture_controls(frame)
            result["checks"]["fixture_only_controls"] = True
            sanitized_screenshot(page, output / "fixture-start.png")
            frame.get_by_role("textbox", name="Research question", exact=True).fill(QUESTION)
            create = frame.get_by_role("button", name="Create plan", exact=True)
            result["stage"] = "create_plan"
            wait_enabled(frame, create, timeout=30)
            create.click(timeout=10_000)
            approve = frame.get_by_role("button", name="Approve plan", exact=True)
            wait_enabled(frame, approve, timeout=90)
            result["checks"]["plan_created"] = True
            result["stage"] = "approve_plan"
            approve.click(timeout=10_000)
            markdown_button = frame.get_by_role("button", name="Download Markdown", exact=True)
            wait_enabled(frame, markdown_button, timeout=120)
            result["checks"]["report_download_controls_visible"] = True
            result["stage"] = "download_reports"
            # Raw exports contain fixture/session IDs. Keep them only in this temporary
            # directory and publish boolean/count evidence instead of their contents.
            with TemporaryDirectory(prefix="evidenceforge-fixture-downloads-") as folder:
                directory = Path(folder)
                markdown_bytes = download_report(
                    page, frame, "Download Markdown", "report.md", directory
                )
                json_bytes = download_report(page, frame, "Download JSON", "report.json", directory)
                markdown = markdown_bytes.decode("utf-8")
                exported = json.loads(json_bytes.decode("utf-8"))
                check(FIXTURE_DISCLOSURE in markdown, "markdown_fixture_disclosure_missing")
                check("Status: `completed`" in markdown, "markdown_not_completed")
                for expected in (
                    "Synthetic fixture: solar electricity output depends on sunlight",
                    "Synthetic fixture: wind electricity output depends on wind speed",
                ):
                    check(expected in markdown, "markdown_fixture_finding_missing")
                check(exported.get("export_version") == 1, "unexpected_export_version")
                check(exported.get("evidence_mode") == "synthetic_fixture", "nonfixture_export")
                check(exported.get("model") == "offline_fixture", "nonfixture_model")
                check(exported.get("progress", {}).get("run_status") == "completed", "incomplete")
                check(isinstance(exported.get("report"), dict), "report_missing")
                check("model_api_key" not in json_bytes.decode("utf-8"), "private_field_in_export")
                result["downloads"] = [
                    {"filename": "report.md", "bytes": len(markdown_bytes), "verified": True},
                    {"filename": "report.json", "bytes": len(json_bytes), "verified": True},
                ]
            result["checks"]["markdown_browser_download"] = True
            result["checks"]["json_browser_download"] = True
            result["checks"]["completed_fixture_export"] = True
            sanitized_screenshot(page, output / "fixture-completed.png")
            result["stage"] = "fresh_browser_isolation"
            # A separate context has no cookies/storage inherited from the first visitor.
            second = browser.new_context(viewport={"width": 1280, "height": 900})
            try:
                other = second.new_page()
                other.set_default_timeout(15_000)
                other_frame = open_demo(other)
                check_fixture_controls(other_frame)
                other.wait_for_timeout(4_000)
                check(
                    other_frame.get_by_role("combobox", name="Saved thread", exact=True).count()
                    == 0,
                    "second_visitor_has_saved_thread",
                )
                for label in ("Download Markdown", "Download JSON"):
                    check(
                        other_frame.get_by_role("button", name=label, exact=True).count() == 0,
                        "second_visitor_has_download",
                    )
                result["checks"]["fresh_browser_has_no_saved_thread"] = True
                result["checks"]["fresh_browser_has_no_report_downloads"] = True
                sanitized_screenshot(other, output / "fresh-visitor.png")
            finally:
                second.close()
            result["status"] = "verified"
            result["stage"] = "finished"
        except Exception:
            try:
                sanitized_screenshot(page, output / "fixture-failure.png")
            except Exception:
                pass
            raise
        finally:
            first.close()
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".evidenceforge/verification/public-downloads"),
        help="Directory for sanitized JSON and masked screenshots; never raw reports.",
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "verification_version": 1,
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "target": PUBLIC_URL,
        "status": "failed",
        "stage": "browser_start",
        "checks": {},
        "downloads": [],
        "paid_provider_calls_requested_by_check": 0,
        "scope": "one fixed offline synthetic fixture run and one fresh browser context",
        "limitations": [
            "This verifies hosted browser exports and visitor isolation for one fixture case.",
            "It does not establish broader factual accuracy or persistent hosted storage.",
        ],
    }
    try:
        verify(output, result)
    except Exception as error:
        # Playwright exception messages may contain transport/session details.
        # Record only the stable stage and exception class, never a traceback.
        result["failure_class"] = type(error).__name__
        if isinstance(error, VerificationFailure):
            result["failure_code"] = str(error)
    finally:
        (output / "result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
