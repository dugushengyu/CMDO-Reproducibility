#!/usr/bin/env python3
"""Build or verify deterministic provenance manifests for the reviewer package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "provenance"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sorted_files(directory: Path) -> list[Path]:
    """Return files in a platform-independent canonical path order."""
    return sorted(
        (item for item in directory.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(ROOT).as_posix(),
    )


def csv_text(rows: list[dict[str, object]], fieldnames: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def imported_source_manifest() -> str:
    roots = [
        ROOT / "legacy/original_authoritative",
        ROOT / "legacy/extracted_authoritative",
        ROOT / "legacy/repaired_runnable",
    ]
    rows = []
    for directory in roots:
        for path in _sorted_files(directory):
            rows.append(
                {
                    "repository_path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "authority": (
                        "EXTRACTED_BYTE_EXACT_PAYLOAD"
                        if "extracted_authoritative" in path.parts
                        else "NON_AUTHORITATIVE_RUNNABLE_REPAIR"
                        if "repaired_runnable" in path.parts
                        else "DRIVE_IMPORTED_AUTHORITATIVE_CONTAINER"
                    ),
                }
            )
    return csv_text(rows, ["repository_path", "size_bytes", "sha256", "authority"])


def frozen_asset_manifest() -> str:
    roots = [ROOT / "data/canonical_records", ROOT / "data/frozen_assets"]
    rows = []
    for directory in roots:
        if not directory.exists():
            continue
        for path in _sorted_files(directory):
            relative = path.relative_to(ROOT).as_posix()
            role = (
                "FIGURE_CANONICAL_RECORD"
                if "canonical_records" in path.parts
                else "U2_AUTHORITATIVE_CHECKPOINT"
                if path.suffix == ".pt"
                else "U2_AUTHORITATIVE_PREDICTION_OR_METADATA_CACHE"
            )
            rows.append(
                {
                    "repository_path": relative,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "role": role,
                    "distribution": "PORTABLE_BUNDLE_ONLY_GITIGNORED",
                }
            )
    return csv_text(
        rows,
        ["repository_path", "size_bytes", "sha256", "role", "distribution"],
    )


def u2_frozen_metrics() -> str | None:
    directory = (
        ROOT
        / "data/frozen_assets/u2/environment_prediction_cache_v0.1.7_AUTHORITATIVE_EPOCH12"
    )
    if not directory.is_dir():
        return None
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - only needed while building portable bundle
        raise RuntimeError("NumPy is required to build U2 frozen metrics") from exc
    rows = []
    scalar_fields = [
        "target",
        "family",
        "n",
        "prevalence",
        "threshold",
        "auc",
        "auprc",
        "balanced_accuracy",
        "brier",
        "log_loss",
    ]
    for path in sorted(directory.glob("*.npz"), key=lambda item: item.name):
        with np.load(path, allow_pickle=False) as payload:
            row = {field: payload[field].item() for field in scalar_fields}
        row["cache_file"] = path.name
        row["cache_sha256"] = sha256(path)
        rows.append(row)
    return csv_text(
        rows,
        ["cache_file", *scalar_fields, "cache_sha256"],
    )


def revision_audit() -> str:
    definitions = [
        {
            "stage": "T3-X",
            "notebook": "legacy/original_authoritative/t_series/CrossModal_StageT3-X_Transparent_Blind_Failure_Autopsy_And_Observability_Decomposition_v0.1_SELF_CONTAINED.ipynb",
            "release": "legacy/original_authoritative/t_series/StageT3-X_Notebook_Release_Manifest_v0.1.json",
            "release_notebook_hash_key": "notebook_sha256",
            "release_notebook_bytes_key": "notebook_bytes",
            "release_pipeline_hash_key": "decoded_source_sha256",
            "pipeline": "legacy/extracted_authoritative/t_series/StageT3X_pipeline_v0.1.py",
        },
        {
            "stage": "T4-DE",
            "notebook": "legacy/original_authoritative/t_series/CrossModal_StageT4-DE_Baseline_Anchored_MultiFunctional_Audit_v0.1_SELF_CONTAINED.ipynb",
            "release": "legacy/original_authoritative/t_series/StageT4-DE_Notebook_Release_Manifest_v0.1.json",
            "release_notebook_hash_key": "notebook_sha256",
            "release_notebook_bytes_key": None,
            "release_pipeline_hash_key": "embedded_pipeline_sha256",
            "pipeline": "legacy/extracted_authoritative/t_series/StageT4DE_pipeline_v0.1.py",
        },
        {
            "stage": "T4-FG",
            "notebook": "legacy/original_authoritative/t_series/CrossModal_StageT4-FG_MethodV3_v0.1.3_CANONICAL_ZIP_LOADER_SELF_CONTAINED.ipynb",
            "release": "legacy/original_authoritative/t_series/StageT4-FG_Notebook_Release_Manifest_v0.1.3.json",
            "release_notebook_hash_key": "notebook_sha256",
            "release_notebook_bytes_key": None,
            "release_pipeline_hash_key": "pipeline_sha256",
            "pipeline": "legacy/extracted_authoritative/t_series/StageT4FG_pipeline_v0.1.3.py",
        },
    ]
    rows = []
    for definition in definitions:
        notebook = ROOT / definition["notebook"]
        release = json.loads((ROOT / definition["release"]).read_text(encoding="utf-8"))
        pipeline = ROOT / definition["pipeline"]
        expected_container_hash = release[definition["release_notebook_hash_key"]]
        expected_container_bytes = (
            release.get(definition["release_notebook_bytes_key"])
            if definition["release_notebook_bytes_key"]
            else None
        )
        expected_pipeline_hash = release[definition["release_pipeline_hash_key"]]
        current_container_hash = sha256(notebook)
        current_pipeline_hash = sha256(pipeline)
        rows.append(
            {
                "stage": definition["stage"],
                "container_path": definition["notebook"],
                "current_container_bytes": notebook.stat().st_size,
                "current_container_sha256": current_container_hash,
                "release_container_bytes": expected_container_bytes,
                "release_container_sha256": expected_container_hash,
                "container_status": (
                    "MATCHES_RELEASE"
                    if current_container_hash == expected_container_hash
                    else "DRIVE_CONTAINER_REVISION_DRIFT"
                ),
                "extracted_pipeline_path": definition["pipeline"],
                "extracted_pipeline_sha256": current_pipeline_hash,
                "release_pipeline_sha256": expected_pipeline_hash,
                "pipeline_status": (
                    "BYTE_VERIFIED"
                    if current_pipeline_hash == expected_pipeline_hash
                    else "MISMATCH"
                ),
                "execution_authority": "EXTRACTED_PIPELINE",
            }
        )
    payload = {
        "schema_version": 1,
        "interpretation": (
            "Notebook containers can drift when Colab outputs or metadata are saved. "
            "The extracted embedded pipeline is the execution authority when its "
            "release-manifest SHA-256 matches."
        ),
        "records": rows,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def verify_frozen_assets(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing frozen manifest: {path.relative_to(ROOT)}"]
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            target = ROOT / row["repository_path"]
            if not target.exists():
                # Portable-only assets are deliberately absent from an ordinary Git clone.
                continue
            if target.stat().st_size != int(row["size_bytes"]):
                errors.append(f"size mismatch: {row['repository_path']}")
            elif sha256(target) != row["sha256"]:
                errors.append(f"hash mismatch: {row['repository_path']}")
    return errors


def check_or_write(path: Path, expected: str, *, check: bool) -> list[str]:
    if check:
        if not path.is_file():
            return [f"missing generated manifest: {path.relative_to(ROOT)}"]
        actual = path.read_text(encoding="utf-8-sig")
        return [] if actual == expected else [f"stale generated manifest: {path.relative_to(ROOT)}"]
    path.write_text(expected, encoding="utf-8", newline="\n")
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    errors.extend(
        check_or_write(
            PROVENANCE / "imported_legacy_sources.csv",
            imported_source_manifest(),
            check=args.check,
        )
    )
    errors.extend(
        check_or_write(
            PROVENANCE / "container_revision_audit.json",
            revision_audit(),
            check=args.check,
        )
    )
    frozen_path = PROVENANCE / "frozen_assets_manifest.csv"
    if args.check:
        errors.extend(verify_frozen_assets(frozen_path))
    else:
        frozen_path.write_text(frozen_asset_manifest(), encoding="utf-8", newline="\n")
    u2_metrics_path = PROVENANCE / "u2_frozen_metrics.csv"
    u2_metrics = u2_frozen_metrics()
    if u2_metrics is None:
        if not u2_metrics_path.is_file():
            errors.append("missing portable-derived reference: provenance/u2_frozen_metrics.csv")
    else:
        errors.extend(check_or_write(u2_metrics_path, u2_metrics, check=args.check))
    if errors:
        print("CMDO provenance manifests FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("CMDO provenance manifests PASS" if args.check else "CMDO provenance manifests WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
