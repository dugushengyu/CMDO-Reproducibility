#!/usr/bin/env python3
"""Verify every file recorded in the CMDO submission-v2 SHA-256 manifest."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from build_submission_v2_manifest import V2_SCOPE

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "submission_v2_manifest.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not MANIFEST.is_file():
        raise SystemExit(f"Missing submission-v2 manifest: {MANIFEST}")

    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    expected = [p.replace("/", "\\") for p in V2_SCOPE]
    paths = [r["path"] for r in rows]

    if len(paths) != len(set(paths)):
        raise SystemExit("Duplicate path(s) in submission-v2 manifest")
    if paths != expected:
        missing = [p for p in expected if p not in paths]
        extra = [p for p in paths if p not in expected]
        raise SystemExit(
            "Manifest scope/order differs from frozen V2_SCOPE"
            f"\nmissing={missing}\nextra={extra}"
        )

    failures: list[str] = []
    for row in rows:
        rel = row["path"].replace("\\", "/")
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"MISSING {rel}")
            continue
        expected_bytes = int(row["bytes"])
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            failures.append(f"SIZE {rel}: expected {expected_bytes}, found {actual_bytes}")
            continue
        expected_sha = row["sha256"].lower()
        actual_sha = sha256(path)
        if actual_sha != expected_sha:
            failures.append(f"SHA {rel}: expected {expected_sha}, found {actual_sha}")

    if failures:
        raise SystemExit("Submission-v2 manifest verification FAILED:\n" + "\n".join(failures))

    print(f"PASS SUBMISSION V2 MANIFEST: {len(rows)}/{len(rows)} files match bytes + SHA-256")
    print(f"manifest_sha256={sha256(MANIFEST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
