#!/usr/bin/env python3
"""
Compute deterministic 95% uncertainty intervals for the U10 strategy comparison used in Figure 5.

The point estimates are frozen post-completion U10 values. The intervals quantify Monte-Carlo
audit-sampling variability over the 200 frozen replicate draws. They are descriptive post-hoc
intervals and do NOT replace the locked prospective verdict MECHANISM_NOT_CONFIRMED.

Strategies:
  - shared_adaptive
  - fixed_weight_reuse (constant mean shared weight)
  - permuted_weight_control (empirical-marginal independence control)
  - crossfit_adaptive

For shared/fixed/crossfit, percentile intervals use paired bootstrap resampling of the 200
replicate indices. For the permuted control, each bootstrap resamples D and W marginals
independently and evaluates the exact empirical-marginal expected risk, avoiding extra Monte
Carlo noise from a finite number of permutations.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

BOOTSTRAPS = 10000
CI = (2.5, 97.5)
DATASETS = ("georgia", "cpsc_2018")
BUDGETS = (128, 256, 512, 1024)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cmdo_u10_dep", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gain(base, risk):
    return 100.0 * (base - risk) / base


def q95(x):
    return np.percentile(np.asarray(x, float), CI)


def exact_independent_weight_risk(D, W, H, theta):
    """Expected risk when empirical D and W marginals are independent."""
    e = np.asarray(D, float) - theta
    W = np.asarray(W, float)
    B = H - theta
    Ee = np.mean(e)
    Ee2 = np.mean(e * e)
    Ew = np.mean(W)
    Ew2 = np.mean(W * W)
    return float(
        Ee2 * (1.0 - 2.0 * Ew + Ew2)
        + 2.0 * B * Ee * (Ew - Ew2)
        + (B * B) * Ew2
    )


def bootstrap_cell(D, wF, shared, cf, H, theta, seed, n_boot):
    n = len(D)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n), dtype=np.int32)

    Db = D[idx]
    base = np.mean((Db - theta) ** 2, axis=1)
    if np.any(base <= 0):
        raise RuntimeError("Bootstrap direct MSE contains non-positive values.")

    # Shared adaptive: paired with the same audit replicate.
    shared_b = shared[idx]
    risk_shared = np.mean((shared_b - theta) ** 2, axis=1)

    # Constant-mean shared weight: re-estimate the mean weight within each bootstrap.
    Wpaired = wF[idx]
    wbar = np.mean(Wpaired, axis=1)
    fixed_est = (1.0 - wbar[:, None]) * Db + wbar[:, None] * H
    risk_fixed = np.mean((fixed_est - theta) ** 2, axis=1)

    # Cross-fit adaptive: paired replicate bootstrap.
    cf_b = cf[idx]
    risk_cross = np.mean((cf_b - theta) ** 2, axis=1)

    # Permuted-weight control: independently bootstrap the two empirical marginals,
    # then compute exact expected risk under independence for each bootstrap sample.
    idxW = rng.integers(0, n, size=(n_boot, n), dtype=np.int32)
    Wb = wF[idxW]
    e = Db - theta
    B = H - theta
    Ee = np.mean(e, axis=1)
    Ee2 = np.mean(e * e, axis=1)
    Ew = np.mean(Wb, axis=1)
    Ew2 = np.mean(Wb * Wb, axis=1)
    risk_perm = (
        Ee2 * (1.0 - 2.0 * Ew + Ew2)
        + 2.0 * B * Ee * (Ew - Ew2)
        + (B * B) * Ew2
    )

    return {
        "shared_adaptive": gain(base, risk_shared),
        "fixed_weight_reuse": gain(base, risk_fixed),
        "permuted_weight_control": gain(base, risk_perm),
        "crossfit_adaptive": gain(base, risk_cross),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Local U10 root, e.g. C:/Users/zyx/CMDO-U10-ECG")
    ap.add_argument("--repo", required=True, help="Local CMDO-Reproducibility clone")
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--bootstraps", type=int, default=BOOTSTRAPS)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    repo = Path(args.repo).expanduser().resolve()
    out_csv = Path(args.out).expanduser().resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    dep_py = repo / "U10_Prospective_ECG" / "03_Code" / "CMDO_U10_DEPENDENCE_DECOMPOSITION_v0.1" / "CMDO_U10_DEPENDENCE_DECOMPOSITION_v01.py"
    dep_csv = repo / "U10_Prospective_ECG" / "02_Posthoc_Diagnostics" / "U10_DEPENDENCE_DECOMPOSITION.csv"
    final_json = repo / "source_data" / "figure5_final_system" / "CMDO_Figure5_Final_System_v1.0.json"

    for p in (dep_py, dep_csv, final_json):
        if not p.exists():
            raise FileNotFoundError(p)

    mod = load_module(dep_py)

    # Re-verify the same sealed local U10 inputs used by the dependence-decomposition code.
    sealp = root / "SEALS" / "U10_PREOUTCOME_SEAL.json"
    specp = root / "UNSEAL" / "U10_LOCKED_EVALUATION_SPEC_v0.1.json"
    csvp = root / "UNSEAL" / "RESULTS_v0.1" / "U10_TARGET_BUDGET_SUMMARY.csv"
    jsonp = root / "UNSEAL" / "RESULTS_v0.1" / "U10_PRIMARY_RESULT.json"
    checks = [
        ("seal", sealp, mod.EXPECTED_SEAL),
        ("spec", specp, mod.EXPECTED_SPEC),
        ("prospective_csv", csvp, mod.EXPECTED_CSV),
        ("prospective_json", jsonp, mod.EXPECTED_JSON),
    ]
    for name, p, expected in checks:
        actual = mod.sha256_file(p)
        if actual != expected:
            raise RuntimeError(f"{name} hash mismatch: {actual}")
        print(f"[verify] {name}: PASS {actual}")

    seal = json.loads(sealp.read_text(encoding="utf-8"))
    H = float(seal["source_development"]["historical_accuracy_H"])
    prospective = pd.read_csv(csvp)
    frozen = pd.read_csv(dep_csv)

    rows = []
    point_tol = 1e-9

    for ds in DATASETS:
        z = mod.load_z(root, ds, seal)
        theta = float(z.mean())

        for m in BUDGETS:
            D, DA, DB, wF, wA, wB, shared, cf = mod.original_replicates(z, H, ds, m)
            base = mod.mse(D, theta)

            wfbar = float(wF.mean())
            fixed = (1.0 - wfbar) * D + wfbar * H

            # Reproduce the frozen permutation point estimate exactly using the original 500 permutations.
            perm_mse, _ = mod.permuted_shared(D, wF, H, theta, ds, m)

            recomputed = {
                "shared_adaptive": gain(base, mod.mse(shared, theta)),
                "fixed_weight_reuse": gain(base, mod.mse(fixed, theta)),
                "permuted_weight_control": gain(base, perm_mse),
                "crossfit_adaptive": gain(base, mod.mse(cf, theta)),
            }

            fr = frozen[(frozen.dataset == ds) & (frozen.budget == m)]
            if len(fr) != 1:
                raise RuntimeError(f"Frozen row not unique: {ds} m={m}")
            fr = fr.iloc[0]
            frozen_points = {
                "shared_adaptive": float(fr.shared_adaptive_gain_pct),
                "fixed_weight_reuse": float(fr.shared_constant_mean_gain_pct),
                "permuted_weight_control": float(fr.shared_permuted_weight_gain_pct),
                "crossfit_adaptive": float(fr.crossfit_adaptive_gain_pct),
            }

            for strategy in recomputed:
                delta = abs(recomputed[strategy] - frozen_points[strategy])
                if delta > point_tol:
                    raise RuntimeError(
                        f"Point estimate mismatch {ds} m={m} {strategy}: "
                        f"recomputed={recomputed[strategy]:.12g}, frozen={frozen_points[strategy]:.12g}, delta={delta:.3g}"
                    )

            seed = mod.seed_for("figure5_strategy_interval_v01", ds, m, args.bootstraps)
            boot = bootstrap_cell(D, wF, shared, cf, H, theta, seed, args.bootstraps)

            # Conditional exact empirical-marginal permuted point, reported only as a diagnostic.
            perm_exact = gain(base, exact_independent_weight_risk(D, wF, H, theta))

            for strategy, samples in boot.items():
                lo, hi = q95(samples)
                rows.append({
                    "dataset": ds,
                    "budget": m,
                    "strategy": strategy,
                    "point_gain_pct": frozen_points[strategy],
                    "bootstrap_mean_gain_pct": float(np.mean(samples)),
                    "bootstrap_se_pct": float(np.std(samples, ddof=1)),
                    "ci95_low_pct": float(lo),
                    "ci95_high_pct": float(hi),
                    "ci_excludes_zero": bool((lo > 0.0) or (hi < 0.0)),
                    "n_frozen_replicates": int(len(D)),
                    "n_bootstrap": int(args.bootstraps),
                    "interval_type": "paired_bootstrap" if strategy != "permuted_weight_control" else "independent_marginal_bootstrap",
                    "permuted_exact_empirical_gain_pct": perm_exact if strategy == "permuted_weight_control" else np.nan,
                })

            print(
                f"[cell] {ds:9s} m={m:4d} | "
                f"shared={frozen_points['shared_adaptive']:+7.2f}% | "
                f"fixed={frozen_points['fixed_weight_reuse']:+7.2f}% | "
                f"perm={frozen_points['permuted_weight_control']:+7.2f}% | "
                f"crossfit={frozen_points['crossfit_adaptive']:+7.2f}%"
            )

    df = pd.DataFrame(rows)
    if len(df) != 32:
        raise RuntimeError(f"Expected 32 interval rows; got {len(df)}")

    df.to_csv(out_csv, index=False, float_format="%.12g")

    meta = {
        "schema": "CMDO_FIGURE5_U10_STRATEGY_INTERVALS_v0.1",
        "status": "POSTHOC_DESCRIPTIVE_UNCERTAINTY_DO_NOT_REPLACE_PROSPECTIVE_VERDICT",
        "prospective_verdict": "MECHANISM_NOT_CONFIRMED",
        "datasets": list(DATASETS),
        "budgets": list(BUDGETS),
        "strategies": ["shared_adaptive", "fixed_weight_reuse", "permuted_weight_control", "crossfit_adaptive"],
        "n_frozen_replicates": int(mod.REPS),
        "n_bootstrap": int(args.bootstraps),
        "ci_percentiles": list(CI),
        "interpretation": "Intervals quantify frozen Monte-Carlo audit-sampling variability. They are not population-level clinical confidence intervals and are not prospective confirmation.",
        "csv_sha256": mod.sha256_file(out_csv),
    }
    out_json = out_csv.with_suffix(".json")
    out_json.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    print("=" * 118)
    print(" FIGURE 5 U10 STRATEGY INTERVAL AUDIT: PASS")
    print(" Prospective verdict remains MECHANISM_NOT_CONFIRMED")
    print("=" * 118)
    print(df[["dataset", "budget", "strategy", "point_gain_pct", "ci95_low_pct", "ci95_high_pct", "ci_excludes_zero"]].to_string(index=False))
    print()
    print(f"CSV : {out_csv}")
    print(f"JSON: {out_json}")
    print(f"CSV SHA256 : {mod.sha256_file(out_csv)}")
    print(f"JSON SHA256: {mod.sha256_file(out_json)}")
    print("=" * 118)


if __name__ == "__main__":
    main()
