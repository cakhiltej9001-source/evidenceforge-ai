"""Opt-in local PDF OCR in a bounded child process; documents never leave this host."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import Field

from evidenceforge.schemas import Contract, PositiveCount


class LocalOcrFailure(ValueError):
    """Sanitized unavailable-engine, timeout or output-limit failure."""


class OcrLimits(Contract):
    max_pages: PositiveCount = Field(default=5, le=10)
    max_pixels: PositiveCount = Field(default=4_000_000, le=8_000_000)
    timeout_seconds: PositiveCount = Field(default=120, le=180)
    max_text_bytes: PositiveCount = Field(default=200_000, le=2_000_000)


class OcrResult(Contract):
    pages: dict[int, str]


def _worker_pythonpath() -> str:
    """Include only the current package and already resolved OCR installation roots."""
    roots = [str(Path(__file__).resolve().parents[2])]
    try:
        for module in ("rapidocr_onnxruntime", "pypdfium2"):
            spec = importlib.util.find_spec(module)
            if spec is None:
                raise LocalOcrFailure("Local OCR requires Python 3.12 and the optional ocr extra.")
            if spec.submodule_search_locations:
                roots.extend(
                    str(Path(location).resolve().parent)
                    for location in spec.submodule_search_locations
                )
            elif spec.origin is not None:
                roots.append(str(Path(spec.origin).resolve().parent))
            else:
                raise LocalOcrFailure("Local OCR requires Python 3.12 and the optional ocr extra.")
    except (ImportError, OSError, ValueError) as exc:
        if isinstance(exc, LocalOcrFailure):
            raise
        raise LocalOcrFailure(
            "Local OCR requires Python 3.12 and the optional ocr extra."
        ) from None
    return os.pathsep.join(dict.fromkeys(roots))


def _stop_worker(process: subprocess.Popen[bytes], environment: dict[str, str]) -> None:
    """Stop an owned worker, including a Windows launcher's descendant process."""
    tree_confirmed = True
    if sys.platform == "win32":
        # Use the OS utility by absolute path and the owned child's PID, never a shell
        # or an image-name match. Keep the parent alive until the tree is terminated.
        taskkill = Path(environment.get("SYSTEMROOT", r"C:\Windows")) / "System32" / "taskkill.exe"
        try:
            result = subprocess.run(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                env=environment,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            tree_confirmed = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            tree_confirmed = False
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        raise LocalOcrFailure(
            "Local OCR time limit exceeded; process cleanup could not be confirmed."
        ) from None
    if not tree_confirmed:
        raise LocalOcrFailure(
            "Local OCR time limit exceeded; process-tree cleanup could not be confirmed."
        )


def transcribe_pdf(
    data: bytes, pages: tuple[int, ...], limits: OcrLimits, temporary_root: Path
) -> dict[int, str]:
    """Run CPU OCR only on requested textless pages, then validate bounded output."""
    if not pages or len(pages) > limits.max_pages or any(page < 1 for page in pages):
        raise LocalOcrFailure("OCR page limit exceeded.")
    if sys.version_info >= (3, 13):
        raise LocalOcrFailure("Local OCR requires Python 3.12 and the optional ocr extra.")
    pythonpath = _worker_pythonpath()
    with TemporaryDirectory(prefix=".ocr-", dir=temporary_root) as folder:
        directory = Path(folder)
        input_path, output_path, job_path = (
            directory / name for name in ("input.pdf", "output.json", "job.json")
        )
        input_path.write_bytes(data)
        job_path.write_text(
            json.dumps({"pages": pages, "limits": limits.model_dump()}), encoding="utf-8"
        )
        # The local engine needs runtime paths, not provider credentials or tracing.
        runtime_keys = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "TEMP",
            "TMP",
            "TMPDIR",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "LD_LIBRARY_PATH",
            "DYLD_LIBRARY_PATH",
        }
        environment = {
            key: value for key, value in os.environ.items() if key.upper() in runtime_keys
        }
        environment.update(
            {
                "OMP_NUM_THREADS": "1",
                "PYTHONPATH": pythonpath,
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            }
        )
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "evidenceforge.storage.ocr_worker",
                    str(input_path),
                    str(output_path),
                    str(job_path),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                returncode = process.wait(timeout=limits.timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop_worker(process, environment)
                raise LocalOcrFailure("Local OCR time limit exceeded.") from None
            if returncode or not output_path.is_file():
                raise LocalOcrFailure("Local OCR failed; affected pages were not indexed.")
            if output_path.stat().st_size > limits.max_text_bytes + 10_000:
                raise LocalOcrFailure("OCR extracted text limit exceeded.")
            parsed = OcrResult.model_validate_json(output_path.read_bytes())
            if (
                set(parsed.pages) != set(pages)
                or sum(len(text.encode()) for text in parsed.pages.values()) > limits.max_text_bytes
            ):
                raise LocalOcrFailure("OCR output integrity or text limit check failed.")
            return parsed.pages
        except (OSError, ValueError) as exc:
            if isinstance(exc, LocalOcrFailure):
                raise
            raise LocalOcrFailure("Local OCR failed; affected pages were not indexed.") from exc
