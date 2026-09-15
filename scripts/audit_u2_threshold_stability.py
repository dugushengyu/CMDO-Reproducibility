#!/usr/bin/env python3
"""Read-only threshold-stability audit across completed CMDO fresh U2 runs.

No training, inference, downloading, or figure rendering is performed.

The audit asks whether fresh-run balanced-accuracy deviations are primarily
associated with variation in the validation-selected operating threshold while
threshold-free discrimination metrics remain stable.

It compares:
1. each run's native validation-selected threshold;
2. the frozen pre-existing U2 threshold;
3. every run threshold cross-applied to every run's saved predictions;
4. AUC/AUPRC/Brier stability under the repository's predeclared replay rule.

Nothing in this script changes the original tolerance or frozen manuscript data.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = "StageU2_External_Target_True_Metrics_v0.1.csv"
PRED_DIR = "predictions"
CORE_THRESHOLD_FREE = ("auc", "auprc", "brier")
ALL_CORE = ("auc", "auprc", "balanced_accuracy", "brier")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"missing required CSV: {path}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def within(a: float, b: float, abs_tol: float, rel_tol: float) -> bool:
    absolute = abs(a - b)
    relative = absolute / max(abs(a), abs(b), 1e-15)
    return absolute <= abs_tol or relative <= rel_tol


def balanced_accuracy(labels: np.ndarray, scores: np.ndarray, threshold: float) -> float:
    y = np.asarray(labels).astype(int)
    pred = (np.asarray(scores) >= threshold).astype(int)
    pos = y == 1
    neg = y == 0
    if not pos.any() or not neg.any():
        raise RuntimeError("balanced accuracy requires both classes")
    tpr = float((pred[pos] == 1).mean())
    tnr = float((pred[neg] == 0).mean())
    return 0.5 * (tpr + tnr)


def parse_run(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise argparse.ArgumentTypeError("--run must be LABEL=PATH")
    label, raw = spec.split("=", 1)
    label = label.strip()
    if not label:
        raise argparse.ArgumentTypeError("run label cannot be empty")
    return label, Path(raw.strip()).expanduser().resolve()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run",
        action="append",
        required=True,
        help="completed run as LABEL=PATH; provide at least two, ideally three",
    )
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    runs = [parse_run(x) for x in args.run]
    if len(runs) < 2:
        raise SystemExit("at least two completed runs are required")
    labels = [x[0] for x in runs]
    if len(labels) != len(set(labels)):
        raise SystemExit("run labels must be unique")

    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rule = read_json(ROOT / "provenance" / "replay_acceptance_rules.json")["u2_fresh_training"]
    abs_tol = float(rule["absolute_tolerance"])
    rel_tol = float(rule["relative_tolerance"])

    frozen_rows = read_csv(ROOT / "provenance" / "u2_frozen_metrics.csv")
    frozen = {r["target"]: r for r in frozen_rows}
    if len(frozen) != 38:
        raise RuntimeError(f"expected 38 frozen targets, found {len(frozen)}")
    frozen_thresholds = sorted({float(r["threshold"]) for r in frozen_rows})
    if len(frozen_thresholds) != 1:
        raise RuntimeError(f"expected one frozen threshold, found {frozen_thresholds}")
    frozen_threshold = frozen_thresholds[0]

    loaded: dict[str, dict[str, object]] = {}
    for label, run_root in runs:
        u2 = run_root / "u2_fresh"
        val = read_json(u2 / "validation_metrics.json")
        metrics_rows = read_csv(u2 / METRICS_CSV)
        metrics = {r["target"]: r for r in metrics_rows}
        if set(metrics) != set(frozen):
            raise RuntimeError(f"{label}: target roster differs from frozen 38-target roster")

        predictions: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for target in frozen:
            p = u2 / PRED_DIR / f"{target}.npz"
            if not p.is_file():
                raise RuntimeError(f"{label}: missing prediction file {p}")
            with np.load(p) as z:
                scores = np.asarray(z["scores"], dtype=float)
                y = np.asarray(z["labels"], dtype=int)
            if len(scores) != int(float(frozen[target]["n"])) or len(y) != len(scores):
                raise RuntimeError(f"{label}/{target}: prediction length mismatch")
            predictions[target] = (scores, y)

        loaded[label] = {
            "root": run_root,
            "threshold": float(val["threshold"]),
            "metrics": metrics,
            "predictions": predictions,
        }

    native_thresholds = {label: float(loaded[label]["threshold"]) for label in labels}
    candidate_thresholds: list[tuple[str, float]] = [("FROZEN", frozen_threshold)]
    candidate_thresholds += [(f"NATIVE_{label}", native_thresholds[label]) for label in labels]
    median_threshold = float(np.median(list(native_thresholds.values())))
    candidate_thresholds.append(("MEDIAN_NATIVE", median_threshold))

    dedup: list[tuple[str, float]] = []
    seen: list[float] = []
    for name, value in candidate_thresholds:
        if not any(math.isclose(value, old, abs_tol=1e-15, rel_tol=0) for old in seen):
            dedup.append((name, value))
            seen.append(value)
    candidate_thresholds = dedup

    cross_rows: list[dict[str, object]] = []
    summary_counts: dict[str, dict[str, int]] = {label: {} for label in labels}
    fog_rows: list[dict[str, object]] = []

    for label in labels:
        preds = loaded[label]["predictions"]
        for th_name, th in candidate_thresholds:
            pass_count = 0
            for target in sorted(frozen):
                scores, y = preds[target]
                ba = balanced_accuracy(y, scores, th)
                ref = float(frozen[target]["balanced_accuracy"])
                absolute = abs(ref - ba)
                relative = absolute / max(abs(ref), abs(ba), 1e-15)
                passed = within(ref, ba, abs_tol, rel_tol)
                pass_count += int(passed)
                row = {
                    "run": label,
                    "threshold_source": th_name,
                    "threshold": th,
                    "target": target,
                    "frozen_balanced_accuracy": ref,
                    "recomputed_balanced_accuracy": ba,
                    "absolute_difference": absolute,
                    "relative_difference": relative,
                    "passed": int(passed),
                }
                cross_rows.append(row)
                if target == "FOG_S5":
                    fog_rows.append(row.copy())
            summary_counts[label][th_name] = pass_count

    write_csv(
        out / "threshold_cross_application.csv",
        cross_rows,
        [
            "run", "threshold_source", "threshold", "target",
            "frozen_balanced_accuracy", "recomputed_balanced_accuracy",
            "absolute_difference", "relative_difference", "passed",
        ],
    )
    write_csv(
        out / "FOG_S5_threshold_audit.csv",
        fog_rows,
        [
            "run", "threshold_source", "threshold", "target",
            "frozen_balanced_accuracy", "recomputed_balanced_accuracy",
            "absolute_difference", "relative_difference", "passed",
        ],
    )

    metric_stability_rows: list[dict[str, object]] = []
    per_run_core_failures: dict[str, list[dict[str, object]]] = {}
    for label in labels:
        failures: list[dict[str, object]] = []
        metrics = loaded[label]["metrics"]
        for target in sorted(frozen):
            for metric in ALL_CORE:
                ref = float(frozen[target][metric])
                fresh = float(metrics[target][metric])
                absolute = abs(ref - fresh)
                relative = absolute / max(abs(ref), abs(fresh), 1e-15)
                passed = within(ref, fresh, abs_tol, rel_tol)
                row = {
                    "run": label,
                    "target": target,
                    "metric": metric,
                    "frozen": ref,
                    "fresh": fresh,
                    "absolute_difference": absolute,
                    "relative_difference": relative,
                    "passed": int(passed),
                }
                metric_stability_rows.append(row)
                if not passed:
                    failures.append(row)
        per_run_core_failures[label] = failures

    write_csv(
        out / "core_metric_stability.csv",
        metric_stability_rows,
        [
            "run", "target", "metric", "frozen", "fresh",
            "absolute_difference", "relative_difference", "passed",
        ],
    )

    target_ranges: list[dict[str, object]] = []
    for target in sorted(frozen):
        for metric in ("auc", "auprc", "balanced_accuracy", "brier", "log_loss"):
            values = [float(loaded[label]["metrics"][target][metric]) for label in labels]
            target_ranges.append(
                {
                    "target": target,
                    "metric": metric,
                    "fresh_min": min(values),
                    "fresh_max": max(values),
                    "fresh_range": max(values) - min(values),
                    "fresh_mean": float(np.mean(values)),
                    "fresh_sd": float(np.std(values, ddof=0)),
                }
            )
    write_csv(
        out / "fresh_run_metric_ranges.csv",
        target_ranges,
        ["target", "metric", "fresh_min", "fresh_max", "fresh_range", "fresh_mean", "fresh_sd"],
    )

    threshold_free_failures = {
        label: [
            row for row in per_run_core_failures[label]
            if row["metric"] in CORE_THRESHOLD_FREE
        ]
        for label in labels
    }
    native_ba_failures = {
        label: [
            row for row in per_run_core_failures[label]
            if row["metric"] == "balanced_accuracy"
        ]
        for label in labels
    }

    frozen_ba_all_pass = all(summary_counts[label]["FROZEN"] == 38 for label in labels)
    threshold_free_all_pass = all(not threshold_free_failures[label] for label in labels)
    native_core_only_ba = all(
        all(row["metric"] == "balanced_accuracy" for row in per_run_core_failures[label])
        for label in labels
    )

    if threshold_free_all_pass and native_core_only_ba and frozen_ba_all_pass:
        conclusion = "THRESHOLD_SENSITIVITY_SUPPORTED"
    elif threshold_free_all_pass and native_core_only_ba:
        conclusion = "THRESHOLD_SENSITIVITY_PLAUSIBLE_BUT_FIXED_THRESHOLD_NOT_FULLY_STABILIZING"
    elif threshold_free_all_pass:
        conclusion = "DISCRIMINATION_STABLE_BUT_CORE_VARIATION_IS_MIXED"
    else:
        conclusion = "MODEL_OR_CALIBRATION_VARIABILITY_EXTENDS_BEYOND_THRESHOLD_SELECTION"

    fog_metric_ranges = {
        row["metric"]: row
        for row in target_ranges
        if row["target"] == "FOG_S5"
    }

    result = {
        "classification": "CMDO_U2_THRESHOLD_STABILITY_AUDIT",
        "runs": [
            {
                "label": label,
                "root": str(loaded[label]["root"]),
                "native_threshold": native_thresholds[label],
                "native_core_failures": per_run_core_failures[label],
            }
            for label in labels
        ],
        "predeclared_tolerance": {
            "absolute": abs_tol,
            "relative": rel_tol,
        },
        "frozen_threshold": frozen_threshold,
        "native_threshold_min": min(native_thresholds.values()),
        "native_threshold_max": max(native_thresholds.values()),
        "native_threshold_range": max(native_thresholds.values()) - min(native_thresholds.values()),
        "native_threshold_mean": float(np.mean(list(native_thresholds.values()))),
        "native_threshold_sd": float(np.std(list(native_thresholds.values()), ddof=0)),
        "median_native_threshold": median_threshold,
        "balanced_accuracy_pass_counts_by_threshold": summary_counts,
        "threshold_free_core_failures_by_run": threshold_free_failures,
        "native_balanced_accuracy_failures_by_run": native_ba_failures,
        "FOG_S5_fresh_metric_ranges": fog_metric_ranges,
        "diagnostic_conclusion": conclusion,
        "interpretation_guardrail": (
            "This is a post-run diagnostic. It does not alter the frozen U2 threshold, "
            "the replay tolerances, or manuscript-authoritative records."
        ),
    }
    (out / "threshold_stability_audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    md: list[str] = [
        "# CMDO U2 threshold-stability audit",
        "",
        f"Diagnostic conclusion: **{conclusion}**",
        "",
        "This audit is read-only and post-run. It does not change the frozen threshold or replay tolerances.",
        "",
        "## Thresholds",
        "",
        f"- Frozen pre-existing threshold: {frozen_threshold:.12f}",
    ]
    for label in labels:
        md.append(f"- {label} native threshold: {native_thresholds[label]:.12f}")
    md += [
        f"- Native-threshold range: {result['native_threshold_range']:.12f}",
        "",
        "## Balanced-accuracy pass counts versus frozen reference",
        "",
        "| Run | " + " | ".join(name for name, _ in candidate_thresholds) + " |",
        "|---|" + "|".join("---:" for _ in candidate_thresholds) + "|",
    ]
    for label in labels:
        md.append(
            "| " + label + " | "
            + " | ".join(f"{summary_counts[label][name]}/38" for name, _ in candidate_thresholds)
            + " |"
        )

    md += [
        "",
        "## Native core-metric failures",
        "",
    ]
    for label in labels:
        failures = per_run_core_failures[label]
        if not failures:
            md.append(f"- {label}: none")
        else:
            rendered = "; ".join(
                f"{x['target']} {x['metric']} (frozen={x['frozen']:.6g}, fresh={x['fresh']:.6g})"
                for x in failures
            )
            md.append(f"- {label}: {rendered}")

    md += [
        "",
        "## FOG_S5",
        "",
        f"- Fresh AUC range: {fog_metric_ranges['auc']['fresh_min']:.6f} to {fog_metric_ranges['auc']['fresh_max']:.6f}",
        f"- Fresh AUPRC range: {fog_metric_ranges['auprc']['fresh_min']:.6f} to {fog_metric_ranges['auprc']['fresh_max']:.6f}",
        f"- Native balanced-accuracy range: {fog_metric_ranges['balanced_accuracy']['fresh_min']:.6f} to {fog_metric_ranges['balanced_accuracy']['fresh_max']:.6f}",
        f"- Fresh Brier range: {fog_metric_ranges['brier']['fresh_min']:.6f} to {fog_metric_ranges['brier']['fresh_max']:.6f}",
        "",
        "See FOG_S5_threshold_audit.csv for the same saved scores evaluated under every candidate threshold.",
    ]
    (out / "THRESHOLD_STABILITY_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("=== CMDO U2 THRESHOLD-STABILITY AUDIT COMPLETE ===")
    print(f"Runs             : {len(labels)}")
    print(f"Frozen threshold : {frozen_threshold:.12f}")
    for label in labels:
        print(
            f"{label:16s}: native threshold={native_thresholds[label]:.12f} "
            f"| frozen-threshold BA pass={summary_counts[label]['FROZEN']}/38"
        )
    print(f"Threshold range  : {result['native_threshold_range']:.12f}")
    print(f"Conclusion       : {conclusion}")
    print(f"Output           : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
