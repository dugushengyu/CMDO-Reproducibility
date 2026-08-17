#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".cmdo_stage" / "final56"
EXPECTED_ZIP_SHA256 = "8f00165021f2035c6708a7850026f81b380470ce676cad044bce5fd3e182302e"

parts = sorted(STAGE.glob("part_*.txt"))
if [p.name for p in parts] != [f"part_{i:02d}.txt" for i in range(1, 7)]:
    raise SystemExit(f"Expected six staged payload parts, found: {[p.name for p in parts]}")

payload = "".join(p.read_text(encoding="ascii").strip() for p in parts)
raw = base64.b64decode(payload, validate=True)
sha = hashlib.sha256(raw).hexdigest()
if sha != EXPECTED_ZIP_SHA256:
    raise SystemExit(f"Patch ZIP SHA-256 mismatch: {sha}")

with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
    bad = zf.testzip()
    if bad is not None:
        raise SystemExit(f"Corrupt member in staged patch ZIP: {bad}")
    for info in zf.infolist():
        target = (ROOT / info.filename).resolve()
        if ROOT.resolve() not in target.parents and target != ROOT.resolve():
            raise SystemExit(f"Unsafe archive path: {info.filename}")
    zf.extractall(ROOT)

print("Materialized final Figure 5/6 patch")
print("ZIP SHA-256:", sha)
