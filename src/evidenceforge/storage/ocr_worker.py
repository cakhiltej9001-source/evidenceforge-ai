"""Private CPU OCR worker with packaged models, pixel bounds and no network requests."""

import json
import math
import sys
from contextlib import closing
from pathlib import Path

from evidenceforge.storage.ocr import OcrLimits, OcrResult


def run(input_path: Path, output_path: Path, job_path: Path) -> None:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]
    from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]

    job = json.loads(job_path.read_text(encoding="utf-8"))
    limits = OcrLimits.model_validate(job["limits"])
    requested = tuple(int(page) for page in job["pages"])
    if not requested or len(requested) > limits.max_pages:
        raise ValueError("page limit")
    # The pinned engine includes its ONNX models in the installed wheel.
    engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    output: dict[int, str] = {}
    total_bytes = 0
    with closing(pdfium.PdfDocument(input_path)) as document:
        for number in requested:
            if not 1 <= number <= len(document):
                raise ValueError("page range")
            with closing(document[number - 1]) as page:
                width, height = page.get_size()
                if not all(math.isfinite(value) and value > 0 for value in (width, height)):
                    raise ValueError("page dimensions")
                scale = min(
                    200 / 72,
                    math.sqrt(limits.max_pixels / (width * height)),
                    3000 / max(width, height),
                )
                if scale < 0.25:
                    raise ValueError("page dimensions")
                with closing(page.render(scale=scale)) as bitmap:
                    image = bitmap.to_numpy()
                    if image.shape[0] * image.shape[1] > limits.max_pixels + 6000:
                        raise ValueError("pixel limit")
                    lines, _ = engine(image)
                text = "\n".join(str(line[1]) for line in (lines or []) if float(line[2]) >= 0.7)
                total_bytes += len(text.encode())
                if total_bytes > limits.max_text_bytes:
                    raise ValueError("text limit")
                output[number] = text
    output_path.write_text(OcrResult(pages=output).model_dump_json(), encoding="utf-8")


if __name__ == "__main__":
    try:
        run(*(Path(argument) for argument in sys.argv[1:]))
    except Exception:
        # Suppress native/model errors that may contain private document text.
        raise SystemExit(1) from None
