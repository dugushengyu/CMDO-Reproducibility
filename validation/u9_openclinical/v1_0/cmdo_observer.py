from __future__ import annotations
import math
import numpy as np
import pandas as pd
from scipy.stats import beta

def clopper_pearson(k: int, n: int, alpha: float) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n-k+1))
    hi = 1.0 if k == n else float(beta.ppf(1.0-alpha/2.0, k+1, n-k))
    return lo, hi

def _seed(master: int, target_i: int, budget: int, replicate: int) -> int:
    # Deterministic, platform-independent integer mixing.
    x = (int(master) * 1000003 + target_i * 9176 + budget * 131 + replicate * 8191) % (2**32 - 1)
    return int(x if x > 0 else 1)

def evaluate_target(
    *,
    target_name: str,
    y: np.ndarray,
    score: np.ndarray,
    threshold: float,
    historical_accuracy: float,
    budgets: list[int],
    replicates: int,
    master_seed: int,
    folds: int = 4,
    opposite=(2,3,0,1),
    delta_family: float = 0.05,
    max_weight: float = 0.35,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    pred = (score >= threshold).astype(int)
    correct = (pred == y).astype(float)
    theta = float(correct.mean())
    n_target = len(y)
    delta_block = delta_family / folds
    records = []
    for bi, b in enumerate(budgets):
        if b > n_target:
            raise ValueError(f"budget {b} exceeds target N={n_target} for {target_name}")
        if b % folds:
            raise ValueError(f"budget {b} must be divisible by {folds}")
        for r in range(1, replicates+1):
            seed = _seed(master_seed, bi+1, b, r)
            rng = np.random.default_rng(seed)
            idx = rng.choice(n_target, size=b, replace=False)
            z = correct[idx]
            yy = y[idx]
            fold_size = b // folds
            fold_idx = np.arange(b).reshape(folds, fold_size).T
            block_direct, block_est, weights = [], [], []
            coverage, violations = [], []
            for q in range(folds):
                di = fold_idx[:, q]
                ai = fold_idx[:, opposite[q]]
                zd = z[di]
                za = z[ai]
                Dq = float(zd.mean())
                lo, hi = clopper_pearson(int(za.sum()), len(za), delta_block)
                Lq = min(lo*(1-lo), hi*(1-hi)) / len(zd)
                Uq = max((historical_accuracy-lo)**2, (historical_accuracy-hi)**2)
                wq = 0.0 if Lq <= 0 else min(max_weight, 2.0*Lq/(Lq+Uq+np.finfo(float).eps))
                Eq = (1.0-wq)*Dq + wq*historical_accuracy
                covered = (lo <= theta <= hi)
                Vtrue = theta*(1-theta)/len(zd)
                Btrue2 = (historical_accuracy-theta)**2
                oracle_cap = 2.0*Vtrue/(Vtrue+Btrue2+np.finfo(float).eps)
                violation = bool(covered and (wq > oracle_cap + 1e-12))
                block_direct.append(Dq); block_est.append(Eq); weights.append(wq)
                coverage.append(covered); violations.append(violation)
            direct = float(z.mean())
            observer = float(np.mean(block_est))
            fallback = float(np.mean(block_direct))
            records.append({
                "target": target_name,
                "budget": b,
                "replicate": r,
                "seed": seed,
                "target_n": n_target,
                "target_prevalence": float(y.mean()),
                "audit_positive_n": int(yy.sum()),
                "true_accuracy": theta,
                "direct_accuracy": direct,
                "observer_accuracy": observer,
                "direct_abs_error": abs(direct-theta),
                "observer_abs_error": abs(observer-theta),
                "regret": abs(observer-theta)-abs(direct-theta),
                "mean_weight": float(np.mean(weights)),
                "max_weight": float(np.max(weights)),
                "fallback_residual": abs(fallback-direct),
                "simultaneous_coverage": bool(all(coverage)),
                "covered_event_certificate_violations": int(sum(violations)),
            })
    reps = pd.DataFrame(records)
    states = (reps.groupby(["target","budget"], as_index=False)
              .agg(target_n=("target_n","first"),
                   true_accuracy=("true_accuracy","first"),
                   target_prevalence=("target_prevalence","first"),
                   direct_mae=("direct_abs_error","mean"),
                   observer_mae=("observer_abs_error","mean"),
                   regret=("regret","mean"),
                   mean_weight=("mean_weight","mean"),
                   simultaneous_coverage=("simultaneous_coverage","mean"),
                   covered_event_certificate_violations=("covered_event_certificate_violations","sum"),
                   maximum_fallback_residual=("fallback_residual","max")))
    states["relative_gain"] = (states.direct_mae-states.observer_mae)/states.direct_mae.clip(lower=np.finfo(float).eps)
    summary = {
        "target": target_name,
        "target_n": n_target,
        "target_prevalence": float(y.mean()),
        "true_accuracy": theta,
        "historical_accuracy": float(historical_accuracy),
        "historical_accuracy_bias": float(historical_accuracy-theta),
        "direct_mae": float(reps.direct_abs_error.mean()),
        "observer_mae": float(reps.observer_abs_error.mean()),
        "relative_gain": float((reps.direct_abs_error.mean()-reps.observer_abs_error.mean()) /
                               max(reps.direct_abs_error.mean(), np.finfo(float).eps)),
        "worst_state_regret": float(states.regret.max()),
        "mean_weight": float(reps.mean_weight.mean()),
        "mean_simultaneous_coverage": float(states.simultaneous_coverage.mean()),
        "minimum_simultaneous_coverage": float(states.simultaneous_coverage.min()),
        "certificate_violations": int(reps.covered_event_certificate_violations.sum()),
        "maximum_fallback_residual": float(reps.fallback_residual.max()),
    }
    budget_mae = reps.groupby("budget").direct_abs_error.mean().sort_index()
    if len(budget_mae) >= 2 and np.all(budget_mae.values > 0):
        summary["direct_root_budget_slope"] = float(np.polyfit(np.log(budget_mae.index.values),
                                                               np.log(budget_mae.values), 1)[0])
    else:
        summary["direct_root_budget_slope"] = float("nan")
    return reps, states, summary

def synthetic_selftest() -> dict:
    rng = np.random.default_rng(2026081599)
    n = 5000
    y = rng.integers(0, 2, n)
    # Construct correctness probability ~0.72 independent of y.
    correct = rng.random(n) < 0.72
    pred = np.where(correct, y, 1-y)
    score = pred.astype(float)
    reps, states, summary = evaluate_target(
        target_name="synthetic", y=y, score=score, threshold=0.5,
        historical_accuracy=0.70, budgets=[128,256], replicates=10,
        master_seed=2026081598
    )
    if summary["maximum_fallback_residual"] >= 1e-12:
        raise AssertionError("exact fallback selftest failed")
    if not np.isfinite(reps.observer_accuracy).all():
        raise AssertionError("observer selftest produced non-finite values")
    return summary
