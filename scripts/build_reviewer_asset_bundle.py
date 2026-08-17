#!/usr/bin/env python3
"""Build a deterministic seven-archive reviewer asset ZIP."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "canonical_archives_manifest.csv"
CANONICAL = ROOT / "data" / "canonical_records"
FIXED_TIME = (2026, 8, 17, 0, 0, 0)
BUNDLE_VERSION = "v1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_member(archive: zipfile.ZipFile, name: str, data: bytes, *, stored: bool = False) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
    info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    archive.writestr(info, data, compresslevel=None if stored else 9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "CMDO-Reviewer-Assets-v1.0.zip")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()

    manifest_bytes = MANIFEST.read_bytes()
    with MANIFEST.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 7:
        raise RuntimeError(f"expected 7 canonical archives, found {len(rows)}")

    verified: list[tuple[dict[str, str], Path]] = []
    for row in rows:
        path = CANONICAL / row["archive"]
        if not path.is_file():
            raise RuntimeError(f"missing canonical archive: {path}")
        if path.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError(f"size mismatch: {path.name}")
        if sha256_file(path) != row["sha256"].lower():
            raise RuntimeError(f"SHA-256 mismatch: {path.name}")
        with zipfile.ZipFile(path) as inner:
            broken = inner.testzip()
            if broken:
                raise RuntimeError(f"corrupt canonical archive {path.name}: {broken}")
        verified.append((row, path))

    if not args.verify_only:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        info = {
            "schema_version": 1,
            "classification": "CMDO_REVIEWER_CANONICAL_ASSET_BUNDLE",
            "bundle_version": BUNDLE_VERSION,
            "canonical_archive_count": 7,
            "canonical_manifest_sha256": sha256_bytes(manifest_bytes),
            "raw_restricted_data_included": False,
            "u9_eicu_data_included": False,
        }
        info_bytes = (json.dumps(info, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
            write_member(archive, "provenance/canonical_archives_manifest.csv", manifest_bytes)
            write_member(archive, "REVIEWER_ASSET_BUNDLE_INFO.json", info_bytes)
            for _, path in verified:
                write_member(archive, f"data/canonical_records/{path.name}", path.read_bytes(), stored=True)

    if not output.is_file():
        raise RuntimeError(f"reviewer asset bundle not found: {output}")
    with zipfile.ZipFile(output) as outer:
        broken = outer.testzip()
        if broken:
            raise RuntimeError(f"output asset bundle corrupt member: {broken}")
        info = json.loads(outer.read("REVIEWER_ASSET_BUNDLE_INFO.json"))
        if info["canonical_archive_count"] != 7 or info["u9_eicu_data_included"] is not False:
            raise RuntimeError("reviewer asset bundle metadata mismatch")
        for row, _ in verified:
            name = f"data/canonical_records/{row['archive']}"
            data = outer.read(name)
            if len(data) != int(row["size_bytes"]) or sha256_bytes(data) != row["sha256"].lower():
                raise RuntimeError(f"outer bundle member mismatch: {row['archive']}")

    checksum = sha256_file(output)
    checksum_path = output.with_suffix(output.suffix + ".sha256.txt")
    checksum_path.write_text(f"{checksum}  {output.name}\n", encoding="utf-8", newline="\n")
    print("CMDO reviewer asset bundle: PASS")
    print("Bundle :", output)
    print("SHA256:", checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
