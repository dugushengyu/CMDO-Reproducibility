#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Stage U5E — Pair-Complete Cross-Fitted Observer v1.0

Transparent post-U5D development. Uses the exact U5D reconstructed target
scores and labels plus the sealed U5B transport descriptors. Splits each
balanced witness into positive/negative A/B halves, retains all four pair
blocks (AA, AB, BA, BB), and uses the disjoint opposite block to determine each
block's transport weight.

At zero transport weight, the four-block aggregate is exactly the full direct
AUC. No new blind is accessed. No parent result or decision is changed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import shutil
import sys
import time
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score


PROJECT = "Cross-Modal_Diagnostic_Observability"
STAGE = "StageU5E_Pair_Complete_Cross_Fitted_Observer_v1.0"

EXPECTED_U5_FINAL = "0850505e3a603b5c3cca68a44c94c10970218d525cb8364be5a6f148b5059721"
EXPECTED_U5D_FINAL = "d50e5749bb2cf53f8d83c819ab4a832e07c89303d81c142e0012567d13850620"
EXPECTED_U5D_COMPLETE_FILE_SHA = "ceeac8a7d1735991c722c1e5277711ee2c8874a7ada02f730606551c0c1028bd"
EXPECTED_U5D_RAW_SHA = "89fdff551bc7ac527cc0a9fa87cff5ccdf91e3b11e3d6d79baae53fa2603544c"
EXPECTED_U5D_RAW_MANIFEST_SHA = "c8ad053feb82fdfbe1241a5530ccaa847d1d8ca42d5a09f5f9f1d3c21a39ab00"
EXPECTED_U5_DESCRIPTOR_SHA = "84465a697f27e5d1f2d58604f8c0c1f04d1c646dd2af4b6be384b5431246bc54"

BUDGETS = np.asarray([8, 16, 32, 64, 128], dtype=int)
N_REPLICATES = 200
SEED = 20260724
DELTA_TOTAL = 0.10
DELTA_BLOCK = DELTA_TOTAL / 4.0
MAX_WEIGHT = 0.35
RISK_COEFFICIENT = 8.0
U5D_DELONG_WORST_REGRET = 0.013707302436436253
PRIMARY_METHOD = "PC_DELONG_VARGATE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def locate_project_root() -> Path:
    candidates = [
        Path("/content/drive/MyDrive") / PROJECT,
        Path("/content/drive/Shareddrives") / PROJECT,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = [path for path in Path("/content/drive").rglob(PROJECT) if path.is_dir()]
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Cannot uniquely locate project root: {matches}")


def auc_kernel(pos_scores: np.ndarray, neg_scores: np.ndarray) -> np.ndarray:
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    return (
        (pos[:, None] > neg[None, :]).astype(float)
        + 0.5 * (pos[:, None] == neg[None, :]).astype(float)
    )


def auc_and_variance(pos_scores: np.ndarray, neg_scores: np.ndarray) -> Tuple[float, float]:
    matrix = auc_kernel(pos_scores, neg_scores)
    auc = float(matrix.mean())
    row = matrix.mean(axis=1)
    col = matrix.mean(axis=0)
    row_var = float(np.var(row, ddof=1)) if len(row) > 1 else 0.0
    col_var = float(np.var(col, ddof=1)) if len(col) > 1 else 0.0
    variance = max(0.0, row_var / len(row) + col_var / len(col))
    return auc, variance


def paired_sensor(
    pos_scores: np.ndarray,
    neg_scores: np.ndarray,
    rng: np.random.Generator,
) -> Tuple[float, float, int]:
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    h = min(len(pos), len(neg))
    pos = pos[rng.permutation(len(pos))[:h]]
    neg = neg[rng.permutation(len(neg))[:h]]
    values = (pos > neg).astype(float) + 0.5 * (pos == neg).astype(float)
    variance = float(np.var(values, ddof=1)) if h > 1 else 0.0
    return float(values.mean()), variance, h


def sensor_radius(
    method: str,
    sensor_variance: float,
    sensor_size: int,
    delong_variance: float,
) -> float:
    if method == "PC_PAIRED_HOEFFDING":
        return min(
            1.0,
            math.sqrt(math.log(2.0 / DELTA_BLOCK) / (2.0 * sensor_size)),
        )
    if method == "PC_USTAT_MCDIARMID":
        return min(
            1.0,
            math.sqrt(math.log(2.0 / DELTA_BLOCK) / sensor_size),
        )
    if method in {"PC_DELONG", "PC_DELONG_VARGATE"}:
        return min(
            1.0,
            float(norm.ppf(1.0 - DELTA_BLOCK / 2.0))
            * math.sqrt(max(delong_variance, 1e-12)),
        )
    raise ValueError(method)


def weight_from_ucb(
    variance: float,
    bias_upper_sq: float,
    support: float,
    risk: float,
) -> float:
    return float(support) * min(
        MAX_WEIGHT,
        float(variance)
        / (
            float(variance)
            + float(bias_upper_sq)
            + RISK_COEFFICIENT * float(risk)
            + 1e-12
        ),
    )


def plugin_weight(
    variance: float,
    bias_hat_sq: float,
    support: float,
    risk: float,
) -> float:
    return float(support) * min(
        MAX_WEIGHT,
        float(variance)
        / (
            float(variance)
            + 0.5 * float(bias_hat_sq)
            + RISK_COEFFICIENT * float(risk)
            + 1e-12
        ),
    )


def block_scores(
    pos_a: np.ndarray,
    pos_b: np.ndarray,
    neg_a: np.ndarray,
    neg_b: np.ndarray,
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    return {
        "AA": (pos_a, neg_a),
        "AB": (pos_a, neg_b),
        "BA": (pos_b, neg_a),
        "BB": (pos_b, neg_b),
    }


OPPOSITE = {"AA": "BB", "BB": "AA", "AB": "BA", "BA": "AB"}


def exact_pair_complete_identity(block_auc: Dict[str, float], full_auc: float) -> float:
    return abs(float(np.mean(list(block_auc.values()))) - float(full_auc))


def build_method(
    method: str,
    block_auc: Dict[str, float],
    block_variance: Dict[str, float],
    paired_sensors: Dict[str, Tuple[float, float, int]],
    transport_auc: float,
    support: float,
    risk: float,
    true_bias_sq: float,
    full_variance: float,
) -> Dict[str, Any]:
    weights: Dict[str, float] = {}
    bias_upper: Dict[str, float] = {}
    coverage: Dict[str, bool] = {}
    block_risk_upper: Dict[str, float] = {}

    if method == "PC_ORACLE":
        for block in block_auc:
            variance = block_variance[block]
            weight = float(support) * min(
                MAX_WEIGHT,
                variance
                / (
                    variance
                    + true_bias_sq
                    + RISK_COEFFICIENT * float(risk)
                    + 1e-12
                ),
            )
            weights[block] = weight
            bias_upper[block] = true_bias_sq
            coverage[block] = True
            block_risk_upper[block] = (
                (1.0 - weight) ** 2 * variance + weight**2 * true_bias_sq
            )
    elif method in {"PC_PLUGIN", "PC_PLUGIN_VARGATE"}:
        for block in block_auc:
            sensor = OPPOSITE[block]
            bias_hat_sq = max(
                0.0,
                (block_auc[sensor] - transport_auc) ** 2
                - block_variance[sensor],
            )
            weight = plugin_weight(
                block_variance[block],
                bias_hat_sq,
                support,
                risk,
            )
            weights[block] = weight
            bias_upper[block] = bias_hat_sq
            coverage[block] = np.nan
            block_risk_upper[block] = (
                (1.0 - weight) ** 2 * block_variance[block]
                + weight**2 * bias_hat_sq
            )
    else:
        radius_method = method.replace("_VARGATE", "")
        for block in block_auc:
            sensor = OPPOSITE[block]
            if radius_method == "PC_PAIRED_HOEFFDING":
                sensor_value, sensor_var, sensor_n = paired_sensors[sensor]
                radius = sensor_radius(
                    radius_method,
                    sensor_var,
                    sensor_n,
                    block_variance[sensor],
                )
            else:
                sensor_value = block_auc[sensor]
                radius = sensor_radius(
                    radius_method,
                    0.0,
                    int(paired_sensors[sensor][2]),
                    block_variance[sensor],
                )
            upper = min(
                1.0,
                abs(sensor_value - transport_auc) + radius,
            ) ** 2
            weight = weight_from_ucb(
                block_variance[block],
                upper,
                support,
                risk,
            )
            weights[block] = weight
            bias_upper[block] = upper
            coverage[block] = bool(upper >= true_bias_sq)
            block_risk_upper[block] = (
                (1.0 - weight) ** 2 * block_variance[block]
                + weight**2 * upper
            )

    pre_gate_weights = dict(weights)
    pre_gate_risk_proxy = float(np.mean(list(block_risk_upper.values())))
    used_variance_gate = method.endswith("_VARGATE")
    fallback = False
    if used_variance_gate and pre_gate_risk_proxy > float(full_variance):
        weights = {key: 0.0 for key in weights}
        fallback = True

    estimates = {
        block: (1.0 - weights[block]) * block_auc[block]
        + weights[block] * transport_auc
        for block in block_auc
    }
    estimate = float(np.mean(list(estimates.values())))
    simultaneous_coverage = (
        bool(all(value for value in coverage.values()))
        if all(isinstance(value, (bool, np.bool_)) for value in coverage.values())
        else np.nan
    )
    block_geometry = []
    for block in block_auc:
        true_risk = (
            (1.0 - weights[block]) ** 2 * block_variance[block]
            + weights[block] ** 2 * true_bias_sq
        )
        block_geometry.append(true_risk <= block_variance[block] + 1e-14)

    return {
        "estimate": estimate,
        "mean_weight": float(np.mean(list(weights.values()))),
        "max_weight": float(np.max(list(weights.values()))),
        "fallback_to_full_direct": fallback,
        "pre_gate_mean_weight": float(np.mean(list(pre_gate_weights.values()))),
        "pre_gate_risk_proxy": pre_gate_risk_proxy,
        "full_direct_variance": float(full_variance),
        "simultaneous_coverage": simultaneous_coverage,
        "block_coverage_rate": (
            float(np.mean(list(coverage.values())))
            if all(isinstance(value, (bool, np.bool_)) for value in coverage.values())
            else np.nan
        ),
        "block_no_harm_geometry": bool(all(block_geometry)),
        "weights": weights,
        "bias_upper": bias_upper,
    }


def analyse_pair_complete(
    raw: pd.DataFrame,
    transport: pd.DataFrame,
) -> pd.DataFrame:
    target_map = {
        (family, target): group.sort_values("row_index")
        for (family, target), group in raw.groupby(["family", "target"])
    }
    transport_index = transport.set_index(["family", "target"])
    methods = [
        "PC_PAIRED_HOEFFDING",
        "PC_USTAT_MCDIARMID",
        "PC_DELONG",
        "PC_DELONG_VARGATE",
        "PC_PLUGIN",
        "PC_PLUGIN_VARGATE",
        "PC_ORACLE",
    ]
    rows: List[Dict[str, Any]] = []
    target_counter = 0

    for (family, target), group in sorted(target_map.items()):
        scores = group["score"].to_numpy(dtype=float)
        labels = group["label"].to_numpy(dtype=int)
        positives = np.where(labels == 1)[0]
        negatives = np.where(labels == 0)[0]
        true_auc = float(roc_auc_score(labels, scores))
        descriptor = transport_index.loc[(family, target)]
        transport_auc = float(descriptor["transport_auc"])
        support = float(descriptor["support_gate"])
        risk = float(descriptor["transport_risk_proxy"])
        true_bias_sq = (transport_auc - true_auc) ** 2

        for budget in BUDGETS:
            per_class = int(budget // 2)
            half_class = int(per_class // 2)
            for replicate in range(N_REPLICATES):
                rng = np.random.default_rng(
                    SEED + target_counter * 100000 + int(budget) * 1000 + replicate
                )
                selected_pos = rng.choice(
                    positives,
                    size=per_class,
                    replace=False,
                )
                selected_neg = rng.choice(
                    negatives,
                    size=per_class,
                    replace=False,
                )
                selected_pos = selected_pos[rng.permutation(per_class)]
                selected_neg = selected_neg[rng.permutation(per_class)]

                pos_a = scores[selected_pos[:half_class]]
                pos_b = scores[selected_pos[half_class:]]
                neg_a = scores[selected_neg[:half_class]]
                neg_b = scores[selected_neg[half_class:]]

                full_pos = np.concatenate([pos_a, pos_b])
                full_neg = np.concatenate([neg_a, neg_b])
                direct_full_auc, direct_full_variance = auc_and_variance(
                    full_pos,
                    full_neg,
                )

                blocks = block_scores(pos_a, pos_b, neg_a, neg_b)
                block_auc: Dict[str, float] = {}
                block_variance: Dict[str, float] = {}
                paired: Dict[str, Tuple[float, float, int]] = {}
                for name, (pos_scores, neg_scores) in blocks.items():
                    block_auc[name], block_variance[name] = auc_and_variance(
                        pos_scores,
                        neg_scores,
                    )
                    paired[name] = paired_sensor(pos_scores, neg_scores, rng)

                identity_residual = exact_pair_complete_identity(
                    block_auc,
                    direct_full_auc,
                )

                for method in methods:
                    result = build_method(
                        method,
                        block_auc,
                        block_variance,
                        paired,
                        transport_auc,
                        support,
                        risk,
                        true_bias_sq,
                        direct_full_variance,
                    )
                    estimate = result["estimate"]
                    rows.append(
                        {
                            "family": family,
                            "target": target,
                            "budget": int(budget),
                            "replicate": replicate,
                            "method": method,
                            "true_auc": true_auc,
                            "transport_auc": transport_auc,
                            "true_bias_sq": true_bias_sq,
                            "support_gate": support,
                            "transport_risk_proxy": risk,
                            "direct_full_auc": direct_full_auc,
                            "direct_full_variance": direct_full_variance,
                            "pair_complete_direct_auc": float(
                                np.mean(list(block_auc.values()))
                            ),
                            "identity_residual": identity_residual,
                            "estimate": estimate,
                            "absolute_error": abs(estimate - true_auc),
                            "direct_full_abs_error": abs(
                                direct_full_auc - true_auc
                            ),
                            "squared_error": (estimate - true_auc) ** 2,
                            "direct_full_squared_error": (
                                direct_full_auc - true_auc
                            ) ** 2,
                            "mean_weight": result["mean_weight"],
                            "max_weight": result["max_weight"],
                            "pre_gate_mean_weight": result["pre_gate_mean_weight"],
                            "pre_gate_risk_proxy": result["pre_gate_risk_proxy"],
                            "fallback_to_full_direct": result[
                                "fallback_to_full_direct"
                            ],
                            "simultaneous_coverage": result[
                                "simultaneous_coverage"
                            ],
                            "block_coverage_rate": result[
                                "block_coverage_rate"
                            ],
                            "block_no_harm_geometry": result[
                                "block_no_harm_geometry"
                            ],
                        }
                    )

                # Full-direct comparators.
                plugin_bias = max(
                    0.0,
                    (direct_full_auc - transport_auc) ** 2
                    - direct_full_variance,
                )
                plugin_full_weight = plugin_weight(
                    direct_full_variance,
                    plugin_bias,
                    support,
                    risk,
                )
                plugin_full = (
                    (1.0 - plugin_full_weight) * direct_full_auc
                    + plugin_full_weight * transport_auc
                )
                oracle_full_weight = float(support) * min(
                    MAX_WEIGHT,
                    direct_full_variance
                    / (
                        direct_full_variance
                        + true_bias_sq
                        + RISK_COEFFICIENT * risk
                        + 1e-12
                    ),
                )
                oracle_full = (
                    (1.0 - oracle_full_weight) * direct_full_auc
                    + oracle_full_weight * transport_auc
                )
                for method, estimate, weight in [
                    ("DIRECT_FULL", direct_full_auc, 0.0),
                    ("PLUGIN_FULL", plugin_full, plugin_full_weight),
                    ("ORACLE_FULL", oracle_full, oracle_full_weight),
                ]:
                    rows.append(
                        {
                            "family": family,
                            "target": target,
                            "budget": int(budget),
                            "replicate": replicate,
                            "method": method,
                            "true_auc": true_auc,
                            "transport_auc": transport_auc,
                            "true_bias_sq": true_bias_sq,
                            "support_gate": support,
                            "transport_risk_proxy": risk,
                            "direct_full_auc": direct_full_auc,
                            "direct_full_variance": direct_full_variance,
                            "pair_complete_direct_auc": float(
                                np.mean(list(block_auc.values()))
                            ),
                            "identity_residual": identity_residual,
                            "estimate": estimate,
                            "absolute_error": abs(estimate - true_auc),
                            "direct_full_abs_error": abs(
                                direct_full_auc - true_auc
                            ),
                            "squared_error": (estimate - true_auc) ** 2,
                            "direct_full_squared_error": (
                                direct_full_auc - true_auc
                            ) ** 2,
                            "mean_weight": weight,
                            "max_weight": weight,
                            "pre_gate_mean_weight": weight,
                            "pre_gate_risk_proxy": np.nan,
                            "fallback_to_full_direct": False,
                            "simultaneous_coverage": np.nan,
                            "block_coverage_rate": np.nan,
                            "block_no_harm_geometry": np.nan,
                        }
                    )
        target_counter += 1

    return pd.DataFrame(rows)


def summarize_results(
    replicates: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    states = (
        replicates.groupby(
            ["family", "target", "budget", "method"],
            as_index=False,
        )
        .agg(
            mae=("absolute_error", "mean"),
            mse=("squared_error", "mean"),
            direct_full_mae=("direct_full_abs_error", "mean"),
            direct_full_mse=("direct_full_squared_error", "mean"),
            mean_weight=("mean_weight", "mean"),
            pre_gate_mean_weight=("pre_gate_mean_weight", "mean"),
            fallback_rate=("fallback_to_full_direct", "mean"),
            simultaneous_coverage=("simultaneous_coverage", "mean"),
            block_coverage_rate=("block_coverage_rate", "mean"),
            block_no_harm_rate=("block_no_harm_geometry", "mean"),
            maximum_identity_residual=("identity_residual", "max"),
        )
    )
    states["mae_regret_vs_full_direct"] = (
        states["mae"] - states["direct_full_mae"]
    )
    states["mse_regret_vs_full_direct"] = (
        states["mse"] - states["direct_full_mse"]
    )

    summary = (
        states.groupby("method", as_index=False)
        .agg(
            pooled_mae=("mae", "mean"),
            pooled_mse=("mse", "mean"),
            pooled_direct_full_mae=("direct_full_mae", "mean"),
            worst_target_budget_regret=("mae_regret_vs_full_direct", "max"),
            median_target_budget_regret=("mae_regret_vs_full_direct", "median"),
            mean_weight=("mean_weight", "mean"),
            pre_gate_mean_weight=("pre_gate_mean_weight", "mean"),
            fallback_rate=("fallback_rate", "mean"),
            mean_simultaneous_coverage=("simultaneous_coverage", "mean"),
            minimum_simultaneous_coverage=("simultaneous_coverage", "min"),
            minimum_block_no_harm_rate=("block_no_harm_rate", "min"),
            maximum_identity_residual=("maximum_identity_residual", "max"),
        )
    )
    summary["gain_vs_full_direct"] = (
        1.0 - summary["pooled_mae"] / summary["pooled_direct_full_mae"]
    )

    target_summary = (
        replicates.groupby(
            ["family", "target", "method"],
            as_index=False,
        )
        .agg(
            mae=("absolute_error", "mean"),
            direct_full_mae=("direct_full_abs_error", "mean"),
            mean_weight=("mean_weight", "mean"),
            fallback_rate=("fallback_to_full_direct", "mean"),
        )
    )
    target_summary["gain_vs_full_direct"] = (
        1.0 - target_summary["mae"] / target_summary["direct_full_mae"]
    )
    return states, summary, target_summary


def make_figures(
    output_dir: Path,
    summary: pd.DataFrame,
    states: pd.DataFrame,
    target_summary: pd.DataFrame,
) -> None:
    display_methods = [
        "DIRECT_FULL",
        "PLUGIN_FULL",
        "PC_PLUGIN",
        "PC_DELONG",
        "PC_DELONG_VARGATE",
        "PC_PAIRED_HOEFFDING",
        "PC_ORACLE",
        "ORACLE_FULL",
    ]
    display = summary[summary["method"].isin(display_methods)].copy()

    plt.figure(figsize=(9.0, 5.2))
    plt.bar(display["method"], display["pooled_mae"])
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("Pooled MAE")
    plt.title("Pair-complete observer performance")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U5E_1_Method_MAE.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8.0, 5.4))
    for _, row in display.iterrows():
        plt.scatter(
            row["worst_target_budget_regret"],
            row["pooled_mae"],
            s=70,
        )
        plt.annotate(
            row["method"],
            (
                row["worst_target_budget_regret"],
                row["pooled_mae"],
            ),
            fontsize=8,
        )
    plt.axvline(0.005, linestyle="--")
    plt.xlabel("Worst target-budget regret versus full direct")
    plt.ylabel("Pooled MAE")
    plt.title("Efficiency–tail-safety frontier after pair completion")
    plt.tight_layout()
    plt.savefig(
        output_dir / "Figure_U5E_2_Efficiency_Tail_Safety.png",
        dpi=180,
    )
    plt.close()

    primary = states[states["method"] == PRIMARY_METHOD]
    budget = (
        primary.groupby("budget", as_index=False)
        .agg(
            mean_weight=("mean_weight", "mean"),
            fallback_rate=("fallback_rate", "mean"),
            coverage=("simultaneous_coverage", "mean"),
        )
    )
    plt.figure(figsize=(7.6, 5.0))
    plt.plot(
        budget["budget"],
        budget["mean_weight"],
        marker="o",
        label="Mean retained weight",
    )
    plt.plot(
        budget["budget"],
        budget["fallback_rate"],
        marker="o",
        label="Fallback rate",
    )
    plt.xscale("log", base=2)
    plt.xlabel("Total balanced label budget")
    plt.ylabel("Rate / weight")
    plt.title("Primary pair-complete observer by label budget")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        output_dir / "Figure_U5E_3_Primary_Weight_And_Fallback.png",
        dpi=180,
    )
    plt.close()

    target = target_summary[target_summary["method"] == PRIMARY_METHOD].copy()
    target = target.sort_values("gain_vs_full_direct")
    plt.figure(figsize=(8.4, 5.4))
    plt.barh(target["target"], target["gain_vs_full_direct"])
    plt.axvline(0.0, linestyle="--")
    plt.xlabel("Target-level gain versus full direct")
    plt.title("Primary pair-complete observer across targets")
    plt.tight_layout()
    plt.savefig(
        output_dir / "Figure_U5E_4_Target_Level_Gain.png",
        dpi=180,
    )
    plt.close()

    identity = (
        states.groupby("budget", as_index=False)
        .agg(maximum_identity_residual=("maximum_identity_residual", "max"))
    )
    plt.figure(figsize=(7.2, 4.8))
    plt.plot(
        identity["budget"],
        identity["maximum_identity_residual"],
        marker="o",
    )
    plt.yscale("log")
    plt.xscale("log", base=2)
    plt.xlabel("Total balanced label budget")
    plt.ylabel("Maximum |four-block direct − full direct|")
    plt.title("Pair-complete zero-weight identity")
    plt.tight_layout()
    plt.savefig(
        output_dir / "Figure_U5E_5_Pair_Complete_Identity.png",
        dpi=180,
    )
    plt.close()


def durable_manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    excluded = {
        "StageU5E_Durable_Manifest_v1.0.csv",
        "StageU5E_Canonical_Records_v1.0.zip",
    }
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in excluded:
            rows.append(
                {
                    "relative_path": str(path.relative_to(output_dir)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    started = time.time()
    random.seed(SEED)
    np.random.seed(SEED)
    warnings.filterwarnings("ignore", category=FutureWarning)

    protocol_path = Path(os.environ["CMDO_U5E_PROTOCOL_PATH"]).resolve()
    auth_path = Path(os.environ["CMDO_U5E_AUTH_PATH"]).resolve()
    theory_path = Path(os.environ["CMDO_U5E_THEORY_PATH"]).resolve()
    pipeline_path = Path(__file__).resolve()

    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    release_ok = bool(
        auth.get("u5e_protocol_sha256") == sha256_file(protocol_path)
        and auth.get("u5e_pipeline_sha256") == sha256_file(pipeline_path)
        and auth.get("u5e_theory_sha256") == sha256_file(theory_path)
        and auth.get("parent_u5_final_record_sha256") == EXPECTED_U5_FINAL
        and auth.get("parent_u5d_final_record_sha256") == EXPECTED_U5D_FINAL
        and auth.get("new_blind_access_authorised") is False
        and auth.get("stage12_authorised") is False
    )
    if not release_ok:
        raise RuntimeError("U5E release integrity failed.")

    root = locate_project_root()
    cross_modal = root / "06_Data_Records" / "Cross_Modal"
    u5_dir = cross_modal / "StageU5B_Sentinel_Observability_Prospective_Reserve_v1.0"
    u5d_dir = cross_modal / "StageU5D_Confidence_Bounded_Observer_Hardening_v1.0"

    u5_record = json.loads(
        (u5_dir / "StageU5B_Complete_v1.0.json").read_text(encoding="utf-8")
    )
    u5d_record_path = u5d_dir / "StageU5D_Complete_v1.0.json"
    u5d_record = json.loads(u5d_record_path.read_text(encoding="utf-8"))
    raw_path = (
        u5d_dir
        / "StageU5D_Reconstructed_Target_Scores_And_Labels_v1.0.csv.gz"
    )
    raw_manifest_path = (
        u5d_dir / "StageU5D_Reconstructed_Target_Manifest_v1.0.csv"
    )
    transport_path = (
        u5_dir
        / "StageU5B_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    )

    parent_ok = bool(
        u5_record.get("final_record_sha256") == EXPECTED_U5_FINAL
        and u5d_record.get("final_record_sha256") == EXPECTED_U5D_FINAL
        and sha256_file(u5d_record_path) == EXPECTED_U5D_COMPLETE_FILE_SHA
        and sha256_file(raw_path) == EXPECTED_U5D_RAW_SHA
        and sha256_file(raw_manifest_path) == EXPECTED_U5D_RAW_MANIFEST_SHA
        and sha256_file(transport_path) == EXPECTED_U5_DESCRIPTOR_SHA
    )
    if not parent_ok:
        raise RuntimeError("U5E parent integrity failed.")

    output_dir = cross_modal / STAGE
    if output_dir.exists():
        completed = output_dir / "StageU5E_Complete_v1.0.json"
        if completed.exists():
            raise RuntimeError("Completed U5E exists; rerun is prohibited.")
        backup = output_dir.with_name(
            output_dir.name
            + "_PARTIAL_"
            + datetime.now().strftime("%Y%m%dT%H%M%S")
        )
        output_dir.rename(backup)
    output_dir.mkdir(parents=True, exist_ok=False)

    for source in [protocol_path, auth_path, theory_path, pipeline_path]:
        shutil.copy2(source, output_dir / source.name)

    print("[U5E] Loading exact U5D reconstructed target scores and labels.")
    raw = pd.read_csv(raw_path)
    transport = pd.read_csv(transport_path)

    raw_targets = set(zip(raw["family"], raw["target"]))
    transport_targets = set(zip(transport["family"], transport["target"]))
    exact_target_roster = raw_targets == transport_targets and len(raw_targets) == 16
    if not exact_target_roster:
        raise RuntimeError("U5E target roster mismatch.")

    print("[U5E] Running pair-complete opposite-block cross-fitting.")
    replicates = analyse_pair_complete(raw, transport)
    replicates.to_csv(
        output_dir / "StageU5E_Pair_Complete_Replicates_v1.0.csv.gz",
        index=False,
        compression="gzip",
    )

    states, summary, target_summary = summarize_results(replicates)
    states.to_csv(
        output_dir / "StageU5E_Pair_Complete_State_Results_v1.0.csv",
        index=False,
    )
    summary.to_csv(
        output_dir / "StageU5E_Method_Summary_v1.0.csv",
        index=False,
    )
    target_summary.to_csv(
        output_dir / "StageU5E_Target_Summary_v1.0.csv",
        index=False,
    )

    make_figures(output_dir, summary, states, target_summary)

    summary_index = summary.set_index("method")
    primary = summary_index.loc[PRIMARY_METHOD]
    strict = summary_index.loc["PC_PAIRED_HOEFFDING"]
    identity_max = float(replicates["identity_residual"].max())
    primary_positive_targets = int(
        (
            target_summary[
                target_summary["method"] == PRIMARY_METHOD
            ]["gain_vs_full_direct"]
            > 0
        ).sum()
    )

    gates = [
        (
            "release_and_parent_integrity",
            bool(release_ok and parent_ok),
            str(release_ok and parent_ok),
        ),
        (
            "exact_target_roster",
            bool(exact_target_roster),
            f"targets={len(raw_targets)}",
        ),
        (
            "pair_complete_zero_weight_identity",
            bool(identity_max < 1e-12),
            f"max_residual={identity_max:.3e}",
        ),
        (
            "strict_opposite_block_coverage",
            bool(
                strict["mean_simultaneous_coverage"] >= 0.90
                and strict["minimum_simultaneous_coverage"] >= 0.85
            ),
            (
                f"mean={strict['mean_simultaneous_coverage']:.6f};"
                f"minimum={strict['minimum_simultaneous_coverage']:.6f}"
            ),
        ),
        (
            "strict_block_no_harm_geometry",
            bool(strict["minimum_block_no_harm_rate"] >= 0.999),
            f"minimum={strict['minimum_block_no_harm_rate']:.6f}",
        ),
        (
            "primary_same_budget_pooled_utility",
            bool(
                primary["pooled_mae"]
                <= primary["pooled_direct_full_mae"]
            ),
            (
                f"primary={primary['pooled_mae']:.6f};"
                f"direct={primary['pooled_direct_full_mae']:.6f};"
                f"gain={primary['gain_vs_full_direct']:.6f}"
            ),
        ),
        (
            "primary_full_direct_tail_safety",
            bool(primary["worst_target_budget_regret"] <= 0.005),
            f"worst={primary['worst_target_budget_regret']:.6f}",
        ),
        (
            "certification_tax_materially_reduced",
            bool(
                primary["worst_target_budget_regret"]
                <= 0.5 * U5D_DELONG_WORST_REGRET
            ),
            (
                f"U5E={primary['worst_target_budget_regret']:.6f};"
                f"U5D={U5D_DELONG_WORST_REGRET:.6f}"
            ),
        ),
        (
            "primary_retains_selective_utility",
            bool(
                primary["mean_weight"] > 0
                and primary_positive_targets >= 9
            ),
            (
                f"mean_weight={primary['mean_weight']:.6f};"
                f"positive_targets={primary_positive_targets}/16;"
                f"fallback={primary['fallback_rate']:.6f}"
            ),
        ),
        ("new_blind_accessed", True, "False"),
        ("stage12_authorised", True, "False"),
    ]
    gate_table = pd.DataFrame(
        gates,
        columns=["gate", "passed", "observed"],
    )
    gate_table.to_csv(
        output_dir / "StageU5E_Gate_Table_v1.0.csv",
        index=False,
    )

    core = gate_table[
        ~gate_table["gate"].isin(
            ["new_blind_accessed", "stage12_authorised"]
        )
    ]
    if bool(core["passed"].all()):
        decision = (
            "SEAL_STAGEU5E_PAIR_COMPLETE_OBSERVER_SUPPORTED_"
            "AUTHORISE_FINAL_OBSERVER_FREEZE_AND_U6_PREREGISTRATION_ONLY_"
            "NO_NEW_BLIND_STAGE12_PROHIBITED"
        )
    else:
        decision = (
            "SEAL_STAGEU5E_PARTIAL_PAIR_COMPLETE_OBSERVER_SUPPORT_"
            "RETAIN_ALL_RESULTS_REFINE_BEFORE_U6_"
            "NO_NEW_BLIND_STAGE12_PROHIBITED"
        )

    report = f"""# Stage U5E — Pair-Complete Cross-Fitted Observer

Decision: `{decision}`

- Exact U5/U5D parent integrity: {parent_ok}
- Exact 16-target roster: {exact_target_roster}
- Maximum four-block/full-direct identity residual: {identity_max:.3e}
- Strict paired-Hoeffding simultaneous coverage: {strict['mean_simultaneous_coverage']:.6f}
- Strict blockwise no-harm geometry: {strict['minimum_block_no_harm_rate']:.6f}
- Primary method: {PRIMARY_METHOD}
- Primary pooled MAE / full-direct MAE: {primary['pooled_mae']:.6f} / {primary['pooled_direct_full_mae']:.6f}
- Primary relative gain: {primary['gain_vs_full_direct']:.6f}
- Primary worst target-budget regret: {primary['worst_target_budget_regret']:.6f}
- U5D DeLong worst target-budget regret: {U5D_DELONG_WORST_REGRET:.6f}
- Primary mean transport weight: {primary['mean_weight']:.6f}
- Primary fallback rate: {primary['fallback_rate']:.6f}
- Primary positive targets: {primary_positive_targets}/16

The four pair blocks retain every positive-negative comparison. At zero
transport weight their average is exactly the full direct AUC. Blockwise
confidence geometry is formal under opposite-block independence. The
variance-gated full-direct comparison remains an empirical transparent
development result and is not represented as a new prospective guarantee.
"""
    (output_dir / "StageU5E_Report_v1.0.md").write_text(
        report,
        encoding="utf-8",
    )

    pre_record = {
        "stage": STAGE,
        "status": "TRANSPARENT_PAIR_COMPLETE_OBSERVER_DEVELOPMENT",
        "created_utc": utc_now(),
        "decision": decision,
        "parent_u5_final_record_sha256": EXPECTED_U5_FINAL,
        "parent_u5d_final_record_sha256": EXPECTED_U5D_FINAL,
        "release_integrity_pass": release_ok,
        "parent_integrity_pass": parent_ok,
        "exact_target_roster": exact_target_roster,
        "maximum_pair_complete_identity_residual": identity_max,
        "primary_method": PRIMARY_METHOD,
        "primary_summary": primary.to_dict(),
        "strict_summary": strict.to_dict(),
        "positive_primary_targets": primary_positive_targets,
        "method_summary": summary.to_dict("records"),
        "new_blind_accessed": False,
        "parent_result_changed": False,
        "stage12_authorised": False,
        "runtime_seconds": time.time() - started,
        "python": sys.version,
        "platform": platform.platform(),
    }
    final_record_sha = sha256_text(canonical_json(pre_record))
    record = dict(pre_record)
    record["final_record_sha256"] = final_record_sha
    (output_dir / "StageU5E_Complete_v1.0.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest = durable_manifest(output_dir)
    manifest.to_csv(
        output_dir / "StageU5E_Durable_Manifest_v1.0.csv",
        index=False,
    )
    zip_path = output_dir / "StageU5E_Canonical_Records_v1.0.zip"
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(
                    path,
                    arcname=str(path.relative_to(output_dir)),
                )
    zip_sha = sha256_file(zip_path)
    (
        output_dir / "StageU5E_Canonical_Zip_Commit_v1.0.json"
    ).write_text(
        json.dumps(
            {
                "stage": STAGE,
                "final_record_sha256": final_record_sha,
                "canonical_zip_sha256": zip_sha,
                "committed_utc": utc_now(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("\n========== STAGE U5E COMPLETE ==========")
    print("Decision:", decision)
    print("Pair-complete identity max residual:", identity_max)
    print(
        "Strict coverage / block geometry:",
        strict["mean_simultaneous_coverage"],
        strict["minimum_block_no_harm_rate"],
    )
    print(
        "Primary MAE / direct / gain / worst regret:",
        primary["pooled_mae"],
        primary["pooled_direct_full_mae"],
        primary["gain_vs_full_direct"],
        primary["worst_target_budget_regret"],
    )
    print(
        "Primary weight / fallback / positive targets:",
        primary["mean_weight"],
        primary["fallback_rate"],
        primary_positive_targets,
    )
    print("New blind accessed:", False)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", final_record_sha)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gate_table.to_string(index=False))


if __name__ == "__main__":
    main()

