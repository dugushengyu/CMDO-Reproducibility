#!/usr/bin/env python3
"""Cross-platform static audit for the CMDO reviewer-facing submission route.

Uses only the Python standard library. It verifies tracked submission inputs,
manifest hashes, absence of author-machine dependencies in active renderers,
and the frozen Figure-5 numerical fingerprint.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ACTIVE_TEXT_FILES = [
    "RUN_SUBMISSION_FIGURES.m",
    "matlab/submission_figures/Figure1_IDA_RealData_Final.m",
    "matlab/submission_figures/Figure2_IDENTIFY_Validation.m",
    "matlab/submission_figures/Figure3_REUSE_Validation.m",
    "matlab/submission_figures/Figure4_PRESERVE_Refined.m",
    "matlab/submission_figures/Figure5_PhaseBoundary.m",
    "matlab/submission_figures/ED1_OutcomeFreeBoundary_v9.m",
    "matlab/submission_figures/ED2_IntegrityControls_v2.m",
    "matlab/submission_figures/cmdo_submission_load.m",
]

REQUIRED_TRACKED = [
    *ACTIVE_TEXT_FILES,
    "source_data/figure1_assets/Figure1_assets_selected_v1.mat",
    "source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv",
    "source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv",
    "source_data/figure4/CMDO_PRESERVE_StateRisk_v1.csv",
    "source_data/figure4/CMDO_AdaptationFrontier_v1.csv",
    "source_data/ed2/ED2_CouplingSummary_v1.csv",
    "source_data/ed2/ED2_LockedControlSummary_v1.csv",
    "source_data/submission_frozen/StageU4C_Audit_State_Results_v1.1.csv",
    "source_data/submission_frozen/StageU4C_Component_Fits_v1.1.csv",
    "source_data/submission_frozen/StageU4C_Component_Trajectory_Predictions_v1.1.csv",
    "source_data/submission_frozen/StageU4C_Evidence_Expiry_Map_v1.1.csv",
    "source_data/submission_frozen/StageU5B_Audit_State_Results_v1.0.csv",
    "source_data/submission_frozen/StageU6_Audit_State_Results_v1.0.csv",
    "source_data/submission_frozen/StageU6_Target_Summary_v1.0.csv",
    "source_data/submission_frozen/StageU7_State_Results_v1.0.csv",
    "source_data/submission_frozen/StageU7_Target_Metric_Summary_v1.0.csv",
    "source_data/submission_frozen/StageU7_Metric_Summary_v1.0.csv",
    "U10_Prospective_ECG/01_Prospective_Result/U10_PRIMARY_RESULT.json",
    "U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_PLUS_georgia_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_MINUS_georgia_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_PLUS_cpsc_2018_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_MINUS_cpsc_2018_v0.1.csv",
    "provenance/submission_github_native_v4_manifest.csv",
]

FORBIDDEN = [
    "C:\\Users\\zyx\\",
    "F:\\manuscript manual\\",
    "CMDO-U6-WSL-REPLAY",
    "uigetfile(",
    "getenv('USERPROFILE')",
    'getenv("USERPROFILE")',
]

EXPECTED_FIG1_SHA256 = "30490a2586a9394fad868159ccd1f0248b0d9afc17d9bc970456c425c63925e7"
EXPECTED_FIG5_CRITICAL = {
    8: [1.00, 1.00, 0.25, 0.75],
    16: [2.00, 4.00, 0.75, 2.00],
    32: [4.00, 4.00, 1.50, 2.00],
    64: [4.00, 4.00, 2.00, 2.00],
    128: [4.00, 4.00, 2.00, 2.00],
}
FIG5_METHODS = [
    "PC_PAIRED_HOEFFDING",
    "PC_USTAT_MCDIARMID",
    "PC_DELONG",
    "PC_PLUGIN",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_files(report: dict[str, Any]) -> None:
    missing = [p for p in REQUIRED_TRACKED if not (ROOT / p).is_file()]
    if missing:
        raise RuntimeError("Missing reviewer-facing tracked files:\n" + "\n".join(missing))
    report["required_file_count"] = len(REQUIRED_TRACKED)


def require_git_tracking(report: dict[str, Any]) -> None:
    if not (ROOT / ".git").is_dir():
        report["git_tracking"] = "SKIPPED_NO_GIT_METADATA"
        return
    if git("--version").returncode != 0:
        raise RuntimeError("Git metadata exists but git executable is unavailable")
    untracked = []
    for rel in REQUIRED_TRACKED:
        if git("ls-files", "--error-unmatch", "--", rel).returncode != 0:
            untracked.append(rel)
    if untracked:
        raise RuntimeError("Reviewer-facing files are present but not tracked:\n" + "\n".join(untracked))
    report["git_tracking"] = "PASS"


def require_no_author_paths(report: dict[str, Any]) -> None:
    hits: list[dict[str, str]] = []
    for rel in ACTIVE_TEXT_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN:
            if token in text:
                hits.append({"file": rel, "token": token})
    if hits:
        raise RuntimeError("Author-machine dependency found: " + json.dumps(hits, indent=2))
    report["author_path_scan"] = "PASS"


def require_manifest(report: dict[str, Any]) -> None:
    manifest_path = ROOT / "provenance/submission_github_native_v4_manifest.csv"
    checked = 0
    with manifest_path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            rel = row["path"].replace("\\", "/")
            path = ROOT / rel
            if not path.is_file():
                raise RuntimeError(f"Manifest file is missing: {rel}")
            expected_bytes = int(row["bytes"])
            expected_sha = row["sha256"].strip().lower()
            if path.stat().st_size != expected_bytes:
                raise RuntimeError(f"Manifest byte mismatch for {rel}")
            observed = sha256(path)
            if observed != expected_sha:
                raise RuntimeError(f"Manifest SHA-256 mismatch for {rel}: {observed} != {expected_sha}")
            checked += 1
    if checked < 12:
        raise RuntimeError(f"Submission manifest is unexpectedly short: {checked} entries")
    fig1 = ROOT / "source_data/figure1_assets/Figure1_assets_selected_v1.mat"
    if sha256(fig1) != EXPECTED_FIG1_SHA256:
        raise RuntimeError("Figure-1 frozen asset SHA-256 mismatch")
    report["manifest_entries_checked"] = checked


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def require_figure5(report: dict[str, Any]) -> None:
    path = ROOT / "source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 1000:
        raise RuntimeError(f"Figure-5 table unexpectedly short: {len(rows)}")
    lambdas = sorted({f(r, "lambda_nominal") for r in rows})
    observed: dict[int, list[float]] = {}
    for budget, expected in EXPECTED_FIG5_CRITICAL.items():
        values = []
        for method in FIG5_METHODS:
            crit = 0.0
            for lam in lambdas:
                cell = [
                    r for r in rows
                    if r["method"] == method
                    and int(float(r["budget"])) == budget
                    and abs(f(r, "lambda_nominal") - lam) < 1e-12
                ]
                if not cell:
                    raise RuntimeError(f"Incomplete Figure-5 cell: {method}, m={budget}, lambda={lam}")
                if max(f(r, "mean_excess_mae") for r in cell) <= 0:
                    crit = lam
                else:
                    break
            values.append(crit)
        if any(abs(a - b) > 1e-12 for a, b in zip(values, expected)):
            raise RuntimeError(f"Figure-5 critical-Lambda mismatch at m={budget}: {values} != {expected}")
        observed[budget] = values

    cmdo: dict[tuple[float, int, float, int], float] = {}
    ustat: dict[tuple[float, int, float, int], float] = {}
    for row in rows:
        lam = f(row, "lambda_nominal")
        if lam > 1 + 1e-12:
            continue
        key = (f(row, "true_auc"), int(float(row["budget"])), lam, int(float(row["bias_sign"])))
        if row["method"] == "PC_PAIRED_HOEFFDING":
            cmdo[key] = f(row, "gain_percent")
        elif row["method"] == "PC_USTAT_MCDIARMID":
            ustat[key] = f(row, "gain_percent")
    keys = sorted(set(cmdo) & set(ustat))
    advantage = [cmdo[k] - ustat[k] for k in keys]
    mean_adv = sum(advantage) / len(advantage)
    win_fraction = sum(x > 0 for x in advantage) / len(advantage)
    if abs(mean_adv - 1.0817) >= 5e-4:
        raise RuntimeError(f"Figure-5 paired advantage mismatch: {mean_adv:.8f}")
    if abs(win_fraction - 0.80) >= 1e-12:
        raise RuntimeError(f"Figure-5 paired-win mismatch: {win_fraction:.8f}")
    report["figure5"] = {
        "rows": len(rows),
        "critical_lambda_by_budget": {str(k): v for k, v in observed.items()},
        "lambda_le_1_cmdo_minus_ustat_pp": mean_adv,
        "lambda_le_1_fraction_cmdo_gt_ustat": win_fraction,
        "paired_states": len(keys),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report: dict[str, Any] = {
        "classification": "CMDO_SUBMISSION_PORTABILITY_STATIC_AUDIT",
        "repository": str(ROOT),
        "platform": sys.platform,
        "python": sys.version.split()[0],
    }
    require_files(report)
    require_git_tracking(report)
    require_no_author_paths(report)
    require_manifest(report)
    require_figure5(report)
    report["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("=== CMDO SUBMISSION PORTABILITY STATIC AUDIT: PASS ===")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
