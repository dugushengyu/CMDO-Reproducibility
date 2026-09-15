#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_SUMMARY = ROOT / "numerical_closure" / "PCC_V14_TIE_FULL_SUMMARY_20260907.txt"
M_CHOICES = np.array([16, 32, 64, 128, 256], dtype=int)


def auc_var_lower_bound(theta: float, m: int, n: int) -> float:
    if theta <= 0.0 or theta >= 1.0 or m < 2 or n < 2:
        return 0.0
    s = min(m, n)
    ell = max(m, n)
    r = min(theta, 1.0 - theta)
    q = max(theta, 1.0 - theta)
    if (s - 1.0) / (ell - 1.0) <= 2.0 * r:
        B = s - (s - 1.0) ** 2 / (
            12.0 * (ell - 1.0) * theta * (1.0 - theta)
        )
    else:
        B = (
            1.0
            - (m + n - 2.0) * r / q
            + 4.0
            / (3.0 * q)
            * np.sqrt(2.0 * r * (m - 1.0) * (n - 1.0))
        )
    return max(0.0, theta * (1.0 - theta) / (m * n) * B)


def midrank_auc_variance(
    px: np.ndarray, py: np.ndarray, m: int, n: int
) -> tuple[float, float, float, float, float, float]:
    # AUC kernel h(x,y)=1{x>y}+0.5*1{x=y}; support is ordered low->high.
    py_less = np.concatenate(([0.0], np.cumsum(py)[:-1]))
    a = py_less + 0.5 * py

    px_greater = 1.0 - np.cumsum(px)
    b = px_greater + 0.5 * px

    theta = float(np.dot(px, a))
    tau = float(np.dot(px, py))

    eh2 = theta - 0.25 * tau
    var_h = max(0.0, eh2 - theta * theta)
    var_a = max(0.0, float(np.dot(px, a * a) - theta * theta))
    var_b = max(0.0, float(np.dot(py, b * b) - theta * theta))

    true_v = (
        var_h + (n - 1.0) * var_a + (m - 1.0) * var_b
    ) / (m * n)

    A = float(np.dot(px, py * py))
    B = float(np.dot(py, px * px))
    return theta, tau, true_v, A, B, var_h


def verify_archived_full_run() -> None:
    text = ARCHIVED_SUMMARY.read_text(encoding="utf-8")
    required = [
        "Mode: FULL",
        "Random discrete states: 120000",
        "Continuous-BK violations under ties: 26205/120000 (21.837500%)",
        "Min trueV - tau-only tieLB: 4.9183853433e-06",
        "Min trueV - sharp tieLB: 2.33067211364e-11",
        "Max de-atomization identity residual: 5.20417042793e-18",
        "Tie-robust lower-bound audit: PASS",
        "OVERALL MATHEMATICAL VALIDATION: PASS",
    ]
    missing = [line for line in required if line not in text]
    if missing:
        raise AssertionError(
            "Archived PCC-v1.4 FULL summary fingerprint mismatch: "
            + "; ".join(missing)
        )

    match = re.search(
        r"Continuous-BK violations under ties:\s*(\d+)/(\d+)\s*\(([0-9.]+)%\)",
        text,
    )
    if not match:
        raise AssertionError("Could not parse archived continuous-BK violation count")
    if (int(match.group(1)), int(match.group(2))) != (26205, 120000):
        raise AssertionError("Archived historical tie-audit count changed")


def independent_audit(states: int, seed: int) -> dict[str, float | int]:
    # Independent Python implementation of the recorded generation family.
    # The historical PCC-v1.4 run used MATLAB RNG. This implementation uses
    # NumPy RandomState and is therefore a mathematical cross-check, not a
    # byte-for-byte replay of the historical random stream.
    rng = np.random.RandomState(seed)

    continuous_violations = 0
    tie_violations = 0
    sharp_violations = 0
    min_tie_slack = np.inf
    min_sharp_slack = np.inf

    for _ in range(states):
        levels = int(rng.randint(2, 9))
        px = rng.dirichlet(np.ones(levels))
        py = rng.dirichlet(np.ones(levels))
        m = int(rng.choice(M_CHOICES))
        n = int(rng.choice(M_CHOICES))

        theta, tau, true_v, A, B, _ = midrank_auc_variance(px, py, m, n)
        v_bk = auc_var_lower_bound(theta, m, n)

        tie_lb = max(
            0.0,
            v_bk - (m + n + 1.0) * tau / (12.0 * m * n),
        )
        sharp_lb = max(
            0.0,
            v_bk
            - ((n - 1.0) * A + (m - 1.0) * B) / (12.0 * m * n)
            - tau / (4.0 * m * n),
        )

        if v_bk > true_v + 1e-12:
            continuous_violations += 1
        if tie_lb > true_v + 1e-12:
            tie_violations += 1
        if sharp_lb > true_v + 1e-12:
            sharp_violations += 1

        min_tie_slack = min(min_tie_slack, true_v - tie_lb)
        min_sharp_slack = min(min_sharp_slack, true_v - sharp_lb)

    return {
        "states": states,
        "continuous_violations": continuous_violations,
        "continuous_rate": continuous_violations / states,
        "tie_violations": tie_violations,
        "sharp_violations": sharp_violations,
        "min_tie_slack": float(min_tie_slack),
        "min_sharp_slack": float(min_sharp_slack),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Verify the archived PCC-v1.4 tie-audit execution fingerprint and "
            "run an independent Python implementation of the declared discrete-distribution audit."
        )
    )
    ap.add_argument("--states", type=int, default=120000)
    ap.add_argument("--seed", type=int, default=140401)
    args = ap.parse_args()

    if args.states <= 0:
        raise ValueError("--states must be positive")

    verify_archived_full_run()
    result = independent_audit(args.states, args.seed)

    if int(result["tie_violations"]) != 0:
        raise AssertionError(
            f"Tie-robust lower envelope violated in {result['tie_violations']} independent states"
        )
    if int(result["sharp_violations"]) != 0:
        raise AssertionError(
            f"Sharper tie-aware lower envelope violated in {result['sharp_violations']} independent states"
        )
    if not (0.15 <= float(result["continuous_rate"]) <= 0.30):
        raise AssertionError(
            "Independent audit no longer demonstrates the expected failure of the "
            f"unmodified continuous-score bound: rate={result['continuous_rate']:.4f}"
        )

    print("[PASS] Archived PCC-v1.4 FULL tie-audit fingerprint verified.")
    print(
        "[PASS] Historical execution: continuous-BK violations "
        "26205/120000 = 21.837500%; tie-robust violations = 0."
    )
    print(
        "[PASS] Independent Python discrete audit: "
        f"{result['states']} states; continuous-BK violations "
        f"{result['continuous_violations']}/{result['states']} "
        f"({100.0 * float(result['continuous_rate']):.3f}%); "
        "tie-robust violations = 0; sharper-envelope violations = 0."
    )
    print(
        "       Independent minimum slacks: "
        f"tau-only={result['min_tie_slack']:.6g}, "
        f"sharp={result['min_sharp_slack']:.6g}."
    )
    print(
        "[INFO] The independent Python RNG stream is not asserted to be "
        "byte-identical to the archived MATLAB PCC-v1.4 run."
    )


if __name__ == "__main__":
    main()
