"""Scoped, immutable UTF-8 artifacts with integrity checks and a retained-byte cap."""

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from evidenceforge.identity import stable_id
from evidenceforge.retrieval.contracts import ArtifactFailure
from evidenceforge.schemas import ArtifactReference


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


class ArtifactStore:
    def __init__(self, root: Path, owner_scope: str, run_id: str, max_bytes: int) -> None:
        self.root = root.resolve()
        self.scope = stable_id("artifacts", owner_scope, run_id)[-32:]
        self.directory = self.root / self.scope
        self.max_bytes = max_bytes

    def _path(self, key: str) -> Path:
        if self.directory.is_symlink():
            raise ArtifactFailure("Artifact scope cannot be a symbolic link.")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.directory.resolve()) or not path.is_relative_to(self.root):
            raise ArtifactFailure("Artifact scope/path invalid.")
        return path

    def put(self, text: str, parser: str) -> ArtifactReference:
        try:
            content = text.encode("utf-8")
            digest = hashlib.sha256(content).hexdigest()
            identifier = stable_id("artifact", self.scope, digest, parser)
            key = f"{self.scope}/{identifier[-32:]}.txt"
            path = self._path(key)
            if path.exists():
                if path.read_bytes() != content:
                    raise ArtifactFailure("Artifact integrity check failed.")
            else:
                existing_bytes = sum(p.stat().st_size for p in self.directory.glob("*.txt"))
                if existing_bytes + len(content) > self.max_bytes:
                    raise ArtifactFailure("Artifact byte limit reached.")
                atomic_write(path, content)
            return ArtifactReference(
                id=identifier,
                content_hash=digest,
                storage_key=key,
                parser_version=parser,
                byte_count=len(content),
            )
        except (OSError, UnicodeError) as exc:
            raise ArtifactFailure("Artifact write failed.") from exc

    def read(self, reference: ArtifactReference) -> str:
        try:
            path = self._path(reference.storage_key)
            if path.stat().st_size != reference.byte_count or reference.byte_count > self.max_bytes:
                raise ArtifactFailure("Artifact size check failed.")
            content = path.read_bytes()
            if len(content) != reference.byte_count or hashlib.sha256(content).hexdigest() != (
                reference.content_hash
            ):
                raise ArtifactFailure("Artifact integrity check failed.")
            return content.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise ArtifactFailure("Artifact read failed.") from exc
