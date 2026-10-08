"""Local ingestion CLI; private documents are never sent to a model or web provider."""

import argparse
import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.storage.documents import DocumentFailure, DocumentOptions, DocumentStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register a local PDF/DOCX/TXT document with located chunks."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--owner", default="local")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Opt in to local OCR for textless PDF pages (Python 3.12, ocr extra).",
    )
    args = parser.parse_args()
    try:
        directory = args.data_dir if args.data_dir is not None else load_settings().data_dir
        record = DocumentStore(
            directory / "documents", DocumentOptions(enable_ocr=args.ocr)
        ).ingest(args.path, args.owner)
    except (DocumentFailure, ConfigurationError) as exc:
        print(str(exc))
        return 1
    except (OSError, sqlite3.Error, ValidationError):
        print("Local ingestion configuration or storage failed; registration is unconfirmed.")
        return 1
    print(json.dumps(record.model_dump(mode="json"), indent=2))
    print("Use the document id with evidenceforge-research --document ID and the same --owner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
