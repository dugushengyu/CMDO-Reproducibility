#!/usr/bin/env python3
"""Install the seven Portable-only canonical archives from a reviewer asset ZIP."""
from __future__ import annotations
import argparse, csv, hashlib, io, subprocess, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "canonical_archives_manifest.csv"
DESTINATION = ROOT / "data" / "canonical_records"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.expanduser().resolve()
    if not bundle.is_file():
        raise SystemExit(f"Reviewer asset bundle not found: {bundle}")
    with MANIFEST.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 7:
        raise RuntimeError(f"expected 7 canonical archives in manifest, found {len(rows)}")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle) as outer:
        members_by_name: dict[str, list[zipfile.ZipInfo]] = {}
        for info in outer.infolist():
            if not info.is_dir():
                members_by_name.setdefault(Path(info.filename).name, []).append(info)
        for row in rows:
            name = row["archive"]
            matches = members_by_name.get(name, [])
            if len(matches) != 1:
                raise RuntimeError(f"expected exactly one {name} in reviewer asset bundle, found {len(matches)}")
            data = outer.read(matches[0])
            expected_size = int(row["size_bytes"])
            expected_sha = row["sha256"].lower()
            if len(data) != expected_size:
                raise RuntimeError(f"size mismatch for {name}: expected {expected_size}, got {len(data)}")
            actual_sha = sha256_bytes(data)
            if actual_sha != expected_sha:
                raise RuntimeError(f"SHA-256 mismatch for {name}: expected {expected_sha}, got {actual_sha}")
            with zipfile.ZipFile(io.BytesIO(data)) as inner:
                broken = inner.testzip()
                if broken:
                    raise RuntimeError(f"corrupt canonical ZIP {name}: {broken}")
            target = DESTINATION / name
            temporary = target.with_suffix(target.suffix + ".part")
            temporary.write_bytes(data)
            temporary.replace(target)
            print(f"installed exact canonical archive: {name}")
    result = subprocess.run([sys.executable, "scripts/verify_repository.py", "--require-canonical"], cwd=ROOT)
    if result.returncode:
        return result.returncode
    print("\nCMDO reviewer assets: INSTALLED AND BYTE-VERIFIED")
    print("Destination:", DESTINATION)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
