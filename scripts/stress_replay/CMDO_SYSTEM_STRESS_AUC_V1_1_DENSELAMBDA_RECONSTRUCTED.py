#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CMDO controlled AUC stress test v1.1 dense-Lambda — faithful reconstruction.

This script reconstructs the lost post-completion controlled stress-test
program from two frozen sources of authority:
  (1) the final manuscript Methods design; and
  (2) the frozen Stage-U5E pair-complete observer formulas/hyperparameters.

It is NOT claimed to be byte-for-byte identical to the lost 2026-08-31 file.
It is deterministic, self-contained, and produces the exact CSV schema used by
Figure5_PhaseBoundary.m.

Design
------
true AUCs              0.55, 0.65, 0.75
balanced audit budgets 8, 16, 32, 64, 128
Lambda                 0, .25, .5, .75, 1, 1.5, 2, 4
bias directions        both signs for Lambda>0, one state at Lambda=0
states/method           225
calibration repeats     500 per AUC x budget
analysis repeats        200 per state

The Gaussian construction uses N(0,1) negatives and N(d,1) positives with
  d = sqrt(2) * Phi^{-1}(AUC),
which gives the requested population AUC under equal variances.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

# -----------------------------------------------------------------------------
# Frozen U5E constants
# -----------------------------------------------------------------------------
BUDGETS = np.asarray([8, 16, 32, 64, 128], dtype=int)
TRUE_AUCS = np.asarray([0.55, 0.65, 0.75], dtype=float)
LAMBDAS = np.asarray([0.0, 0.25, 0.50, 0.75, 1.0, 1.50, 2.0, 4.0], dtype=float)
N_CALIBRATION = 500
N_REPLICATES = 200
BASE_SEED = 20260724
DELTA_TOTAL = 0.10
DELTA_BLOCK = DELTA_TOTAL / 4.0
MAX_WEIGHT = 0.35
RISK_COEFFICIENT = 8.0
SUPPORT_GATE = 1.0
TRANSPORT_RISK_PROXY = 0.0
Z_DELONG = float(norm.ppf(1.0 - DELTA_BLOCK / 2.0))

METHODS = [
    "DIRECT",
    "PC_PAIRED_HOEFFDING",
    "PC_USTAT_MCDIARMID",
    "PC_DELONG",
    "PC_DELONG_VARGATE",
    "PC_PLUGIN",
    "PC_PLUGIN_VARGATE",
    "PC_ORACLE",
]
METHOD_LABEL = {
    "DIRECT": "Direct",
    "PC_PAIRED_HOEFFDING": "CMDO",
    "PC_USTAT_MCDIARMID": "U-stat",
    "PC_DELONG": "DeLong",
    "PC_DELONG_VARGATE": "DeLong + gate",
    "PC_PLUGIN": "Plug-in",
    "PC_PLUGIN_VARGATE": "Plug-in + gate",
    "PC_ORACLE": "Oracle",
}
OPPOSITE = {"AA": "BB", "BB": "AA", "AB": "BA", "BA": "AB"}
BLOCK_ORDER = ("AA", "AB", "BA", "BB")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def auc_and_variance(pos_scores: np.ndarray, neg_scores: np.ndarray) -> Tuple[float, float]:
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    kernel = (
        (pos[:, None] > neg[None, :]).astype(float)
        + 0.5 * (pos[:, None] == neg[None, :]).astype(float)
    )
    auc = float(kernel.mean())
    row = kernel.mean(axis=1)
    col = kernel.mean(axis=0)
    row_var = float(np.var(row, ddof=1)) if len(row) > 1 else 0.0
    col_var = float(np.var(col, ddof=1)) if len(col) > 1 else 0.0
    variance = max(0.0, row_var / len(row) + col_var / len(col))
    return auc, variance


def paired_sensor(pos_scores: np.ndarray, neg_scores: np.ndarray, rng: np.random.Generator):
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    h = min(len(pos), len(neg))
    pos = pos[rng.permutation(len(pos))[:h]]
    neg = neg[rng.permutation(len(neg))[:h]]
    values = (pos > neg).astype(float) + 0.5 * (pos == neg)
    variance = float(np.var(values, ddof=1)) if h > 1 else 0.0
    return float(values.mean()), variance, int(h)


def sensor_radius(method: str, sensor_size: int, delong_variance: float) -> float:
    if method == "PC_PAIRED_HOEFFDING":
        return min(1.0, math.sqrt(math.log(2.0 / DELTA_BLOCK) / (2.0 * sensor_size)))
    if method == "PC_USTAT_MCDIARMID":
        return min(1.0, math.sqrt(math.log(2.0 / DELTA_BLOCK) / sensor_size))
    if method == "PC_DELONG":
        return min(1.0, Z_DELONG * math.sqrt(max(delong_variance, 1e-12)))
    raise ValueError(method)


def weight_from_ucb(variance: float, bias_upper_sq: float) -> float:
    return SUPPORT_GATE * min(
        MAX_WEIGHT,
        float(variance)
        / (float(variance) + float(bias_upper_sq) + RISK_COEFFICIENT * TRANSPORT_RISK_PROXY + 1e-12),
    )


def plugin_weight(variance: float, bias_hat_sq: float) -> float:
    return SUPPORT_GATE * min(
        MAX_WEIGHT,
        float(variance)
        / (float(variance) + 0.5 * float(bias_hat_sq) + RISK_COEFFICIENT * TRANSPORT_RISK_PROXY + 1e-12),
    )


def gaussian_separation(true_auc: float) -> float:
    return math.sqrt(2.0) * float(norm.ppf(true_auc))


def sample_current(true_auc: float, budget: int, rng: np.random.Generator):
    per_class = budget // 2
    d = gaussian_separation(true_auc)
    pos = rng.normal(d, 1.0, per_class)
    neg = rng.normal(0.0, 1.0, per_class)
    pos = pos[rng.permutation(per_class)]
    neg = neg[rng.permutation(per_class)]
    half = per_class // 2
    return pos[:half], pos[half:], neg[:half], neg[half:]


def compute_blocks(pos_a, pos_b, neg_a, neg_b, rng):
    blocks = {
        "AA": (pos_a, neg_a),
        "AB": (pos_a, neg_b),
        "BA": (pos_b, neg_a),
        "BB": (pos_b, neg_b),
    }
    block_auc: Dict[str, float] = {}
    block_var: Dict[str, float] = {}
    paired: Dict[str, tuple] = {}
    for name in BLOCK_ORDER:
        block_auc[name], block_var[name] = auc_and_variance(*blocks[name])
        paired[name] = paired_sensor(*blocks[name], rng)
    return blocks, block_auc, block_var, paired


def build_method(method, block_auc, block_var, paired, transport_auc, true_bias_sq, full_variance):
    weights: Dict[str, float] = {}
    block_risk_upper: Dict[str, float] = {}

    if method == "PC_ORACLE":
        for block in BLOCK_ORDER:
            v = block_var[block]
            w = SUPPORT_GATE * min(
                MAX_WEIGHT,
                v / (v + true_bias_sq + RISK_COEFFICIENT * TRANSPORT_RISK_PROXY + 1e-12),
            )
            weights[block] = w
            block_risk_upper[block] = (1.0 - w) ** 2 * v + w**2 * true_bias_sq

    elif method in {"PC_PLUGIN", "PC_PLUGIN_VARGATE"}:
        for block in BLOCK_ORDER:
            sensor = OPPOSITE[block]
            bias_hat_sq = max(
                0.0,
                (block_auc[sensor] - transport_auc) ** 2 - block_var[sensor],
            )
            w = plugin_weight(block_var[block], bias_hat_sq)
            weights[block] = w
            block_risk_upper[block] = (1.0 - w) ** 2 * block_var[block] + w**2 * bias_hat_sq

    else:
        radius_method = method.replace("_VARGATE", "")
        for block in BLOCK_ORDER:
            sensor = OPPOSITE[block]
            if radius_method == "PC_PAIRED_HOEFFDING":
                sensor_value, _, sensor_n = paired[sensor]
                rad = sensor_radius(radius_method, sensor_n, block_var[sensor])
            else:
                sensor_value = block_auc[sensor]
                sensor_n = int(paired[sensor][2])
                rad = sensor_radius(radius_method, sensor_n, block_var[sensor])
            upper = min(1.0, abs(sensor_value - transport_auc) + rad) ** 2
            w = weight_from_ucb(block_var[block], upper)
            weights[block] = w
            block_risk_upper[block] = (1.0 - w) ** 2 * block_var[block] + w**2 * upper

    pre_gate_mean_weight = float(np.mean(list(weights.values())))
    pre_gate_risk_proxy = float(np.mean(list(block_risk_upper.values())))
    fallback = False
    if method.endswith("_VARGATE") and pre_gate_risk_proxy > float(full_variance):
        weights = {k: 0.0 for k in weights}
        fallback = True

    estimate = float(
        np.mean(
            [
                (1.0 - weights[k]) * block_auc[k] + weights[k] * transport_auc
                for k in BLOCK_ORDER
            ]
        )
    )
    return {
        "estimate": estimate,
        "mean_weight": float(np.mean(list(weights.values()))),
        "max_weight": float(np.max(list(weights.values()))),
        "fallback": bool(fallback),
        "pre_gate_mean_weight": pre_gate_mean_weight,
        "pre_gate_risk_proxy": pre_gate_risk_proxy,
    }


def calibration_seed(auc_index: int, budget_index: int, replicate: int) -> int:
    # Reconstruction seed schedule: deterministic and independent of evaluation.
    return BASE_SEED + 500_000_000 + auc_index * 1_000_000 + budget_index * 10_000 + replicate


def evaluation_seed(auc_index: int, budget_index: int, lambda_index: int, sign_code: int, replicate: int) -> int:
    state_index = auc_index * 10_000 + budget_index * 1_000 + lambda_index * 10 + sign_code
    return BASE_SEED + 100_000_000 + state_index * 1_000 + replicate


def calibrate_direct_variance(true_auc: float, budget: int, auc_index: int, budget_index: int) -> dict:
    direct = np.empty(N_CALIBRATION, dtype=float)
    estimated_variance = np.empty(N_CALIBRATION, dtype=float)
    for r in range(N_CALIBRATION):
        rng = np.random.default_rng(calibration_seed(auc_index, budget_index, r))
        per_class = budget // 2
        d = gaussian_separation(true_auc)
        pos = rng.normal(d, 1.0, per_class)
        neg = rng.normal(0.0, 1.0, per_class)
        direct[r], estimated_variance[r] = auc_and_variance(pos, neg)
    return {
        "true_auc": true_auc,
        "budget": budget,
        "v_ref": float(np.var(direct, ddof=1)),
        "mean_direct_auc": float(np.mean(direct)),
        "direct_mae_calibration": float(np.mean(np.abs(direct - true_auc))),
        "mean_delong_variance": float(np.mean(estimated_variance)),
    }


def state_signs(lam: float):
    return [(0, 0)] if lam == 0 else [(-1, 0), (+1, 2)]


def run(outdir: Path, save_replicates: bool = False):
    outdir.mkdir(parents=True, exist_ok=True)

    calibration_rows = []
    vref = {}
    print("[1/3] Calibrating same-budget direct AUC variance (500 deterministic repeats/cell)")
    for ia, auc in enumerate(TRUE_AUCS):
        for ib, budget in enumerate(BUDGETS):
            rec = calibrate_direct_variance(float(auc), int(budget), ia, ib)
            calibration_rows.append(rec)
            vref[(float(auc), int(budget))] = rec["v_ref"]
            print(f"  AUC={auc:.2f} m={budget:3d}  V_ref={rec['v_ref']:.10f}")

    state_acc = {}
    replicate_rows = [] if save_replicates else None

    print("\n[2/3] Running 225 stress states x 200 deterministic repeats")
    for ia, auc0 in enumerate(TRUE_AUCS):
        true_auc = float(auc0)
        for ib, b0 in enumerate(BUDGETS):
            budget = int(b0)
            V = vref[(true_auc, budget)]
            for il, l0 in enumerate(LAMBDAS):
                lam = float(l0)
                for bias_sign, sign_code in state_signs(lam):
                    bias = 0.0 if lam == 0 else bias_sign * math.sqrt(lam * V)
                    transport_auc = float(np.clip(true_auc + bias, 0.0, 1.0))
                    true_bias_sq = (transport_auc - true_auc) ** 2

                    # Direct and every comparator share the same 200 current samples.
                    store = {
                        m: {"abs_error": [], "weight": [], "fallback": []}
                        for m in METHODS
                    }
                    for r in range(N_REPLICATES):
                        seed = evaluation_seed(ia, ib, il, sign_code, r)
                        rng = np.random.default_rng(seed)
                        pos_a, pos_b, neg_a, neg_b = sample_current(true_auc, budget, rng)
                        full_pos = np.concatenate([pos_a, pos_b])
                        full_neg = np.concatenate([neg_a, neg_b])
                        direct_auc, full_var = auc_and_variance(full_pos, full_neg)
                        _, block_auc, block_var, paired = compute_blocks(
                            pos_a, pos_b, neg_a, neg_b, rng
                        )

                        store["DIRECT"]["abs_error"].append(abs(direct_auc - true_auc))
                        store["DIRECT"]["weight"].append(0.0)
                        store["DIRECT"]["fallback"].append(False)

                        for method in METHODS[1:]:
                            fit = build_method(
                                method,
                                block_auc,
                                block_var,
                                paired,
                                transport_auc,
                                true_bias_sq,
                                full_var,
                            )
                            err = abs(fit["estimate"] - true_auc)
                            store[method]["abs_error"].append(err)
                            store[method]["weight"].append(fit["mean_weight"])
                            store[method]["fallback"].append(fit["fallback"])

                            if save_replicates:
                                replicate_rows.append(
                                    {
                                        "true_auc": true_auc,
                                        "budget": budget,
                                        "lambda_nominal": lam,
                                        "bias_sign": bias_sign,
                                        "transport_auc": transport_auc,
                                        "replicate": r,
                                        "seed": seed,
                                        "method": method,
                                        "estimate": fit["estimate"],
                                        "direct_estimate": direct_auc,
                                        "abs_error": err,
                                        "direct_abs_error": abs(direct_auc - true_auc),
                                        "mean_weight": fit["mean_weight"],
                                        "fallback": int(fit["fallback"]),
                                    }
                                )

                    direct_mae = float(np.mean(store["DIRECT"]["abs_error"]))
                    for method in METHODS:
                        mae = float(np.mean(store[method]["abs_error"]))
                        state_acc[(true_auc, budget, lam, bias_sign, method)] = {
                            "true_auc": true_auc,
                            "budget": budget,
                            "lambda_nominal": lam,
                            "bias_sign": bias_sign,
                            "historical_bias": transport_auc - true_auc,
                            "transport_auc": transport_auc,
                            "v_ref": V,
                            "method": method,
                            "method_label": METHOD_LABEL[method],
                            "mae": mae,
                            "direct_mae": direct_mae,
                            "mean_excess_mae": mae - direct_mae,
                            "gain_percent": 0.0 if method == "DIRECT" else 100.0 * (direct_mae - mae) / direct_mae,
                            "mean_weight": float(np.mean(store[method]["weight"])),
                            "fallback_rate": float(np.mean(store[method]["fallback"])),
                            "n_replicates": N_REPLICATES,
                        }

    state = pd.DataFrame(list(state_acc.values())).sort_values(
        ["true_auc", "budget", "lambda_nominal", "bias_sign", "method"]
    ).reset_index(drop=True)
    calibration = pd.DataFrame(calibration_rows)

    state_path = outdir / "CMDO_SystemStress_AUC_StateSummary_v1_1.csv"
    calibration_path = outdir / "CMDO_SystemStress_AUC_Calibration_v1_1.csv"
    state.to_csv(state_path, index=False, float_format="%.12g")
    calibration.to_csv(calibration_path, index=False, float_format="%.12g")

    # Compact table candidate: same quantities used in the manuscript summary.
    table_rows = []
    for method in METHODS:
        d = state[state.method == method]
        if method == "DIRECT":
            continue
        noninferior = int((d.mean_excess_mae <= 0.0).sum())
        # largest Lambda that is completely non-inferior across every budget/AUC/sign
        all_budget_crit = 0.0
        for lam in LAMBDAS:
            q = d[np.isclose(d.lambda_nominal, lam)]
            if len(q) and float(q.mean_excess_mae.max()) <= 0.0:
                all_budget_crit = float(lam)
            else:
                break
        table_rows.append(
            {
                "method": method,
                "method_label": METHOD_LABEL[method],
                "mean_gain_percent": float(d.gain_percent.mean()),
                "noninferior_states": noninferior,
                "total_states": int(len(d)),
                "noninferior_fraction": noninferior / len(d),
                "largest_all_budget_complete_noninferior_lambda": all_budget_crit,
                "worst_state_excess_mae": float(d.mean_excess_mae.max()),
            }
        )
    table = pd.DataFrame(table_rows)
    table_path = outdir / "CMDO_SystemStress_AUC_TableCandidate_v1_1.csv"
    table.to_csv(table_path, index=False, float_format="%.12g")

    # Budget x Lambda curves used to independently audit Figure-5 phase maps.
    curve_rows = []
    for method in METHODS[1:]:
        dm = state[state.method == method]
        for budget in BUDGETS:
            for lam in LAMBDAS:
                q = dm[(dm.budget == budget) & np.isclose(dm.lambda_nominal, lam)]
                curve_rows.append(
                    {
                        "method": method,
                        "method_label": METHOD_LABEL[method],
                        "budget": int(budget),
                        "lambda_nominal": float(lam),
                        "worst_excess_mae": float(q.mean_excess_mae.max()),
                        "worst_relative_excess_percent": float((100.0 * q.mean_excess_mae / q.direct_mae).max()),
                        "all_states_noninferior": int(float(q.mean_excess_mae.max()) <= 0.0),
                    }
                )
    curves = pd.DataFrame(curve_rows)
    curve_path = outdir / "CMDO_SystemStress_AUC_LambdaCurves_v1_1.csv"
    curves.to_csv(curve_path, index=False, float_format="%.12g")

    rep_path = None
    if save_replicates:
        rep_path = outdir / "CMDO_SystemStress_AUC_Replicates_v1_1.csv.gz"
        pd.DataFrame(replicate_rows).to_csv(rep_path, index=False, compression="gzip", float_format="%.12g")

    # Figure-5 headline audit for the four displayed methods.
    display_methods = [
        "PC_PAIRED_HOEFFDING",
        "PC_USTAT_MCDIARMID",
        "PC_DELONG",
        "PC_PLUGIN",
    ]
    critical = {}
    for budget in BUDGETS:
        critical[str(int(budget))] = {}
        for method in display_methods:
            d = state[(state.method == method) & (state.budget == budget)]
            crit = 0.0
            for lam in LAMBDAS:
                q = d[np.isclose(d.lambda_nominal, lam)]
                if len(q) and float(q.mean_excess_mae.max()) <= 0.0:
                    crit = float(lam)
                else:
                    break
            critical[str(int(budget))][method] = crit

    keys = ["true_auc", "budget", "lambda_nominal", "bias_sign"]
    cmdo = state[state.method == "PC_PAIRED_HOEFFDING"][keys + ["gain_percent"]].rename(columns={"gain_percent": "gain_cmdo"})
    ustat = state[state.method == "PC_USTAT_MCDIARMID"][keys + ["gain_percent"]].rename(columns={"gain_percent": "gain_ustat"})
    paired = cmdo.merge(ustat, on=keys, how="inner")
    paired = paired[paired.lambda_nominal <= 1.0 + 1e-12].copy()
    paired["advantage_pp"] = paired.gain_cmdo - paired.gain_ustat

    manifest = {
        "name": "CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED",
        "status": "faithful_reconstruction_not_byte_identical_original",
        "source_authority": [
            "final manuscript controlled historical-misspecification stress-test Methods",
            "frozen StageU5E pair-complete observer formulas and hyperparameters",
        ],
        "config": {
            "true_aucs": TRUE_AUCS.tolist(),
            "budgets": BUDGETS.tolist(),
            "lambdas": LAMBDAS.tolist(),
            "n_calibration": N_CALIBRATION,
            "n_replicates": N_REPLICATES,
            "base_seed": BASE_SEED,
            "delta_total": DELTA_TOTAL,
            "delta_block": DELTA_BLOCK,
            "max_weight": MAX_WEIGHT,
            "risk_coefficient": RISK_COEFFICIENT,
            "support_gate": SUPPORT_GATE,
            "transport_risk_proxy": TRANSPORT_RISK_PROXY,
        },
        "state_count_per_method": 225,
        "figure5_audit": {
            "critical_lambda_by_budget": critical,
            "shared_lambda_le_1_mean_cmdo_minus_ustat_advantage_pp": float(paired.advantage_pp.mean()),
            "shared_lambda_le_1_fraction_cmdo_gt_ustat": float((paired.advantage_pp > 0).mean()),
            "shared_lambda_le_1_n_paired_states": int(len(paired)),
        },
        "outputs": {},
    }

    for p in [state_path, calibration_path, table_path, curve_path] + ([rep_path] if rep_path else []):
        manifest["outputs"][p.name] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}

    json_path = outdir / "CMDO_SystemStress_AUC_v1_1.json"
    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print("\n[3/3] Complete")
    print(f"  State summary : {state_path}")
    print(f"  Table summary : {table_path}")
    print(f"  Lambda curves : {curve_path}")
    print(f"  Manifest      : {json_path}")
    print("\nFigure-5 reconstruction audit")
    for budget in BUDGETS:
        q = critical[str(int(budget))]
        print(
            f"  m={budget:3d}: CMDO={q['PC_PAIRED_HOEFFDING']:g}  "
            f"Ustat={q['PC_USTAT_MCDIARMID']:g}  DeLong={q['PC_DELONG']:g}  Plug-in={q['PC_PLUGIN']:g}"
        )
    print(
        "  Lambda<=1 CMDO-Ustat mean advantage = "
        f"{paired.advantage_pp.mean():.4f} pp; CMDO higher = "
        f"{100*(paired.advantage_pp > 0).mean():.2f}%"
    )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="", help="Output directory; defaults to source_data/figure5 beside this script")
    parser.add_argument("--save-replicates", action="store_true", help="Also save replicate-level gzip CSV")
    args = parser.parse_args(argv)
    here = Path(__file__).resolve().parent
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else here / "source_data" / "figure5"
    return run(outdir, save_replicates=args.save_replicates)


if __name__ == "__main__":
    raise SystemExit(main())
