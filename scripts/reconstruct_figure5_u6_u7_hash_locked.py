#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Figure 5 — hash-locked U6/U7 score/outcome reconstruction
================================================================

Purpose
-------
Reconstruct the exact per-example score/outcome arrays needed for a
post-completion comparator replay on U6 and U7, using the original frozen
pipelines and public data. A reconstruction is accepted only if the regenerated
score hashes exactly match the pre-outcome hashes stored in the canonical
records. U7 row-membership hashes are also checked exactly.

This script DOES NOT run any alternative comparator and DOES NOT alter the
prospective status of U6/U7. It only reconstructs replay ingredients.

Outputs (local, untracked until reviewed)
----------------------------------------
source_data/figure5_final_system/comparator_reconstruction/
  CMDO_Figure5_U6_Reconstructed_Scores_And_Outcomes_v0.1.csv.gz
  CMDO_Figure5_U7_Reconstructed_Stratum_Scores_And_Outcomes_v0.1.csv.gz
  CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.csv
  CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.json

The large reconstructed arrays are written only for stages whose exact frozen
hash checks pass.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import importlib.util
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


U6_ARCHIVE = "StageU6_Canonical_Records_v1.0.zip"
U7_ARCHIVE = "StageU7_Canonical_Records_v1.0.zip"

U6_PIPELINE_REL = Path(
    "legacy/original_authoritative/u6/"
    "StageU6_Independent_Pair_Complete_Observer_Reserve_v1.0.py"
)
U7_PIPELINE_REL = Path(
    "legacy/original_authoritative/u7/"
    "StageU7_General_Performance_Observability_And_Natural_Clinical_Deployment_v1.0.py"
)

U6_DESC = "StageU6_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
U6_TRUTH = "StageU6_Target_True_Metrics_v1.0.csv"
U7_DESC = "StageU7_PreOutcome_Clinical_Descriptors_v1.0.csv"
U7_TRUTH = "StageU7_Clinical_Strata_Truth_v1.0.csv"

PACKAGE_IMPORTS = {
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "scikit-learn": "sklearn",
    "Pillow": "PIL",
    "medmnist": "medmnist",
    "torchvision": "torchvision",
    "folktables": "folktables",
    "ucimlrepo": "ucimlrepo",
}


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve_canonical_dir(repo: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        require(p.is_dir(), f"Canonical record directory does not exist: {p}")
        return p

    env = os.environ.get("CMDO_CANONICAL_RECORD_DIR", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        require(p.is_dir(), f"CMDO_CANONICAL_RECORD_DIR does not exist: {p}")
        return p

    cfg = repo / "config" / "local_paths.json"
    if cfg.is_file():
        obj = json.loads(cfg.read_text(encoding="utf-8"))
        val = str(obj.get("canonicalRecordDir", "")).strip()
        if val:
            p = Path(val).expanduser().resolve()
            if p.is_dir():
                return p

    default = repo / "data" / "canonical_records"
    if default.is_dir():
        return default.resolve()

    for p in repo.rglob(U7_ARCHIVE):
        if p.is_file() and (p.parent / U6_ARCHIVE).is_file():
            return p.parent.resolve()

    raise RuntimeError(
        "Could not resolve canonical record directory. Set "
        "CMDO_CANONICAL_RECORD_DIR or pass --canonical-dir."
    )


def read_manifest(repo: Path) -> dict[str, str]:
    p = repo / "provenance" / "canonical_archives_manifest.csv"
    require(p.is_file(), f"Missing provenance manifest: {p}")
    df = pd.read_csv(p)
    return {str(r.archive): str(r.sha256).lower() for r in df.itertuples(index=False)}


def find_member(zf: zipfile.ZipFile, basename: str) -> str:
    hits = [n for n in zf.namelist() if Path(n).name == basename]
    require(len(hits) == 1, f"Expected exactly one {basename} in archive; found {len(hits)}")
    return hits[0]


def read_csv_member(zip_path: Path, basename: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as zf:
        member = find_member(zf, basename)
        with zf.open(member, "r") as raw:
            if basename.lower().endswith(".gz"):
                with gzip.GzipFile(fileobj=raw, mode="rb") as dec:
                    return pd.read_csv(dec)
            return pd.read_csv(raw)


def import_pipeline(path: Path, module_name: str):
    require(path.is_file(), f"Missing frozen pipeline: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"Could not load pipeline: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for package, module_name in PACKAGE_IMPORTS.items():
        try:
            mod = importlib.import_module(module_name)
            out[package] = str(getattr(mod, "__version__", "installed-version-unreported"))
        except Exception as exc:
            out[package] = f"MISSING_OR_IMPORT_FAILED: {type(exc).__name__}: {exc}"
    return out


def check_required_packages(stage: str) -> None:
    needed = ["numpy", "pandas", "scipy", "scikit-learn", "Pillow"]
    if stage in {"U6", "Both"}:
        needed += ["medmnist", "torchvision", "folktables"]
    if stage in {"U7", "Both"}:
        needed += ["ucimlrepo"]
    missing = []
    for package in needed:
        module_name = PACKAGE_IMPORTS[package]
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(package)
    if missing:
        raise RuntimeError(
            "Missing/import-failed Python packages: " + ", ".join(missing) +
            "\nInstall into the SAME Python used by this script, e.g.:\n  python -m pip install " +
            " ".join(missing)
        )


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return bool(np.isfinite(a) and np.isfinite(b) and abs(float(a) - float(b)) <= tol)


def git_head(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def reconstruct_u6(repo: Path, canonical: Path, cache: Path, outdir: Path) -> tuple[list[dict], Path | None]:
    print("\n[U6] Reconstructing 16 independent cross-domain target score arrays")
    u6_zip = canonical / U6_ARCHIVE
    desc = read_csv_member(u6_zip, U6_DESC)
    truth = read_csv_member(u6_zip, U6_TRUTH)
    require(len(desc) == 16, f"U6 descriptor roster expected 16 rows; found {len(desc)}")
    require(len(truth) == 16, f"U6 truth roster expected 16 rows; found {len(truth)}")

    mod = import_pipeline(repo / U6_PIPELINE_REL, "cmdo_u6_frozen_reconstruction")
    raw_dir = cache / "u6_public_data"
    raw_dir.mkdir(parents=True, exist_ok=True)
    bundles = mod.acquire_all_targets(raw_dir)
    require(len(bundles) == 16, f"U6 reconstructed roster expected 16 bundles; found {len(bundles)}")

    desc_idx = desc.set_index(["family", "target"], drop=False)
    truth_idx = truth.set_index(["family", "target"], drop=False)
    audit_rows: list[dict] = []
    raw_frames: list[pd.DataFrame] = []

    for bundle in bundles:
        key = (bundle.family, bundle.target)
        require(key in desc_idx.index, f"U6 reconstructed target absent from frozen descriptor: {key}")
        require(key in truth_idx.index, f"U6 reconstructed target absent from frozen truth: {key}")
        d = desc_idx.loc[key]
        t = truth_idx.loc[key]
        if isinstance(d, pd.DataFrame):
            d = d.iloc[0]
        if isinstance(t, pd.DataFrame):
            t = t.iloc[0]

        scores = np.asarray(bundle.scores, dtype=float)
        labels = np.asarray(bundle.label_loader(), dtype=int)
        score_hash = str(mod.sha256_array(scores))
        expected_hash = str(d["target_score_sha256"])
        score_hash_match = score_hash == expected_hash
        true_auc = float(roc_auc_score(labels, scores))
        counts_match = (
            int(len(labels)) == int(t["target_size"]) and
            int((labels == 1).sum()) == int(t["positive_count"]) and
            int((labels == 0).sum()) == int(t["negative_count"])
        )
        truth_match = close(true_auc, float(t["true_auc"]))
        transport_match = (
            close(float(bundle.transport_auc), float(d["transport_auc"])) and
            close(float(bundle.support_gate), float(d["support_gate"])) and
            close(float(bundle.transport_risk_proxy), float(d["transport_risk_proxy"]))
        )
        passed = score_hash_match and counts_match and truth_match and transport_match

        audit_rows.append({
            "stage": "U6",
            "family": bundle.family,
            "target_or_stratum": bundle.target,
            "n": len(scores),
            "expected_score_sha256": expected_hash,
            "reconstructed_score_sha256": score_hash,
            "score_hash_match": score_hash_match,
            "membership_hash_match": "NA",
            "label_count_match": counts_match,
            "truth_match": truth_match,
            "transport_descriptor_match": transport_match,
            "passed": passed,
        })
        print(
            f"  {bundle.target:<34s} score_hash={'MATCH' if score_hash_match else 'MISMATCH'} "
            f"truth={'MATCH' if truth_match else 'MISMATCH'} counts={'MATCH' if counts_match else 'MISMATCH'}"
        )

        raw_frames.append(pd.DataFrame({
            "family": bundle.family,
            "target": bundle.target,
            "example_index": np.arange(len(scores), dtype=int),
            "score": scores.astype(float),
            "label": labels.astype(int),
        }))

    all_pass = all(bool(r["passed"]) for r in audit_rows)
    final_path = outdir / "CMDO_Figure5_U6_Reconstructed_Scores_And_Outcomes_v0.1.csv.gz"
    if all_pass:
        pd.concat(raw_frames, ignore_index=True).to_csv(final_path, index=False, compression="gzip")
        print(f"[U6] EXACT HASH-LOCKED RECONSTRUCTION VERIFIED -> {final_path}")
        return audit_rows, final_path

    if final_path.exists():
        final_path.unlink()
    print("[U6] RECONSTRUCTION NOT ACCEPTED: at least one frozen hash/truth check failed")
    return audit_rows, None


def reconstruct_u7(repo: Path, canonical: Path, cache: Path, outdir: Path) -> tuple[list[dict], Path | None]:
    print("\n[U7] Reconstructing natural-clinical target scores and 16 frozen strata")
    u7_zip = canonical / U7_ARCHIVE
    desc = read_csv_member(u7_zip, U7_DESC)
    truth = read_csv_member(u7_zip, U7_TRUTH)
    require(len(desc) == 16, f"U7 descriptor roster expected 16 rows; found {len(desc)}")
    require(len(truth) == 16, f"U7 truth roster expected 16 rows; found {len(truth)}")

    mod = import_pipeline(repo / U7_PIPELINE_REL, "cmdo_u7_frozen_reconstruction")
    prepared = mod.prepare_clinical_deployment()
    target = prepared["target"].reset_index(drop=True)
    target_rows = np.asarray(prepared["target_rows"], dtype=int)
    target_scores = np.asarray(prepared["target_scores"], dtype=float)
    strata = mod.clinical_strata(target)
    require(len(strata) == 16, f"U7 reconstructed stratum roster expected 16; found {len(strata)}")

    desc_idx = desc.set_index("stratum", drop=False)
    truth_idx = truth.set_index("stratum", drop=False)
    audit_rows: list[dict] = []
    raw_frames: list[pd.DataFrame] = []

    for name, mask in strata.items():
        require(name in desc_idx.index, f"U7 reconstructed stratum absent from frozen descriptor: {name}")
        require(name in truth_idx.index, f"U7 reconstructed stratum absent from frozen truth: {name}")
        d = desc_idx.loc[name]
        t = truth_idx.loc[name]
        if isinstance(d, pd.DataFrame):
            d = d.iloc[0]
        if isinstance(t, pd.DataFrame):
            t = t.iloc[0]

        mask = np.asarray(mask, dtype=bool)
        row_ids = target_rows[mask]
        scores = target_scores[mask]
        labels = (
            prepared["y_frame"].iloc[row_ids, 0].astype(str).to_numpy() == "<30"
        ).astype(int)

        score_hash = str(mod.sha256_array(scores))
        expected_score_hash = str(d["score_sha256"])
        score_hash_match = score_hash == expected_score_hash

        membership_hash = str(mod.sha256_array(row_ids.astype(float)))
        expected_membership_hash = str(d["row_membership_sha256"])
        membership_match = membership_hash == expected_membership_hash

        counts_match = (
            int(len(labels)) == int(t["input_count"]) and
            int((labels == 1).sum()) == int(t["positive_count"]) and
            int((labels == 0).sum()) == int(t["negative_count"])
        )

        eligible = bool(t["eligible"])
        truth_match = True
        if eligible:
            metrics = mod.compute_true_metrics(scores, labels, float(prepared["threshold"]))
            for metric, value in metrics.items():
                col = f"true_{metric}"
                if col in truth.columns:
                    truth_match = truth_match and close(float(value), float(t[col]))

        # Recompute descriptor from frozen source-validation scores for an extra
        # deterministic check; score hashes remain the acceptance lock.
        descriptor = mod.score_shift_descriptor(
            prepared["source_validation_scores"], scores, prepared["source_metrics"]
        )
        transport_match = (
            close(float(descriptor["support_gate"]), float(d["support_gate"])) and
            close(float(descriptor["transport_risk_proxy"]), float(d["transport_risk_proxy"]))
        )
        for metric in mod.METRICS:
            col = f"transport_{metric}"
            if col in desc.columns:
                transport_match = transport_match and close(
                    float(descriptor["transport"][metric]), float(d[col])
                )

        passed = score_hash_match and membership_match and counts_match and truth_match and transport_match
        audit_rows.append({
            "stage": "U7",
            "family": "UCI_DIABETES_130_HOSPITALS",
            "target_or_stratum": name,
            "n": len(scores),
            "expected_score_sha256": expected_score_hash,
            "reconstructed_score_sha256": score_hash,
            "score_hash_match": score_hash_match,
            "membership_hash_match": membership_match,
            "label_count_match": counts_match,
            "truth_match": truth_match,
            "transport_descriptor_match": transport_match,
            "passed": passed,
        })
        print(
            f"  {name:<34s} score_hash={'MATCH' if score_hash_match else 'MISMATCH'} "
            f"membership={'MATCH' if membership_match else 'MISMATCH'} truth={'MATCH' if truth_match else 'MISMATCH'}"
        )

        raw_frames.append(pd.DataFrame({
            "stratum": name,
            "example_index": np.arange(len(scores), dtype=int),
            "row_id": row_ids.astype(int),
            "score": scores.astype(float),
            "label": labels.astype(int),
        }))

    all_pass = all(bool(r["passed"]) for r in audit_rows)
    final_path = outdir / "CMDO_Figure5_U7_Reconstructed_Stratum_Scores_And_Outcomes_v0.1.csv.gz"
    if all_pass:
        pd.concat(raw_frames, ignore_index=True).to_csv(final_path, index=False, compression="gzip")
        print(f"[U7] EXACT HASH-LOCKED RECONSTRUCTION VERIFIED -> {final_path}")
        return audit_rows, final_path

    if final_path.exists():
        final_path.unlink()
    print("[U7] RECONSTRUCTION NOT ACCEPTED: at least one frozen hash/truth check failed")
    return audit_rows, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--canonical-dir", default=None)
    ap.add_argument("--stage", choices=["U6", "U7", "Both"], default="Both")
    ap.add_argument("--cache-dir", default=None)
    args = ap.parse_args()

    repo_arg = Path(args.repo).expanduser()
    repo = repo_arg.resolve()
    require(repo.is_dir(), f"Repository does not exist: {repo}")
    canonical = resolve_canonical_dir(repo, args.canonical_dir)
    manifest = read_manifest(repo)

    check_required_packages(args.stage)

    for archive in [U6_ARCHIVE, U7_ARCHIVE]:
        if args.stage == "U6" and archive == U7_ARCHIVE:
            continue
        if args.stage == "U7" and archive == U6_ARCHIVE:
            continue
        p = canonical / archive
        require(p.is_file(), f"Missing canonical archive: {p}")
        require(archive in manifest, f"Archive missing from manifest: {archive}")
        actual = sha256_file(p).lower()
        require(actual == manifest[archive], f"Canonical archive SHA mismatch: {archive}")

    if args.cache_dir:
        cache = Path(args.cache_dir).expanduser().resolve()
    else:
        base = os.environ.get("LOCALAPPDATA", "").strip()
        if base:
            cache = Path(base) / "CMDO" / "figure5_hash_locked_reconstruction"
        else:
            cache = Path(tempfile.gettempdir()) / "CMDO" / "figure5_hash_locked_reconstruction"
    cache.mkdir(parents=True, exist_ok=True)

    outdir = repo / "source_data" / "figure5_final_system" / "comparator_reconstruction"
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 104)
    print(" CMDO FIGURE 5 HASH-LOCKED U6/U7 RECONSTRUCTION AUDIT")
    print(" exact frozen score hashes are the acceptance criterion")
    print("=" * 104)
    print(f"Repository argument : {repo_arg}")
    print(f"Repository resolved : {repo}")
    print(f"Canonical           : {canonical}")
    print(f"Stage               : {args.stage}")
    print(f"Public-data cache   : {cache}")
    print(f"Git HEAD            : {git_head(repo)}")
    print("\nGuardrail: no comparator is run in this script.")

    audit_rows: list[dict] = []
    generated: dict[str, str | None] = {"U6": None, "U7": None}

    try:
        if args.stage in {"U6", "Both"}:
            rows, path = reconstruct_u6(repo, canonical, cache, outdir)
            audit_rows.extend(rows)
            generated["U6"] = str(path.relative_to(repo)).replace("\\", "/") if path else None
        if args.stage in {"U7", "Both"}:
            rows, path = reconstruct_u7(repo, canonical, cache, outdir)
            audit_rows.extend(rows)
            generated["U7"] = str(path.relative_to(repo)).replace("\\", "/") if path else None
    finally:
        audit_csv = outdir / "CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.csv"
        pd.DataFrame(audit_rows).to_csv(audit_csv, index=False)

    stage_status: dict[str, str] = {}
    for stage in ["U6", "U7"]:
        rows = [r for r in audit_rows if r["stage"] == stage]
        if not rows:
            stage_status[stage] = "NOT_RUN"
        elif len(rows) == 16 and all(bool(r["passed"]) for r in rows):
            stage_status[stage] = "EXACT_HASH_LOCKED_RECONSTRUCTION_VERIFIED"
        else:
            stage_status[stage] = "RECONSTRUCTION_FAILED_OR_HASH_MISMATCH"

    requested = ["U6", "U7"] if args.stage == "Both" else [args.stage]
    overall_pass = all(stage_status[s] == "EXACT_HASH_LOCKED_RECONSTRUCTION_VERIFIED" for s in requested)

    result = {
        "schema": "CMDO_FIGURE5_HASH_LOCKED_RECONSTRUCTION_AUDIT_v0.1",
        "status": "PASS" if overall_pass else "FAIL",
        "requested_stage": args.stage,
        "repository_resolved": str(repo),
        "canonical_dir": str(canonical),
        "git_head": git_head(repo),
        "stage_status": stage_status,
        "generated_reconstruction_files": generated,
        "package_versions": package_versions(),
        "acceptance_rule": (
            "Every regenerated target/stratum score SHA256 must exactly match the frozen pre-outcome score hash; "
            "U7 row-membership hashes must also match; frozen truth/count/transport summaries are checked as secondary invariants."
        ),
        "claim_boundary": [
            "This is post-completion reconstruction only; it is not a new prospective experiment.",
            "No alternative comparator is run here.",
            "U6/U7 comparator replay remains prohibited unless this reconstruction audit passes exactly.",
            "Frozen prospective CMDO U6/U7 results remain unchanged.",
        ],
        "audit_csv": str((outdir / "CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.csv").relative_to(repo)).replace("\\", "/"),
    }
    audit_json = outdir / "CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.json"
    audit_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print("\n" + "=" * 104)
    print(" FIGURE 5 HASH-LOCKED RECONSTRUCTION AUDIT: " + ("PASS" if overall_pass else "FAIL"))
    print("=" * 104)
    for stage in requested:
        print(f"  {stage}: {stage_status[stage]}")
    print(f"Audit CSV : {outdir / 'CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.csv'}")
    print(f"Audit JSON: {audit_json}")
    print("\nInterpretation boundary:")
    print("  - No competitor has been run.")
    print("  - Exact score-hash equality is mandatory before U6/U7 post-completion benchmarking.")
    print("  - If a hash mismatches, the reconstructed scores are rejected, even if summary metrics are close.")

    if not overall_pass:
        sys.exit(2)


if __name__ == "__main__":
    main()
