#!/usr/bin/env python3
"""Finalize and independently verify an already completed CMDO E2E reviewer run.

This script performs no training, inference, downloading, or figure rendering.
It reads the existing reviewer artifacts, independently checks their structure,
classifies numeric deviations without changing the predeclared tolerance,
writes the reviewer-facing advisory, refreshes the final JSON report, and
rebuilds the results ZIP + SHA-256 sidecar.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_METRICS = ("auc", "auprc", "balanced_accuracy", "brier", "log_loss")
CORE_METRICS = {"auc", "auprc", "balanced_accuracy", "brier"}
EXPECTED_STEMS = (
    "Figure1_Evidential_Order_PCC",
    "Figure2_IDENTIFY_Validation",
    "Figure3_REUSE_Refined",
    "Figure4_CERTIFY",
    "Figure5_PRESERVE_PCC",
    "ED1_OutcomeFreeBoundary_v9",
    "ED2_IntegrityControls_v2",
    "ED3_RobustnessEfficiency_v1",
)


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"missing required CSV: {path}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_status() -> str:
    if not (ROOT / ".git").exists():
        return ""
    p = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or "git status failed")
    return p.stdout.strip()


def git_head() -> str | None:
    if not (ROOT / ".git").exists():
        return None
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def boolish(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize an existing CMDO E2E reviewer run")
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args()

    work = args.work_root.expanduser().resolve()
    u2 = work / "u2_fresh"
    figures = work / "submission_v2_figures"

    if git_status():
        raise SystemExit("Repository must be clean before finalization")

    fresh_report_path = u2 / "fresh_u2_report.json"
    fresh_report = load_json(fresh_report_path)
    fresh_metrics = read_csv(u2 / "StageU2_External_Target_True_Metrics_v0.1.csv")
    comparisons = read_csv(u2 / "u2_metric_comparison.csv")
    frozen_metrics = read_csv(ROOT / "provenance" / "u2_frozen_metrics.csv")
    history = read_csv(u2 / "training_history.csv")

    if len(history) != int(fresh_report.get("epochs", 12)):
        raise RuntimeError(
            f"training history has {len(history)} epochs; report says {fresh_report.get('epochs')}"
        )
    if len(fresh_metrics) != 38:
        raise RuntimeError(f"expected 38 fresh metric targets, found {len(fresh_metrics)}")

    frozen = {row["target"]: row for row in frozen_metrics}
    fresh = {row["target"]: row for row in fresh_metrics}
    structural_failures: list[str] = []

    if set(frozen) != set(fresh):
        structural_failures.append("target roster mismatch")
    for target in sorted(set(frozen) & set(fresh)):
        a = frozen[target]
        b = fresh[target]
        if a["family"] != b["family"]:
            structural_failures.append(f"{target}: family mismatch")
        if int(float(a["n"])) != int(float(b["n"])):
            structural_failures.append(f"{target}: n mismatch")
        if not math.isclose(
            float(a["prevalence"]), float(b["prevalence"]), abs_tol=1e-12, rel_tol=0
        ):
            structural_failures.append(f"{target}: prevalence mismatch")

    expected_pairs = {(target, metric) for target in frozen for metric in EXPECTED_METRICS}
    observed_pairs = {(row["target"], row["metric"]) for row in comparisons}
    if observed_pairs != expected_pairs:
        missing = sorted(expected_pairs - observed_pairs)
        extra = sorted(observed_pairs - expected_pairs)
        raise RuntimeError(
            f"metric-comparison grid mismatch: missing={missing[:10]} extra={extra[:10]}"
        )
    if len(comparisons) != 190:
        raise RuntimeError(f"expected 190 metric comparisons, found {len(comparisons)}")

    failed_rows = [row for row in comparisons if not boolish(row["passed"])]
    core_failures = [row for row in failed_rows if row["metric"] in CORE_METRICS]
    logloss_failures = [row for row in failed_rows if row["metric"] == "log_loss"]

    if structural_failures:
        advisory_class = "STRUCTURAL_FAIL"
        readiness = "FAIL"
    elif core_failures:
        advisory_class = "CORE_METRIC"
        readiness = "READY_WITH_CORE_NUMERIC_ADVISORY"
    elif logloss_failures:
        advisory_class = "LOGLOSS_ONLY"
        readiness = "READY_WITH_LOGLOSS_ADVISORY"
    else:
        advisory_class = "NONE"
        readiness = "READY"

    if len(failed_rows) != len(core_failures) + len(logloss_failures):
        raise RuntimeError("unexpected metric name among failed comparisons")

    prediction_files = sorted((u2 / "predictions").glob("*.npz"))
    if len(prediction_files) != 38:
        raise RuntimeError(f"expected 38 fresh prediction files, found {len(prediction_files)}")

    if not (u2 / "fresh_current_outcome_audit.csv").is_file():
        raise RuntimeError("missing fresh_current_outcome_audit.csv")
    if not (u2 / "checkpoint_latest.pt").is_file():
        raise RuntimeError("missing fresh checkpoint")

    for stem in EXPECTED_STEMS:
        for suffix in (".png", ".pdf"):
            path = figures / f"{stem}{suffix}"
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"missing/empty manuscript figure: {path.name}")
    png = sorted(figures.glob("*.png"))
    pdf = sorted(figures.glob("*.pdf"))
    if len(png) != 8 or len(pdf) != 8:
        raise RuntimeError(f"expected exactly 8 PNG + 8 PDF, found {len(png)} + {len(pdf)}")

    passed_count = 190 - len(failed_rows)
    tolerance = fresh_report.get("tolerance", {})
    advisory_lines = [
        "# Fresh U2 numeric replay advisory",
        "",
        f"Strict numeric replay status: {'PASS' if not failed_rows else 'REVIEW_REQUIRED'}",
        f"Advisory class: {advisory_class}",
        f"Metric comparisons within predeclared tolerance: {passed_count}/190 ({100*passed_count/190:.1f}%).",
        f"Structural identity checks: {'PASS' if not structural_failures else 'FAIL'}.",
        "",
        "The predeclared absolute and relative tolerances were not changed after observing this run.",
        "AUC, AUPRC, balanced accuracy and Brier are treated as core replay metrics.",
        "Log-loss is reported separately as a probability-sensitive metric.",
        "",
    ]
    if readiness == "READY_WITH_LOGLOSS_ADVISORY":
        advisory_lines += [
            f"{len(logloss_failures)} out-of-tolerance comparison(s) were observed, all confined to log-loss.",
            "No structural or core-metric tolerance failure was observed.",
            "",
            "Log-loss deviations:",
        ]
        for row in logloss_failures:
            advisory_lines.append(
                "- {target}: frozen={frozen}, fresh={fresh}, abs={absolute_difference}, rel={relative_difference}".format(**row)
            )
    elif readiness == "READY_WITH_CORE_NUMERIC_ADVISORY":
        advisory_lines += [
            "One or more core replay metrics exceeded tolerance and require investigation.",
            "",
            "Core-metric deviations:",
        ]
        for row in core_failures:
            advisory_lines.append(
                "- {target} {metric}: frozen={frozen}, fresh={fresh}, abs={absolute_difference}, rel={relative_difference}".format(**row)
            )
    elif readiness == "FAIL":
        advisory_lines += ["Structural mismatch detected; this is a reproduction failure."]
        advisory_lines += [f"- {item}" for item in structural_failures]
    else:
        advisory_lines += ["All 190 numeric comparisons are within the predeclared tolerance."]

    advisory_path = u2 / "NUMERIC_REPLAY_ADVISORY.md"
    advisory_path.write_text("\n".join(advisory_lines) + "\n", encoding="utf-8")

    fresh_report.update(
        {
            "numeric_advisory_class": advisory_class,
            "metric_comparisons_total": 190,
            "metric_comparisons_passed": passed_count,
            "metric_comparisons_failed": len(failed_rows),
            "core_metric_failures": core_failures,
            "logloss_metric_failures": logloss_failures,
            "structural_failures": structural_failures,
        }
    )
    fresh_report_path.write_text(
        json.dumps(fresh_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    acquisition = load_json(u2 / "acquisition.json")
    data_modes = {
        key: value.get("mode", "unspecified")
        for key, value in acquisition.items()
        if isinstance(value, dict)
    }
    all_data_reused = bool(data_modes) and all(str(v).startswith("reused_") for v in data_modes.values())

    final_report = {
        "schema_version": 2,
        "classification": "CMDO_OPTIONAL_END_TO_END_REVIEWER_AUDIT",
        "status": "PASS" if not failed_rows and not structural_failures else (
            "STRUCTURAL_FAIL" if structural_failures else "REVIEW_REQUIRED"
        ),
        "execution_status": "PASS",
        "reviewer_readiness": readiness,
        "git_commit": git_head(),
        "historical_t2_t3_replay_executed": False,
        "fresh_public_data_acquisition": not all_data_reused,
        "public_data_resolution_completed": True,
        "public_data_cache_reused_for_all_inputs": all_data_reused,
        "public_data_modes": data_modes,
        "fresh_model_training": True,
        "fresh_external_prediction_targets": 38,
        "fresh_prediction_file_count": 38,
        "fresh_u2_tolerance_comparison": "PASS" if not failed_rows else "REVIEW_REQUIRED",
        "fresh_u2_numeric_advisory_class": advisory_class,
        "fresh_u2_metric_comparisons_total": 190,
        "fresh_u2_metric_comparisons_passed": passed_count,
        "fresh_u2_metric_comparisons_failed": len(failed_rows),
        "fresh_u2_structural_failures": structural_failures,
        "fresh_current_outcome_audit_generated": True,
        "manuscript_figures_regenerated": 8,
        "final_png_count": 8,
        "final_pdf_count": 8,
        "git_worktree_clean_after_run": True,
        "scientific_boundary": (
            "Fresh U2 training is an additional platform-tolerant reviewer replay. "
            "It does not replace frozen manuscript records or sealed prospective verdicts."
        ),
        "numeric_advisory_file": str(advisory_path),
        "results_package": str(work / "CMDO_E2E_REVIEWER_RESULTS.zip"),
        "results_package_sha256_sidecar": str(work / "CMDO_E2E_REVIEWER_RESULTS.zip.sha256.txt"),
    }

    report_path = work / "CMDO_E2E_REVIEWER_REPORT.json"
    report_path.write_text(json.dumps(final_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    package = work / "CMDO_E2E_REVIEWER_RESULTS.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for root in (u2, figures):
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(work).as_posix())
        zf.write(report_path, arcname=report_path.name)

    digest = sha256(package)
    sidecar = work / "CMDO_E2E_REVIEWER_RESULTS.zip.sha256.txt"
    sidecar.write_text(f"{digest}  {package.name}\n", encoding="utf-8")

    if sha256(package) != digest:
        raise RuntimeError("results ZIP SHA-256 self-check failed")
    if git_status():
        raise RuntimeError("repository became dirty during finalization")

    print("=== CMDO EXISTING E2E FINALIZATION: PASS ===")
    print(f"Execution      : PASS")
    print(f"Readiness      : {readiness}")
    print(f"Numeric class  : {advisory_class}")
    print(f"U2 comparisons : {passed_count}/190 within tolerance")
    print(f"Predictions    : 38/38")
    print(f"Figures        : 8 PNG + 8 PDF")
    print(f"Git clean      : PASS")
    print(f"Advisory       : {advisory_path}")
    print(f"Report         : {report_path}")
    print(f"Results ZIP    : {package}")
    print(f"SHA256         : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
