"""Bounded local document parsing, immutable located chunks and scoped lexical search."""

import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path
from typing import Annotated, Literal, Self, cast
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.exceptions import InvalidXmlError
from docx.table import Table
from pydantic import AwareDatetime, Field, model_validator
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from evidenceforge.identity import stable_id
from evidenceforge.nodes.extraction import tokens
from evidenceforge.schemas import (
    Contract,
    Count,
    Digest,
    Identifier,
    Passage,
    PositiveCount,
    ResearchRequest,
    Text,
    utc_now,
)
from evidenceforge.storage.ocr import LocalOcrFailure, OcrLimits, transcribe_pdf

PARSER_VERSION = "located_document_v2"


class DocumentFailure(ValueError):
    """Expected local parsing, scope, format or integrity failure; message is sanitized."""


class DocumentOptions(Contract):
    max_file_bytes: PositiveCount = 4_000_000
    max_text_bytes: PositiveCount = 2_000_000
    max_pages: PositiveCount = 100
    max_units: PositiveCount = 2000
    max_chunks: PositiveCount = 3000
    chunk_chars: Annotated[PositiveCount, Field(le=5000)] = 1000
    overlap_chars: Count = 100
    max_zip_bytes: PositiveCount = 16_000_000
    max_owner_bytes: PositiveCount = 32_000_000
    enable_ocr: bool = False
    ocr: OcrLimits = Field(default_factory=OcrLimits)

    @model_validator(mode="after")
    def overlap_bound(self) -> Self:
        if self.overlap_chars >= self.chunk_chars:
            raise ValueError("overlap must be smaller than chunk size")
        return self


class DocumentRecord(Contract):
    id: Identifier
    owner_scope: Identifier
    title: Text
    format: Literal["pdf", "docx", "txt"]
    binary_hash: Digest
    text_hash: Digest
    byte_count: Count
    parser_version: Text = "located_document_v1"
    ingested_at: AwareDatetime
    status: Literal["ready", "partial", "textless"]
    warnings: tuple[Text, ...] = ()
    chunk_metadata_hash: Digest
    chunk_count: Count


class DocumentChunk(Contract):
    id: Identifier
    document_id: Identifier
    owner_scope: Identifier
    text: Passage
    content_hash: Digest
    start_offset: Count
    end_offset: PositiveCount
    page: PositiveCount | None = None
    paragraph: PositiveCount | None = None
    section: Text | None = None

    @model_validator(mode="after")
    def exact_length(self) -> Self:
        if self.end_offset - self.start_offset != len(self.text):
            raise ValueError("chunk offsets differ from text length")
        return self


class DocumentStore:
    def __init__(self, root: Path, options: DocumentOptions | None = None) -> None:
        self.root = root
        self.options = options or DocumentOptions()
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "documents.sqlite"
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS documents (owner TEXT, id TEXT, record TEXT, "
                "original BLOB, text TEXT, PRIMARY KEY(owner,id))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS chunks (owner TEXT, document TEXT, id TEXT, "
                "record TEXT, PRIMARY KEY(owner,id))"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS chunks_document ON chunks(owner,document)")

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def ingest(self, path: Path, owner_scope: str = "local") -> DocumentRecord:
        ResearchRequest(question="Document ingestion", owner_scope=owner_scope)
        kind = path.suffix.lower().lstrip(".")
        if kind not in {"pdf", "docx", "txt"}:
            raise DocumentFailure("Only PDF, DOCX and UTF-8 TXT documents are supported.")
        try:
            if path.stat().st_size > self.options.max_file_bytes:
                raise DocumentFailure("Document file size limit exceeded.")
            with path.open("rb") as stream:
                data = stream.read(self.options.max_file_bytes + 1)
            if len(data) > self.options.max_file_bytes:
                raise DocumentFailure("Document file size limit exceeded.")
            units, warnings = self.parse(data, kind)
        except DocumentFailure:
            raise
        except (
            OSError,
            UnicodeError,
            PdfReadError,
            BadZipFile,
            KeyError,
            TypeError,
            ValueError,
            SyntaxError,
            PackageNotFoundError,
            InvalidXmlError,
        ) as exc:
            raise DocumentFailure(
                "Document could not be parsed; no document was registered."
            ) from exc
        digest = hashlib.sha256(data).hexdigest()
        identifier = stable_id(
            "document",
            owner_scope,
            digest,
            kind,
            PARSER_VERSION,
            self.options.model_dump_json(),
            hashlib.sha256(json.dumps(units, ensure_ascii=False).encode()).hexdigest(),
        )
        text_parts: list[str] = []
        chunks: list[DocumentChunk] = []
        offset = 0
        for unit_index, (text, page, paragraph, section) in enumerate(units):
            if unit_index >= self.options.max_units:
                raise DocumentFailure("Document unit limit exceeded.")
            if text_parts:
                text_parts.append("\n\n")
                offset += 2
            text_parts.append(text)
            if offset + len(text) > self.options.max_text_bytes:
                raise DocumentFailure("Document extracted text limit exceeded.")
            for start in range(0, len(text), self.options.chunk_chars - self.options.overlap_chars):
                end = min(len(text), start + self.options.chunk_chars)
                passage = text[start:end]
                if not passage.strip():
                    continue
                if len(chunks) >= self.options.max_chunks:
                    raise DocumentFailure("Document chunk limit exceeded.")
                chunks.append(
                    DocumentChunk(
                        id=stable_id("chunk", identifier, offset + start, offset + end),
                        document_id=identifier,
                        owner_scope=owner_scope,
                        text=passage,
                        content_hash=hashlib.sha256(passage.encode()).hexdigest(),
                        start_offset=offset + start,
                        end_offset=offset + end,
                        page=page,
                        paragraph=paragraph,
                        section=section,
                    )
                )
                if end == len(text):
                    break
            offset += len(text)
        canonical = "".join(text_parts)
        if len(canonical.encode()) > self.options.max_text_bytes:
            raise DocumentFailure("Document extracted text limit exceeded.")
        status = "textless" if not chunks else "partial" if warnings else "ready"
        record = DocumentRecord(
            id=identifier,
            owner_scope=owner_scope,
            title=path.name,
            format=cast(Literal["pdf", "docx", "txt"], kind),
            binary_hash=digest,
            text_hash=hashlib.sha256(canonical.encode()).hexdigest(),
            byte_count=len(data),
            parser_version=PARSER_VERSION,
            ingested_at=utc_now(),
            status=cast(Literal["ready", "partial", "textless"], status),
            warnings=tuple(warnings),
            chunk_metadata_hash=hashlib.sha256(
                json.dumps(
                    [c.model_dump(mode="json") for c in sorted(chunks, key=lambda c: c.id)],
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
            chunk_count=len(chunks),
        )
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            old = conn.execute(
                "SELECT record FROM documents WHERE owner=? AND id=?", (owner_scope, identifier)
            ).fetchone()
            if old:
                return self.get(owner_scope, identifier)
            total = conn.execute(
                "SELECT COALESCE(SUM(length(original)),0) FROM documents WHERE owner=?",
                (owner_scope,),
            ).fetchone()[0]
            if total + len(data) > self.options.max_owner_bytes:
                raise DocumentFailure("Owner document storage limit exceeded.")
            conn.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?)",
                (owner_scope, identifier, record.model_dump_json(), data, canonical),
            )
            conn.executemany(
                "INSERT INTO chunks VALUES (?,?,?,?)",
                [(owner_scope, identifier, chunk.id, chunk.model_dump_json()) for chunk in chunks],
            )
        return record

    def parse(
        self, data: bytes, kind: str
    ) -> tuple[list[tuple[str, int | None, int | None, str | None]], list[str]]:
        units: list[tuple[str, int | None, int | None, str | None]] = []
        warnings: list[str] = []
        if kind == "txt":
            text = data.decode("utf-8-sig")
            if "\x00" in text:
                raise DocumentFailure("TXT must contain UTF-8 text without NUL characters.")
            units = [
                (part, None, index + 1, None)
                for index, part in enumerate(re.split(r"\n\s*\n", text))
                if part.strip()
            ]
        elif kind == "pdf":
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise DocumentFailure(
                    "Encrypted PDFs are unsupported; supply an unlocked local copy."
                )
            if len(reader.pages) > self.options.max_pages:
                raise DocumentFailure("PDF page limit exceeded.")
            textless_pages: list[int] = []
            for index, page in enumerate(reader.pages):
                stream = page.get_contents()
                if stream is not None and len(stream.get_data()) > self.options.max_zip_bytes:
                    raise DocumentFailure("PDF expanded page content limit exceeded.")
                text = page.extract_text() or ""
                if text.strip():
                    units.append((text, index + 1, None, None))
                else:
                    textless_pages.append(index + 1)
            ocr_pages: dict[int, str] = {}
            ocr_failure: str | None = None
            if textless_pages and self.options.enable_ocr:
                try:
                    ocr_pages = transcribe_pdf(
                        data,
                        tuple(textless_pages[: self.options.ocr.max_pages]),
                        self.options.ocr,
                        self.root,
                    )
                except LocalOcrFailure as exc:
                    ocr_failure = str(exc)
            for number in textless_pages:
                text = ocr_pages.get(number, "")
                if text.strip():
                    units.append((text, number, None, "local OCR transcription"))
                    warnings.append(
                        f"Page {number} was transcribed by local OCR. Quotations and offsets "
                        "refer to the OCR transcript, not embedded PDF text; verify "
                        "wording, numbers and layout against the original page image."
                    )
                elif not self.options.enable_ocr:
                    warnings.append(
                        f"Page {number} has no extractable text; "
                        "it may be scanned or blank. OCR is unavailable unless enabled "
                        "with the local ocr extra and --ocr."
                    )
                elif ocr_failure:
                    warnings.append(f"Page {number} was not indexed. {ocr_failure}")
                elif number not in ocr_pages:
                    warnings.append(f"Page {number} was not indexed; OCR page limit exceeded.")
                else:
                    warnings.append(
                        f"Page {number} has no retained OCR text; it may be blank, "
                        "unreadable or below the recognition confidence threshold."
                    )
            units.sort(key=lambda unit: unit[1] or 0)
        else:
            with ZipFile(io.BytesIO(data)) as archive:
                if (
                    len(archive.infolist()) > self.options.max_units
                    or sum(item.file_size for item in archive.infolist())
                    > self.options.max_zip_bytes
                ):
                    raise DocumentFailure("DOCX expanded archive limit exceeded.")
            document = Document(io.BytesIO(data))
            paragraph = 0
            table_number = 0
            for block in document.iter_inner_content():
                if isinstance(block, Table):
                    table_number += 1
                    for row_index, row in enumerate(block.rows):
                        paragraph += 1
                        # Keep a row together so retrieval retains which value
                        # belongs to which entity. Empty cells preserve alignment.
                        text = " | ".join(cell.text for cell in row.cells)
                        if any(cell.text.strip() for cell in row.cells):
                            units.append(
                                (
                                    text,
                                    None,
                                    paragraph,
                                    f"table {table_number}, row {row_index + 1}, "
                                    f"columns 1-{len(row.cells)}",
                                )
                            )
                else:
                    paragraph += 1
                    if block.text.strip():
                        units.append((block.text, None, paragraph, None))
            warnings.append(
                "DOCX indexes body paragraphs and table rows (cells separated by |); "
                "headers, footers, "
                "drawings and tracked changes are not indexed."
            )
        if not units and not warnings:
            warnings.append("Document has no extractable text; no evidence chunks were indexed.")
        if len(units) > self.options.max_units:
            raise DocumentFailure("Document unit limit exceeded.")
        return units, warnings

    def get(self, owner: str, identifier: str) -> DocumentRecord:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT record,original,text FROM documents WHERE owner=? AND id=?",
                (owner, identifier),
            ).fetchone()
        if row is None:
            raise DocumentFailure("Document is unavailable in the requested owner scope.")
        record = DocumentRecord.model_validate_json(row[0])
        if (
            record.owner_scope != owner
            or record.id != identifier
            or len(row[1]) != record.byte_count
            or hashlib.sha256(row[1]).hexdigest() != record.binary_hash
            or hashlib.sha256(row[2].encode()).hexdigest() != record.text_hash
        ):
            raise DocumentFailure("Stored document integrity check failed.")
        return record

    def chunks(self, owner: str, identifier: str) -> tuple[DocumentChunk, ...]:
        record = self.get(owner, identifier)
        with self.connect() as conn:
            text = conn.execute(
                "SELECT text FROM documents WHERE owner=? AND id=?", (owner, identifier)
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT record FROM chunks WHERE owner=? AND document=? ORDER BY id",
                (owner, identifier),
            ).fetchall()
        chunks = tuple(DocumentChunk.model_validate_json(row[0]) for row in rows)
        metadata_hash = hashlib.sha256(
            json.dumps([c.model_dump(mode="json") for c in chunks], sort_keys=True).encode()
        ).hexdigest()
        if (
            metadata_hash != record.chunk_metadata_hash
            or len(chunks) != record.chunk_count
            or any(
                c.id != stable_id("chunk", identifier, c.start_offset, c.end_offset)
                or c.owner_scope != owner
                or c.document_id != identifier
                or text[c.start_offset : c.end_offset] != c.text
                or hashlib.sha256(c.text.encode()).hexdigest() != c.content_hash
                for c in chunks
            )
        ):
            raise DocumentFailure("Stored chunk integrity check failed.")
        return chunks

    def search(
        self, owner: str, identifiers: tuple[str, ...], query: str, limit: int = 5
    ) -> tuple[DocumentChunk, ...]:
        if not 1 <= limit <= 20 or len(identifiers) > 64:
            raise DocumentFailure("Document search limit exceeded.")
        wanted = tokens(query)
        ranked: list[tuple[float, DocumentChunk]] = []
        for identifier in identifiers:
            for chunk in self.chunks(owner, identifier):
                score = len(wanted & tokens(chunk.text)) / len(wanted) if wanted else 0.0
                if score:
                    ranked.append((score, chunk))
        return tuple(
            chunk for _, chunk in sorted(ranked, key=lambda item: (-item[0], item[1].id))[:limit]
        )
