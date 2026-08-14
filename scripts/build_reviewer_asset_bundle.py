#!/usr/bin/env python3
"""Build the submission reviewer asset ZIP from locally installed canonical archives."""
from __future__ import annotations
import argparse, csv, hashlib, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "canonical_archives_manifest.csv"
CANONICAL = ROOT / "data" / "canonical_records"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "CMDO-Reviewer-Assets-v1.0.zip")
    args = parser.parse_args()
    with MANIFEST.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 7:
        raise RuntimeError(f"expected 7 canonical archives, found {len(rows)}")
    verified: list[Path] = []
    for row in rows:
        path = CANONICAL / row["archive"]
        if not path.is_file():
            raise RuntimeError(f"missing canonical archive: {path}")
        if path.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError(f"size mismatch: {path.name}")
        if sha256(path) != row["sha256"].lower():
            raise RuntimeError(f"SHA-256 mismatch: {path.name}")
        with zipfile.ZipFile(path) as archive:
            broken = archive.testzip()
            if broken:
                raise RuntimeError(f"corrupt canonical archive {path.name}: {broken}")
        verified.append(path)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(MANIFEST, "provenance/canonical_archives_manifest.csv")
        for path in verified:
            archive.write(path, f"data/canonical_records/{path.name}")
    with zipfile.ZipFile(output) as archive:
        broken = archive.testzip()
        if broken:
            raise RuntimeError(f"output asset bundle corrupt member: {broken}")
    checksum = sha256(output)
    checksum_path = output.with_suffix(output.suffix + ".sha256.txt")
    checksum_path.write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    print("CMDO reviewer asset bundle: PASS")
    print("Bundle :", output)
    print("SHA256:", checksum)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
