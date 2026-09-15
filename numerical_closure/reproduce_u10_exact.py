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
        "weight_variance": float(np.sum(p * (w - mean_w) ** 2)),
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

    # Exact equal-state adaptation-frontier aggregation (Supplementary Note 7).
    # Under simple random sampling, D is exactly unbiased, so fixed-weight risk is
    # R_k(w)=(1-w)^2 V_k + w^2 B_k^2.
    lambdas = np.array(
        [((float(row["H"]) - float(row["theta"])) ** 2) / float(row["direct_risk"]) for row in rows]
    )
    global_w = 1.0 / (1.0 + float(np.mean(lambdas)))

    H_opp_terms = []
    A_alloc_terms = []
    C_comp_terms = []
    C_ind_terms = []

    for row in rows:
        V = float(row["direct_risk"])
        B = float(row["H"]) - float(row["theta"])
        wbar = float(row["mean_w"])
        w_star = V / (V + B * B)

        def fixed_risk(w0: float) -> float:
            return (1.0 - w0) ** 2 * V + w0 * w0 * B * B

        r_star = fixed_risk(w_star)
        r_global = fixed_risk(global_w)
        r_bar = fixed_risk(wbar)

        H_opp_terms.append((r_global - r_star) / V)
        A_alloc_terms.append((r_bar - r_star) / V)
        C_comp_terms.append((float(row["adaptive_risk"]) - r_bar) / V)

        weight_variance = float(row["weight_variance"])
        independent_adaptive_risk = (
            r_bar + weight_variance * (V + B * B)
        )
        C_ind_terms.append((independent_adaptive_risk - r_bar) / V)

    H_opp = float(np.mean(H_opp_terms))
    A_alloc = float(np.mean(A_alloc_terms))
    C_comp = float(np.mean(C_comp_terms))
    margin = H_opp - A_alloc - C_comp
    C_ind = float(np.mean(C_ind_terms))
    margin_ind = H_opp - A_alloc - C_ind

    expected = {
        "H": 0.089398,
        "A": 0.013645,
        "C": 0.219749,
        "margin": -0.143996,
        "C_ind": 0.031044,
        "margin_ind": 0.044709,
    }
    observed = {
        "H": H_opp,
        "A": A_alloc,
        "C": C_comp,
        "margin": margin,
        "C_ind": C_ind,
        "margin_ind": margin_ind,
    }
    for key, target in expected.items():
        if abs(observed[key] - target) > 5e-7:
            raise AssertionError(
                f"Exact U10 aggregate {key} mismatch: {observed[key]:.9f} vs {target:.6f}"
            )

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
    print(
        "[PASS] Exact frontier aggregate: "
        f"H={H_opp:.6f}, A={A_alloc:.6f}, C={C_comp:.6f}, "
        f"H-A-C={margin:+.6f}."
    )
    print(
        "[PASS] Independent-weight idealization: "
        f"C={C_ind:.6f}, H-A-C={margin_ind:+.6f}."
    )
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
