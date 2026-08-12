#!/usr/bin/env python3
"""License-free integrity checks used locally and by GitHub Actions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_MALFORMED_NOTEBOOK = ROOT / (
    "legacy/original_authoritative/u0_u1/"
    "CrossModal_StageU0-U1_Universal_Observability_Law_Discovery_"
    "v0.1_SELF_CONTAINED.ipynb"
)
MAX_GIT_FILE_BYTES = 90 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_hash_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.DictReader(stream)
        for row in rows:
            rel = row["repository_path"]
            target = (ROOT / rel).resolve()
            if ROOT not in target.parents:
                errors.append(f"unsafe manifest path: {rel}")
                continue
            if not target.is_file():
                errors.append(f"manifest file missing: {rel}")
                continue
            expected = (row.get("repository_sha256") or row.get("sha256") or "").lower()
            if not expected:
                errors.append(f"manifest row lacks SHA-256: {rel}")
                continue
            if row.get("size_bytes") and target.stat().st_size != int(row["size_bytes"]):
                errors.append(
                    f"size mismatch: {rel}: expected {row['size_bytes']}, "
                    f"got {target.stat().st_size}"
                )
                continue
            actual = sha256(target)
            if actual != expected:
                errors.append(
                    f"hash mismatch: {rel}: expected {expected}, got {actual}"
                )
    return errors


def verify_package_text_manifest(directory: Path, manifest_name: str) -> list[str]:
    errors: list[str] = []
    manifest = directory / manifest_name
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        target = directory / rel.strip()
        if not target.is_file() or sha256(target) != expected:
            errors.append(f"sealed package hash mismatch: {target.relative_to(ROOT)}")
    return errors


def verify_u9_manifest() -> list[str]:
    errors: list[str] = []
    directory = ROOT / "matlab/stages/u9/v1_0_preoutcome"
    with (directory / "PACKAGE_MANIFEST_SHA256_v1_0.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        for row in csv.DictReader(stream):
            target = directory / row["filename"]
            if not target.is_file():
                errors.append(f"U9 package file missing: {row['filename']}")
                continue
            if target.stat().st_size != int(row["bytes"]) or sha256(target) != row["sha256"]:
                errors.append(f"U9 package hash mismatch: {row['filename']}")
    return errors


def verify_canonical_archives(required: bool) -> tuple[list[str], bool]:
    """Verify portable-only canonical archives when present or required."""

    errors: list[str] = []
    directory = ROOT / "data/canonical_records"
    manifest = ROOT / "provenance/canonical_archives_manifest.csv"
    present = directory.is_dir() and any(directory.glob("*.zip"))
    if not required and not present:
        return errors, False

    with manifest.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            target = directory / row["archive"]
            if not target.is_file():
                errors.append(f"canonical archive missing: {row['archive']}")
                continue
            if target.stat().st_size != int(row["size_bytes"]):
                errors.append(f"canonical archive size mismatch: {row['archive']}")
                continue
            if sha256(target) != row["sha256"].lower():
                errors.append(f"canonical archive hash mismatch: {row['archive']}")
                continue
            try:
                with zipfile.ZipFile(target) as archive:
                    broken = archive.testzip()
                    if broken:
                        errors.append(
                            f"canonical archive has corrupt member: "
                            f"{row['archive']}::{broken}"
                        )
            except Exception as exc:
                errors.append(f"invalid canonical archive: {row['archive']}: {exc}")
    return errors, True


def verify_optional_frozen_assets() -> list[str]:
    errors: list[str] = []
    manifest = ROOT / "provenance/frozen_assets_manifest.csv"
    if not manifest.is_file():
        return ["missing provenance/frozen_assets_manifest.csv"]
    with manifest.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            target = ROOT / row["repository_path"]
            # These assets are deliberately omitted from an ordinary Git clone.
            if not target.exists():
                continue
            if target.stat().st_size != int(row["size_bytes"]):
                errors.append(f"frozen asset size mismatch: {row['repository_path']}")
            elif sha256(target) != row["sha256"]:
                errors.append(f"frozen asset hash mismatch: {row['repository_path']}")
    return errors


def verify_optional_portable_bootstraps() -> list[str]:
    errors: list[str] = []
    root = ROOT / "bootstrap_inputs/portable"
    if not root.is_dir():
        return errors
    manifest_path = ROOT / "provenance/portable_bootstrap_manifest.json"
    try:
        outer = json.loads(manifest_path.read_text(encoding="utf-8"))
        declared = {row["file"]: row for row in outer["files"]}
        for name, row in declared.items():
            path = root / name
            if not path.is_file():
                errors.append(f"portable bootstrap declared but absent: {name}")
                continue
            if path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
                errors.append(f"portable bootstrap outer identity mismatch: {name}")
    except Exception as exc:
        errors.append(f"invalid portable bootstrap outer manifest: {exc}")
    for bundle in sorted(root.glob("*.zip")):
        try:
            with zipfile.ZipFile(bundle) as archive:
                broken = archive.testzip()
                if broken:
                    errors.append(f"portable bootstrap corrupt member: {bundle.name}: {broken}")
                    continue
                if "BOOTSTRAP_MANIFEST.json" not in archive.namelist():
                    errors.append(f"portable bootstrap lacks BOOTSTRAP_MANIFEST.json: {bundle.name}")
                    continue
                manifest = json.loads(archive.read("BOOTSTRAP_MANIFEST.json"))
                rows = manifest.get("files", [])
                if int(manifest.get("file_count", len(rows))) != len(rows):
                    errors.append(f"portable bootstrap file_count mismatch: {bundle.name}")
                for row in rows:
                    rel = row["relative_path"]
                    if rel not in archive.namelist():
                        errors.append(f"portable bootstrap member missing: {bundle.name}: {rel}")
                        continue
                    data = archive.read(rel)
                    if len(data) != int(row["size_bytes"]):
                        errors.append(f"portable bootstrap size mismatch: {bundle.name}: {rel}")
                    if hashlib.sha256(data).hexdigest() != row["sha256"]:
                        errors.append(f"portable bootstrap SHA mismatch: {bundle.name}: {rel}")
        except Exception as exc:
            errors.append(f"invalid portable bootstrap {bundle.name}: {exc}")
    aborted = root / "Stage11E-R_Protocol_Seal_v0.1_ABORTED_PREEXECUTION_MIXED_ENDPOINT_ASSUMPTION.json"
    if aborted.exists():
        expected = "7f5a6450c3341fb1ef067dff5b89f186ce0142fdc8d38648607cd74843fa1a77"
        if aborted.stat().st_size != 2370 or sha256(aborted) != expected:
            errors.append("Stage11E-R aborted historical protocol bootstrap identity mismatch")
    return errors


def verify_reproduction_metadata() -> list[str]:
    errors: list[str] = []
    try:
        sys.path.insert(0, str(ROOT))
        from reproduction.dag import ReproductionDAG

        dag = ReproductionDAG(ROOT / "provenance/reproduction_dag.json")
        for stage in dag.stages.values():
            if stage.source and not (ROOT / stage.source).is_file():
                errors.append(f"DAG source missing: {stage.id}: {stage.source}")
        full = dag.select("full-claim")
        full_ids = [stage.id for stage in full]
        if not any(stage.id == "u2_train_replay" for stage in full):
            errors.append("full-claim DAG does not contain U2 fresh training")
        if any("u9" in stage.id.lower() for stage in full):
            errors.append("full-claim DAG must not auto-run U9")
        if len(full_ids) != 55:
            errors.append(f"full-claim DAG must declare 55 nodes, found {len(full_ids)}")
        try:
            if not (full_ids.index("t2f_covariate_balance") < full_ids.index("t3pf_preflight") < full_ids.index("t2g_hierarchy")):
                errors.append("full-claim DAG must order T2-F -> T3-PF -> T2-G")
        except ValueError:
            errors.append("full-claim DAG lacks T2-F/T3-PF/T2-G structural nodes")

        archival = dag.select("archival-continuation")
        archival_ids = [stage.id for stage in archival]
        if "t2d_witness" in archival_ids or "t2e_baselines" in archival_ids:
            errors.append("archival-continuation must not execute fresh T2-D/T2-E")
        if "t2f_covariate_balance" in archival_ids:
            errors.append("archival-continuation must not re-execute T2-F after the disclosed exact-parent numerical boundary")
        for required in ("archival_preflight", "t3pf_preflight", "t2g_hierarchy", "u8_nhanes_reconstruction"):
            if required not in archival_ids:
                errors.append(f"archival-continuation lacks {required}")
        if any("u9" in stage_id.lower() for stage_id in archival_ids):
            errors.append("archival-continuation must not auto-run U9")
        try:
            if not (archival_ids.index("archival_preflight") < archival_ids.index("t3pf_preflight") < archival_ids.index("t2g_hierarchy")):
                errors.append("archival-continuation must order archival preflight -> T3-PF -> T2-G")
        except ValueError:
            pass
    except Exception as exc:
        errors.append(f"invalid reproduction DAG: {exc}")

    datasets_path = ROOT / "provenance/datasets.json"
    try:
        datasets = json.loads(datasets_path.read_text(encoding="utf-8"))
        ids = [row["id"] for row in datasets["datasets"]]
        if len(ids) != len(set(ids)):
            errors.append("duplicate dataset id in provenance/datasets.json")
        for row in datasets["datasets"]:
            for field in ("id", "official_url", "acquisition", "license", "redistribution"):
                if not row.get(field):
                    errors.append(f"dataset {row.get('id')} lacks {field}")
        eicu = next((row for row in datasets["datasets"] if row["id"] == "EICU_CRD"), None)
        if not eicu or eicu.get("required_for"):
            errors.append("eICU/U9 must remain excluded from default profiles")
    except Exception as exc:
        errors.append(f"invalid dataset registry: {exc}")

    receipts_path = ROOT / "provenance/historical_receipts.json"
    try:
        receipts = json.loads(receipts_path.read_text(encoding="utf-8"))
        rows = receipts["files"]
        if len(rows) != 6:
            errors.append(f"historical receipt manifest must declare six files, found {len(rows)}")
        if len({row["id"] for row in rows}) != len(rows):
            errors.append("historical receipt manifest contains duplicate IDs")
        if len({row["relative_path"] for row in rows}) != len(rows):
            errors.append("historical receipt manifest contains duplicate paths")
        for row in rows:
            if int(row.get("size_bytes", 0)) <= 0 or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", ""))):
                errors.append(f"invalid historical receipt identity: {row.get('id')}")
    except Exception as exc:
        errors.append(f"invalid historical receipt manifest: {exc}")

    boundary_path = ROOT / "provenance/scientific_boundaries.json"
    try:
        boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
        if boundary.get("fresh_full_claim", {}).get("stage") != "t2d_witness":
            errors.append("scientific boundary must identify T2-D as the fresh full-claim stop")
        if boundary.get("fresh_full_claim", {}).get("exit_code") != 4:
            errors.append("scientific boundary exit code must be 4")
        if boundary.get("u9_excluded") is not True:
            errors.append("scientific boundary manifest must keep U9 excluded")
        if boundary.get("archival_continuation", {}).get("fresh_raw_to_science_reproduction") is not False:
            errors.append("archival continuation must be explicitly non-fresh")
    except Exception as exc:
        errors.append(f"invalid scientific boundary manifest: {exc}")

    audit_path = ROOT / "provenance/container_revision_audit.json"
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        for row in audit["records"]:
            if row["pipeline_status"] != "BYTE_VERIFIED":
                errors.append(f"unverified extracted pipeline: {row['stage']}")
    except Exception as exc:
        errors.append(f"invalid container-revision audit: {exc}")

    u2_reference = ROOT / "provenance/u2_frozen_metrics.csv"
    try:
        with u2_reference.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 38 or len({row["target"] for row in rows}) != 38:
            errors.append("U2 frozen metric reference must contain 38 unique targets")
    except Exception as exc:
        errors.append(f"invalid U2 frozen metric reference: {exc}")
    return errors


def first_matlab_function(text: str) -> str | None:
    match = re.search(
        r"^\s*function\s+(?:\[[^\]]+\]|[A-Za-z]\w*)\s*=\s*([A-Za-z]\w*)"
        r"|^\s*function\s+([A-Za-z]\w*)\s*(?:\(|$)",
        text,
        re.MULTILINE,
    )
    return (match.group(1) or match.group(2)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-canonical",
        action="store_true",
        help="require and byte-verify all seven portable canonical archives",
    )
    args = parser.parse_args()
    errors: list[str] = []

    for manifest in (
        ROOT / "provenance/drive_import_manifest.csv",
        ROOT / "provenance/drive_supporting_import_manifest.csv",
        ROOT / "provenance/imported_legacy_sources.csv",
    ):
        errors.extend(verify_hash_manifest(manifest))

    errors.extend(
        verify_package_text_manifest(
            ROOT / "matlab/stages/u8/v1_0_preoutcome",
            "PACKAGE_SHA256_v1_0_1.txt",
        )
    )
    errors.extend(
        verify_package_text_manifest(
            ROOT / "matlab/stages/u8/v1_1_canonical",
            "PACKAGE_SHA256_v1_1_0.txt",
        )
    )
    errors.extend(verify_u9_manifest())
    errors.extend(verify_optional_frozen_assets())
    errors.extend(verify_optional_portable_bootstraps())
    errors.extend(verify_reproduction_metadata())
    canonical_errors, canonical_checked = verify_canonical_archives(
        args.require_canonical
    )
    errors.extend(canonical_errors)

    ignored_scan_roots = {".git", ".venv", "outputs", "dist"}
    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if not path.is_file() or any(part in ignored_scan_roots or part.startswith(".venv") for part in relative_parts):
            continue
        rel = path.relative_to(ROOT)
        if path.stat().st_size > MAX_GIT_FILE_BYTES:
            errors.append(f"file exceeds 90 MiB Git safety limit: {rel}")

        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                errors.append(f"invalid JSON: {rel}: {exc}")

        if path.suffix.lower() == ".ipynb":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                if path.resolve() != KNOWN_MALFORMED_NOTEBOOK.resolve():
                    errors.append(f"invalid notebook JSON: {rel}: {exc}")

        if path.suffix.lower() == ".py":
            try:
                compile(path.read_text(encoding="utf-8-sig"), str(rel), "exec")
            except Exception as exc:
                errors.append(f"Python compile failure: {rel}: {exc}")

        if path.suffix.lower() == ".m":
            text = path.read_text(encoding="utf-8-sig")
            function_name = first_matlab_function(text)
            if function_name and function_name != path.stem:
                errors.append(
                    f"MATLAB function/file mismatch: {rel}: {function_name}"
                )

    repaired = ROOT / (
        "legacy/repaired_runnable/u0_u1/"
        "CrossModal_StageU0-U1_Universal_Observability_Law_Discovery_"
        "v0.1_SELF_CONTAINED_REPAIRED.ipynb"
    )
    try:
        repaired_payload = json.loads(repaired.read_text(encoding="utf-8-sig"))
        for index, cell in enumerate(repaired_payload.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if source.strip():
                compile(source, f"{repaired.name}:cell-{index}", "exec")
    except Exception as exc:
        errors.append(f"U0-U1 repaired notebook code is invalid: {exc}")

    workbook = ROOT / "source_data/SourceData_Figure5_U7_U8_and_ED7_U8.xlsx"
    if not workbook.is_file():
        errors.append(f"missing source workbook: {workbook.relative_to(ROOT)}")
    else:
        try:
            with zipfile.ZipFile(workbook) as archive:
                broken = archive.testzip()
                if broken:
                    errors.append(f"source workbook has a corrupt member: {broken}")
        except Exception as exc:
            errors.append(f"invalid source workbook: {exc}")

    active_matlab = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for path in (ROOT / "matlab").rglob("*.m")
    )
    if "F:\\CMDO" in active_matlab:
        errors.append("active MATLAB still contains hard-coded F:\\CMDO")

    if errors:
        print("CMDO repository integrity FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("CMDO repository integrity PASS")
    print("- imported-source hashes verified")
    print("- reproduction DAG, dataset registry and replay rules verified")
    print("- extracted pipeline/container-revision commitments verified")
    print("- sealed U8/U9 package hashes verified")
    print("- JSON/notebooks/Python/function filenames checked")
    print("- source workbook ZIP structure checked")
    if canonical_checked:
        print("- seven portable canonical archives byte-verified")
    print("- no active hard-coded F:\\CMDO path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
