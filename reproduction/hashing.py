"""Small, dependency-free hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, *, root: Path | None = None) -> dict[str, object]:
    resolved = path.resolve()
    relative = resolved.relative_to(root.resolve()) if root else resolved
    return {
        "path": relative.as_posix(),
        "size_bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def tree_records(paths: Iterable[Path], *, root: Path) -> list[dict[str, object]]:
    return [file_record(path, root=root) for path in sorted(paths)]


def canonical_json_sha256(payload: object) -> str:
    data = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
