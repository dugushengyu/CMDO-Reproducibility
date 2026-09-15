#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta, binom

ROOT = Path(__file__).resolve().parents[1]

W0 = 0.05
DELTA = 0.05
TARGET_POWER = 0.80
THETA_GRID = np.arange(0.55, 0.951, 0.05)
MISMATCH_GRID = np.arange(-0.10, 0.1001, 0.025)
M_APPLICATION_GRID = np.array([16, 32, 64, 128, 256, 512], dtype=int)
CERT_PAIR_GRID = np.array([16, 32, 64, 128, 256, 512, 1024, 2048], dtype=int)
H_CLIP = 1e-12
ATOL = 5e-12


def auc_var_lower_bound(theta: float, m: int, n: int) -> float:
    if theta <= 0.0 or theta >= 1.0 or m < 2 or n < 2:
        return 0.0
    s = min(m, n)
    ell = max(m, n)
    r = min(theta, 1.0 - theta)
    q = max(theta, 1.0 - theta)
    if (s - 1.0) / (ell - 1.0) <= 2.0 * r:
        B = s - (s - 1.0) ** 2 / (12.0 * (ell - 1.0) * theta * (1.0 - theta))
    else:
        B = (
            1.0
            - (m + n - 2.0) * r / q
            + 4.0 / (3.0 * q) * math.sqrt(2.0 * r * (m - 1.0) * (n - 1.0))
        )
    return max(0.0, theta * (1.0 - theta) / (m * n) * B)


def auc_var_lower_bound_array(theta: np.ndarray, m: int, n: int) -> np.ndarray:
    t = np.asarray(theta, dtype=float)
    out = np.zeros_like(t)
    mask = (t > 0.0) & (t < 1.0)
    if not np.any(mask):
        return out

    u = t[mask]
    s = min(m, n)
    ell = max(m, n)
    r = np.minimum(u, 1.0 - u)
    q = np.maximum(u, 1.0 - u)
    branch1 = (s - 1.0) / (ell - 1.0) <= 2.0 * r

    B = np.empty_like(u)
    B[branch1] = s - (s - 1.0) ** 2 / (
        12.0 * (ell - 1.0) * u[branch1] * (1.0 - u[branch1])
    )
    z = ~branch1
    B[z] = (
        1.0
        - (m + n - 2.0) * r[z] / q[z]
        + 4.0 / (3.0 * q[z]) * np.sqrt(2.0 * r[z] * (m - 1.0) * (n - 1.0))
    )
    out[mask] = np.maximum(0.0, u * (1.0 - u) / (m * n) * B)
    return out


def build_ci_cache() -> dict[int, tuple[np.ndarray, np.ndarray]]:
    cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for K in CERT_PAIR_GRID:
        x = np.arange(K + 1, dtype=int)
        lo = np.zeros(K + 1, dtype=float)
        hi = np.ones(K + 1, dtype=float)
        mid_lo = x > 0
        mid_hi = x < K
        lo[mid_lo] = beta.ppf(DELTA / 2.0, x[mid_lo], K - x[mid_lo] + 1)
        hi[mid_hi] = beta.ppf(1.0 - DELTA / 2.0, x[mid_hi] + 1, K - x[mid_hi])
        cache[int(K)] = (lo, hi)
    return cache


CI_CACHE = build_ci_cache()


def certification_probability(theta: float, theta_h: float, m: int, K: int) -> float:
    lo, hi = CI_CACHE[int(K)]
    v_min = np.minimum(
        auc_var_lower_bound_array(lo, m, m),
        auc_var_lower_bound_array(hi, m, m),
    )
    b2_max = np.maximum((theta_h - lo) ** 2, (theta_h - hi) ** 2)
    den = b2_max + v_min
    cap = np.where(den > 0.0, np.minimum(1.0, 2.0 * v_min / den), 1.0)
    ok = cap + 1e-15 >= W0
    probs = binom.pmf(np.arange(K + 1), K, theta)
    return float(np.sum(probs[ok]))


def build_frontier() -> pd.DataFrame:
    rows = []
    tau_w = 2.0 / W0 - 1.0

    for theta in THETA_GRID:
        hs: list[float] = []
        for d in MISMATCH_GRID:
            h = float(np.clip(theta + d, H_CLIP, 1.0 - H_CLIP))
            if not any(abs(h - prior) < 1e-14 for prior in hs):
                hs.append(h)

        for h in hs:
            mismatch = h - theta
            for m in M_APPLICATION_GRID:
                m = int(m)
                vmin = auc_var_lower_bound(float(theta), m, m)
                critical = math.sqrt(max(0.0, tau_w * vmin))
                rho = abs(mismatch) / critical if critical > 0 else math.inf
                robust_cap = (
                    min(1.0, 2.0 * vmin / (mismatch * mismatch + vmin))
                    if (mismatch * mismatch + vmin) > 0
                    else 1.0
                )
                structural = robust_cap + 1e-15 < W0

                C_labels = math.inf
                if not structural:
                    for K in CERT_PAIR_GRID:
                        K = int(K)
                        power = certification_probability(float(theta), h, m, K)
                        if power + 1e-15 >= TARGET_POWER:
                            C_labels = int(2 * K)
                            break

                if math.isfinite(C_labels):
                    status = "finite_within_grid"
                elif structural:
                    status = "structurally_noncertifiable"
                else:
                    status = "safe_but_grid_censored"

                rows.append(
                    {
                        "AUC_true": float(theta),
                        "h_hist": h,
                        "mismatch": mismatch,
                        "m_application": m,
                        "C_labels": C_labels,
                        "max_labels_tested": int(2 * CERT_PAIR_GRID[-1]),
                        "Vmin": vmin,
                        "rho": rho,
                        "robust_oracle_cap": robust_cap,
                        "status": status,
                    }
                )

    return pd.DataFrame(rows)


def build_scaling(frontier: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for m in M_APPLICATION_GRID:
        m = int(m)
        q = frontier[frontier["m_application"] == m].copy()
        finite = np.isfinite(q["C_labels"].to_numpy(float))
        zero = q[np.abs(q["mismatch"].to_numpy(float)) < 1e-12]
        zero_cost = zero["C_labels"].to_numpy(float)
        zero_finite = zero_cost[np.isfinite(zero_cost)]
        rows.append(
            {
                "m_application": m,
                "states": int(len(q)),
                "finite_states": int(finite.sum()),
                "structural_noncertifiable": int((q["status"] == "structurally_noncertifiable").sum()),
                "safe_grid_censored": int((q["status"] == "safe_but_grid_censored").sum()),
                "finite_fraction": float(finite.mean()),
                "median_cost_finite": float(np.median(q.loc[finite, "C_labels"].to_numpy(float))),
                "zero_mismatch_median": float(np.median(zero_finite)),
                "zero_mismatch_q25": float(np.quantile(zero_finite, 0.25, method="linear")),
                "zero_mismatch_q75": float(np.quantile(zero_finite, 0.75, method="linear")),
                "zero_mismatch_median_over_m": float(np.median(zero_finite) / m),
            }
        )
    return pd.DataFrame(rows)


def compare_frame(actual: pd.DataFrame, expected: pd.DataFrame, name: str) -> None:
    if list(actual.columns) != list(expected.columns):
        raise AssertionError(f"{name}: column mismatch")
    if len(actual) != len(expected):
        raise AssertionError(f"{name}: row-count mismatch {len(actual)} != {len(expected)}")

    for col in actual.columns:
        a = actual[col]
        e = expected[col]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(e):
            av = a.to_numpy(float)
            ev = e.to_numpy(float)
            if not bool(np.all(np.isinf(av) == np.isinf(ev))):
                raise AssertionError(f"{name}: infinity pattern mismatch in {col}")
            mask = np.isfinite(av) & np.isfinite(ev)
            if mask.any() and not np.allclose(av[mask], ev[mask], rtol=2e-10, atol=ATOL):
                diff = float(np.max(np.abs(av[mask] - ev[mask])))
                raise AssertionError(f"{name}: numeric mismatch in {col}; max abs diff={diff:.3g}")
        else:
            if not np.array_equal(a.astype(str).to_numpy(), e.astype(str).to_numpy()):
                raise AssertionError(f"{name}: text mismatch in {col}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Regenerate and verify the PCC finite-grid certification tables.")
    ap.add_argument("--write-dir", type=Path, default=None, help="Optional external directory for regenerated CSVs.")
    args = ap.parse_args()

    frozen_frontier = ROOT / "source_data" / "pcc" / "PCC_frontier_classified.csv"
    frozen_scaling = ROOT / "source_data" / "pcc" / "PCC_scaling_summary_v12.csv"

    frontier = build_frontier()
    scaling = build_scaling(frontier)

    expected_frontier = pd.read_csv(frozen_frontier)
    expected_scaling = pd.read_csv(frozen_scaling)

    compare_frame(frontier, expected_frontier, "PCC_frontier_classified.csv")
    compare_frame(scaling, expected_scaling, "PCC_scaling_summary_v12.csv")

    zero = scaling[scaling["m_application"] >= 32]
    slope = float(np.polyfit(np.log(zero["m_application"]), np.log(zero["zero_mismatch_median"]), 1)[0])
    if abs(slope - 1.0) > 1e-12:
        raise AssertionError(f"PCC scaling slope mismatch: {slope}")

    if args.write_dir is not None:
        args.write_dir.mkdir(parents=True, exist_ok=True)
        frontier.to_csv(args.write_dir / "PCC_frontier_classified_REGENERATED.csv", index=False, float_format="%.15g")
        scaling.to_csv(args.write_dir / "PCC_scaling_summary_v12_REGENERATED.csv", index=False, float_format="%.15g")

    print("[PASS] PCC finite-grid certification table regenerated: 474/474 states match.")
    print("[PASS] PCC scaling summary matches; zero-mismatch log-log slope (m>=32) = 1.00.")


if __name__ == "__main__":
    main()
