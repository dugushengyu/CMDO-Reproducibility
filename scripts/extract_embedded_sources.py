#!/usr/bin/env python3
"""Extract byte-exact Python payloads embedded in CMDO notebooks and b85 files.

The imported notebooks remain immutable.  This script only materializes the
embedded payloads and records both container and decoded SHA-256 values.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import zlib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "extracted_payloads_manifest.csv"


@dataclass(frozen=True)
class PayloadSpec:
    source: str
    output: str
    expected_sha256: str


SPECS = (
    PayloadSpec(
        "legacy/repaired_runnable/u0_u1/"
        "CrossModal_StageU0-U1_Universal_Observability_Law_Discovery_"
        "v0.1_SELF_CONTAINED_REPAIRED.ipynb",
        "legacy/extracted_authoritative/u0_u1/StageU0U1_pipeline_v0.1.py",
        "1d7f890abc87d4a0cd5b68cbd85723c59460acf1f6a8a3aaa8006e080f0661be",
    ),
    PayloadSpec(
        "legacy/original_authoritative/u3/"
        "CrossModal_StageU3A_Observability_Universality_Classes_v0.1_"
        "SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/u3/StageU3A_pipeline_v0.1.py",
        "782dd5768f7964a8ee8fe12061c90a2fb085eeb2d7117a5ad82df7687d1237ad",
    ),
    PayloadSpec(
        "legacy/original_authoritative/u3/"
        "CrossModal_StageU3C_AUTHORISED_Prospective_Reserve_v1.0.1_FINAL.ipynb",
        "legacy/extracted_authoritative/u3/StageU3C_pipeline_v1.0.1.py",
        "a57832c78591664cdee291804a1e73817c40378b74c120433e83c68a1cde4c5d",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/"
        "CrossModal_StageT2-MN_Censored_Model_Freeze_And_Provider_Prospective_"
        "Extension_v0.3_SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/t_series/StageT2MN_pipeline_v0.3.py",
        "f4aefd24f714c127635566ef0c637593fc8455655f585ae92904c245cb58aa50",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/"
        "CrossModal_StageT3-A_Locked_Blind_Sentinel_Scenario_Classification_And_"
        "Execution_v0.1_SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/t_series/StageT3A_pipeline_v0.1.py",
        "40d3d9f3b766e074471a7eee358f73301401aa76f5881ec24e6e34edee37970d",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/"
        "CrossModal_StageT3-X_Transparent_Blind_Failure_Autopsy_And_"
        "Observability_Decomposition_v0.1_SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/t_series/StageT3X_pipeline_v0.1.py",
        "d7cb0547a558b085efd2b1f459454f2fda8cb4229245b8e314ccb4b0702041d2",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/"
        "CrossModal_StageT4-ABC_Decomposed_Observability_And_MethodV1_"
        "Transparent_Validation_v0.1_SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/t_series/StageT4ABC_pipeline_v0.1.py",
        "cb0290cec21ab295e29a6d17177542db54d789966d5d9b2645d1860d818af6e9",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/"
        "CrossModal_StageT4-DE_Baseline_Anchored_MultiFunctional_Audit_v0.1_"
        "SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/t_series/StageT4DE_pipeline_v0.1.py",
        "965670a5fc2f2a8588f9f9a65c24eaeae5e1a4214767ade0c09f151414df065f",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/"
        "CrossModal_StageT4-FG_MethodV3_v0.1.3_CANONICAL_ZIP_LOADER_"
        "SELF_CONTAINED.ipynb",
        "legacy/extracted_authoritative/t_series/StageT4FG_pipeline_v0.1.3.py",
        "dfc9b497c2244735563a8ad44d70b49c4d16f1c7b4bc71894d13469fd67c7859",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/StageT2KR_CPU_pipeline_v0.4.b85",
        "legacy/extracted_authoritative/t_series/StageT2KR_CPU_pipeline_v0.4.py",
        "911ef861a53dcc0fb7e52c6f223e2d373d612fa556da702d7c116b957756d824",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/StageT2L_pipeline_v0.1.b85",
        "legacy/extracted_authoritative/t_series/StageT2L_pipeline_v0.1.py",
        "160627ebc4bd3a60cd609aed02f93ad2612c9db1467e08173c928abb81197440",
    ),
    PayloadSpec(
        "legacy/original_authoritative/t_series/StageT2MN_pipeline_v0.1.b85",
        "legacy/extracted_authoritative/t_series/history/"
        "StageT2MN_pipeline_v0.1.py",
        "e9a8e8f6b0dded1342c8b199341fcc7cf3dce0d98c81eaf1640f40ef28ea5c47",
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def notebook_payload(path: Path) -> bytes:
    notebook = json.loads(path.read_text(encoding="utf-8-sig"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    )
    match = re.search(r"payload\s*=\s*(['\"])(.*?)\1", code, re.DOTALL)
    if not match:
        raise ValueError(f"no payload assignment found in {path}")
    return zlib.decompress(base64.b85decode(match.group(2).encode("ascii")))


def extract(path: Path) -> bytes:
    if path.suffix.lower() == ".b85":
        return zlib.decompress(base64.b85decode(path.read_bytes().strip()))
    if path.suffix.lower() == ".ipynb":
        return notebook_payload(path)
    raise ValueError(f"unsupported payload container: {path}")


def run(check_only: bool) -> list[str]:
    errors: list[str] = []
    rows: list[dict[str, str | int]] = []
    for spec in SPECS:
        source = ROOT / spec.source
        output = ROOT / spec.output
        if not source.is_file():
            errors.append(f"missing payload container: {spec.source}")
            continue
        raw = source.read_bytes()
        try:
            decoded = extract(source)
        except Exception as exc:
            errors.append(f"cannot decode {spec.source}: {exc}")
            continue
        decoded_sha = sha256_bytes(decoded)
        if decoded_sha != spec.expected_sha256:
            errors.append(
                f"decoded hash mismatch for {spec.source}: "
                f"expected {spec.expected_sha256}, got {decoded_sha}"
            )
        if check_only:
            if not output.is_file():
                errors.append(f"missing extracted source: {spec.output}")
            elif output.read_bytes() != decoded:
                errors.append(f"extracted source differs from payload: {spec.output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(decoded)
        rows.append(
            {
                "container_path": spec.source,
                "container_bytes": len(raw),
                "container_sha256": sha256_bytes(raw),
                "extracted_path": spec.output,
                "extracted_bytes": len(decoded),
                "extracted_sha256": decoded_sha,
                "expected_extracted_sha256": spec.expected_sha256,
                "status": "PASS" if decoded_sha == spec.expected_sha256 else "FAIL",
            }
        )

    if not check_only:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with MANIFEST.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = run(args.check)
    if errors:
        print("Embedded-source extraction FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Embedded-source extraction PASS ({len(SPECS)} payloads)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
