#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import hypergeom

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = (128, 256, 512, 1024)


def weight_rule(D: np.ndarray, H: float, m: int) -> np.ndarray:
    V = np.maximum(D * (1.0 - D) / m, 1e-8)
    return np.minimum(0.35, V / (V + (D - H) ** 2))


def exact_state(N: int, K_correct: int, H: float, m: int) -> dict[str, float | bool | int]:
    theta = K_correct / N
    lo = max(0, m - (N - K_correct))
    hi = min(m, K_correct)

    x = np.arange(lo, hi + 1, dtype=int)
    p = hypergeom.pmf(x, N, K_correct, m)
    p = p / np.sum(p)

    D = x / m
    w = weight_rule(D, H, m)

    adaptive = (1.0 - w) * D + w * H
    mean_w = float(np.sum(p * w))
    matched_fixed = (1.0 - mean_w) * D + mean_w * H

    direct_risk = float(np.sum(p * (D - theta) ** 2))
    fixed_risk = float(np.sum(p * (matched_fixed - theta) ** 2))
    adaptive_risk = float(np.sum(p * (adaptive - theta) ** 2))

    return {
        "N": N,
        "K_correct": K_correct,
        "budget": m,
        "theta": theta,
        "H": H,
        "mean_w": mean_w,
        "direct_risk": direct_risk,
        "matched_fixed_risk": fixed_risk,
        "adaptive_risk": adaptive_risk,
        "adaptive_gt_matched_fixed": adaptive_risk > fixed_risk,
        "fixed_benefit_to_adaptive_harm": fixed_risk < direct_risk < adaptive_risk,
    }


def main() -> None:
    primary_path = (
        ROOT
        / "U10_Prospective_ECG"
        / "01_Prospective_Result"
        / "U10_PRIMARY_RESULT.json"
    )
    primary = json.loads(primary_path.read_text(encoding="utf-8"))

    target_summary = primary["target_summary"]
    H_values = {
        float(target_summary[dataset]["historical_H"])
        for dataset in ("georgia", "cpsc_2018")
    }
    if len(H_values) != 1:
        raise AssertionError(f"U10 historical H is not common across cohorts: {H_values}")
    H = H_values.pop()

    rows = []
    for dataset in ("georgia", "cpsc_2018"):
        rec = target_summary[dataset]
        N = int(rec["eligible_n"])
        theta = float(rec["target_accuracy_theta"])
        K_correct = int(round(theta * N))
        if abs(K_correct / N - theta) > 5e-13:
            raise AssertionError(
                f"{dataset}: frozen theta does not map to an integer correctness roster"
            )

        for m in BUDGETS:
            row = exact_state(N, K_correct, H, m)
            row["dataset"] = dataset
            rows.append(row)

    n_excess = sum(bool(row["adaptive_gt_matched_fixed"]) for row in rows)
    n_reversal = sum(bool(row["fixed_benefit_to_adaptive_harm"]) for row in rows)

    if n_excess != 8:
        raise AssertionError(
            f"Exact U10 check failed: adaptive risk exceeded matched-fixed risk in {n_excess}/8 states"
        )
    if n_reversal != 5:
        raise AssertionError(
            f"Exact U10 check failed: fixed benefit reversed to adaptive harm in {n_reversal}/8 states"
        )

    print("[PASS] U10 exact finite-cohort hypergeometric risk calculation.")
    print("[PASS] Adaptive risk > matched-fixed risk in 8/8 cohort-budget states.")
    print("[PASS] Fixed-use benefit -> adaptive harm in 5/8 states.")
    print("")
    print("dataset,budget,direct_risk,matched_fixed_risk,adaptive_risk,mean_w")
    for row in rows:
        print(
            f"{row['dataset']},{row['budget']},"
            f"{row['direct_risk']:.15g},{row['matched_fixed_risk']:.15g},"
            f"{row['adaptive_risk']:.15g},{row['mean_w']:.15g}"
        )


if __name__ == "__main__":
    main()
