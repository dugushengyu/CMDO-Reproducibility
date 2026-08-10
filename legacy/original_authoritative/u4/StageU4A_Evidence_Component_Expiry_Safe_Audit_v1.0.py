#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage U4A — Evidence-component universality, evidence expiry,
and reliability-gated safe sequential auditing.

STATUS
------
TRANSPARENT REVEALED-RESERVE DEVELOPMENT ONLY.

This pipeline must not reinterpret Stage U3C as successful, must not access a
new blind reserve, and must not authorise Stage 12. It uses the already revealed
Stage U3C reserve solely for falsification-guided theory and method development.

Core outputs
------------
1. Non-negative component-mixture fits:
       E(b) = c0 + c_half * (b / 8)^(-1/2) + c_one * (b / 8)^(-1)
2. Budget-dependent effective exponents.
3. Empirical and model-derived transport-evidence validity horizons.
4. Nested leave-one-target-out development of a reliability-gated,
   budget-adaptive, no-harm sequential AUC audit.
5. A draft U4B prospective protocol. The draft is not a final preregistration
   and does not authorise a new reserve.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import sys
import textwrap
import time
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from sklearn.linear_model import LinearRegression


STAGE = "StageU4A_Evidence_Component_Expiry_Safe_Audit_v1.0"
PROJECT_NAME = "Cross-Modal_Diagnostic_Observability"
EXPECTED_U3C_FINAL_RECORD_SHA256 = (
    "2b6e7efbd1e897bc5c6b0c589a79a6d6392a0ef7fcf4d38fc1222f936e29e9e6"
)
EXPECTED_U3C_CANONICAL_ZIP_SHA256 = (
    "9082c6fcf29f508e27c77af9020533d0e0dde40e7edea464b8c6f973180c4d17"
)
BUDGETS = np.asarray([8, 16, 32, 64, 128], dtype=float)
B0 = 8.0
RANDOM_SEED = 20260724
DESCRIPTOR_COLUMNS = [
    "feature_mean_shift",
    "variance_log_ratio",
    "score_shift",
    "entropy_shift",
    "confidence_shift",
]
TARGET_COLUMNS = ["dataset", "target"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def locate_project_root() -> Path:
    candidates = [
        Path("/content/drive/MyDrive") / PROJECT_NAME,
        Path.home() / "MyDrive" / PROJECT_NAME,
        Path("/mnt/data") / PROJECT_NAME,
        Path.cwd() / PROJECT_NAME,
        Path.cwd(),
    ]
    for candidate in candidates:
        if candidate.exists() and (
            (candidate / "06_Data_Records").exists()
            or list(candidate.rglob("StageU3C_Prospective_Trajectory_Predictions_v1.0.csv"))
        ):
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not locate the CMDO project root. In Colab, mount Google Drive "
        "and ensure MyDrive/Cross-Modal_Diagnostic_Observability exists."
    )


def unique_recursive(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {filename!r} below {root}, found {len(matches)}: {matches[:8]}"
        )
    return matches[0]


@dataclass(frozen=True)
class Inputs:
    trajectory: Path
    exponents: Path
    true_metrics: Path
    descriptors: Path
    replicates: Path
    leverage: Path
    u3c_complete: Path | None
    u3c_canonical_zip: Path | None


def locate_inputs(project_root: Path) -> Inputs:
    def find(name: str) -> Path:
        return unique_recursive(project_root, name)

    complete_matches = list(project_root.rglob("StageU3C_Complete_v1.0.json"))
    if not complete_matches:
        complete_matches = list(project_root.rglob("*StageU3C*Complete*.json"))
    zip_matches = list(project_root.rglob("StageU3C_Canonical_Records_v1.0.zip"))

    return Inputs(
        trajectory=find("StageU3C_Prospective_Trajectory_Predictions_v1.0.csv"),
        exponents=find("StageU3C_Target_Exponents_v1.0.csv"),
        true_metrics=find("StageU3C_Target_True_Metrics_v1.0.csv"),
        descriptors=find("StageU3C_Target_Shift_Descriptors_And_Transport_v1.0.csv"),
        replicates=find("StageU3C_AUC_Direct_Fusion_Replicates_v1.0.csv"),
        leverage=find("StageU3C_Label_Leverage_v1.0.csv"),
        u3c_complete=complete_matches[0] if len(complete_matches) == 1 else None,
        u3c_canonical_zip=zip_matches[0] if len(zip_matches) == 1 else None,
    )


def verify_parent_integrity(inputs: Inputs) -> Dict[str, object]:
    checks: Dict[str, object] = {
        "all_required_inputs_exist": all(
            getattr(inputs, name).exists()
            for name in [
                "trajectory",
                "exponents",
                "true_metrics",
                "descriptors",
                "replicates",
                "leverage",
            ]
        ),
        "expected_u3c_final_record_sha256": EXPECTED_U3C_FINAL_RECORD_SHA256,
        "expected_u3c_canonical_zip_sha256": EXPECTED_U3C_CANONICAL_ZIP_SHA256,
    }

    if inputs.u3c_complete is not None:
        complete = json.loads(inputs.u3c_complete.read_text(encoding="utf-8"))
        observed = (
            complete.get("final_record_sha256")
            or complete.get("final_record_sha")
            or complete.get("final_sha256")
        )
        checks["u3c_complete_path"] = str(inputs.u3c_complete)
        checks["u3c_final_record_observed"] = observed
        checks["u3c_final_record_matches"] = observed == EXPECTED_U3C_FINAL_RECORD_SHA256
    else:
        checks["u3c_complete_path"] = None
        checks["u3c_final_record_observed"] = None
        checks["u3c_final_record_matches"] = None

    if inputs.u3c_canonical_zip is not None:
        observed_zip = sha256_file(inputs.u3c_canonical_zip)
        checks["u3c_canonical_zip_path"] = str(inputs.u3c_canonical_zip)
        checks["u3c_canonical_zip_observed"] = observed_zip
        checks["u3c_canonical_zip_matches"] = observed_zip == EXPECTED_U3C_CANONICAL_ZIP_SHA256
    else:
        checks["u3c_canonical_zip_path"] = None
        checks["u3c_canonical_zip_observed"] = None
        checks["u3c_canonical_zip_matches"] = None

    checks["parent_integrity_pass"] = bool(
        checks["all_required_inputs_exist"]
        and checks["u3c_final_record_matches"] is not False
        and checks["u3c_canonical_zip_matches"] is not False
    )
    return checks


def load_inputs(inputs: Inputs) -> Dict[str, pd.DataFrame]:
    frames = {
        "trajectory": pd.read_csv(inputs.trajectory),
        "exponents": pd.read_csv(inputs.exponents),
        "true": pd.read_csv(inputs.true_metrics),
        "descriptors": pd.read_csv(inputs.descriptors),
        "replicates": pd.read_csv(inputs.replicates),
        "leverage": pd.read_csv(inputs.leverage),
    }
    required_columns = {
        "trajectory": {
            "dataset", "target", "metric", "evidence", "budget", "truth_mae",
            "predicted_alpha", "class_pred", "rootn_pred"
        },
        "true": {"dataset", "target", "auc"},
        "descriptors": {"dataset", "target", "transport_auc", *DESCRIPTOR_COLUMNS},
        "replicates": {
            "dataset", "target", "budget", "replicate", "auc_direct", "auc_fusion"
        },
        "leverage": {
            "dataset", "target", "budget", "direct_mae", "fusion_mae", "leverage"
        },
    }
    for key, columns in required_columns.items():
        missing = columns - set(frames[key].columns)
        if missing:
            raise ValueError(f"{key} is missing required columns: {sorted(missing)}")

    if frames["replicates"].groupby(TARGET_COLUMNS + ["budget"]).size().nunique() != 1:
        raise ValueError("Replicate counts are not constant across target-budget cells.")
    return frames


def reconstruct_budget8_trajectories(
    trajectory: pd.DataFrame,
    leverage: pd.DataFrame,
) -> pd.DataFrame:
    rows: List[dict] = []
    group_cols = ["dataset", "target", "metric", "evidence"]
    for keys, group in trajectory.groupby(group_cols, sort=True):
        group = group.sort_values("budget").copy()
        first = group.iloc[0]
        alpha = float(first["predicted_alpha"])
        budget = float(first["budget"])
        anchor = float(first["class_pred"]) * (budget / B0) ** alpha

        dataset, target, metric, evidence = keys
        if metric == "auc":
            match = leverage[
                (leverage["dataset"] == dataset)
                & (leverage["target"] == target)
                & (leverage["budget"] == 8)
            ]
            if len(match) == 1:
                anchor = float(
                    match["direct_mae"].iloc[0]
                    if evidence == "direct"
                    else match["fusion_mae"].iloc[0]
                )

        rows.append(
            {
                "dataset": dataset,
                "target": target,
                "metric": metric,
                "evidence": evidence,
                "budget": 8,
                "truth_mae": anchor,
                "predicted_alpha": alpha,
                "class_pred": anchor,
                "rootn_pred": anchor,
                "class_abs_error": 0.0,
                "rootn_abs_error": 0.0,
                "anchor_reconstructed": True,
            }
        )
        for record in group.to_dict("records"):
            record["anchor_reconstructed"] = False
            rows.append(record)
    result = pd.DataFrame(rows)
    return result.sort_values(group_cols + ["budget"]).reset_index(drop=True)


def component_design(budgets: np.ndarray) -> np.ndarray:
    x = np.asarray(budgets, dtype=float) / B0
    return np.column_stack([np.ones_like(x), x ** -0.5, x ** -1.0])


def fit_components(
    budgets: Sequence[float],
    errors: Sequence[float],
    ridge: float = 1e-8,
) -> Tuple[np.ndarray, np.ndarray]:
    x = component_design(np.asarray(budgets, dtype=float))
    y = np.asarray(errors, dtype=float)
    if ridge > 0:
        x_aug = np.vstack([x, math.sqrt(ridge) * np.eye(3)])
        y_aug = np.concatenate([y, np.zeros(3)])
    else:
        x_aug, y_aug = x, y
    coef, _ = nnls(x_aug, y_aug)
    return coef, x @ coef


def effective_alpha(coef: Sequence[float], budgets: Sequence[float]) -> np.ndarray:
    c0, ch, c1 = np.asarray(coef, dtype=float)
    x = np.asarray(budgets, dtype=float) / B0
    denom = c0 + ch * x ** -0.5 + c1 * x ** -1.0
    numer = 0.5 * ch * x ** -0.5 + c1 * x ** -1.0
    return np.divide(numer, denom, out=np.zeros_like(numer), where=denom > 0)


def fit_free_power(budgets: Sequence[float], errors: Sequence[float]) -> Tuple[float, float]:
    x = np.log(np.asarray(budgets, dtype=float) / B0)
    y = np.log(np.maximum(np.asarray(errors, dtype=float), 1e-12))
    model = LinearRegression().fit(x.reshape(-1, 1), y)
    alpha = float(-model.coef_[0])
    amplitude = float(math.exp(model.intercept_))
    return amplitude, alpha


def component_analysis(curves: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fit_rows: List[dict] = []
    alpha_rows: List[dict] = []
    pred_rows: List[dict] = []
    group_cols = ["dataset", "target", "metric", "evidence"]

    for keys, group in curves.groupby(group_cols, sort=True):
        group = group.sort_values("budget")
        budgets = group["budget"].to_numpy(dtype=float)
        truth = group["truth_mae"].to_numpy(dtype=float)
        coef, fitted = fit_components(budgets, truth)
        amp, free_alpha = fit_free_power(budgets, truth)
        free_pred = amp * (budgets / B0) ** (-free_alpha)
        rootn_pred = truth[0] * (budgets / B0) ** -0.5
        frozen_alpha = float(group["predicted_alpha"].iloc[0])
        frozen_pred = truth[0] * (budgets / B0) ** (-frozen_alpha)

        early_mask = budgets <= 32
        late_mask = budgets >= 64
        early_coef, _ = fit_components(budgets[early_mask], truth[early_mask], ridge=1e-5)
        early_pred = component_design(budgets) @ early_coef

        dataset, target, metric, evidence = keys
        fit_rows.append(
            {
                "dataset": dataset,
                "target": target,
                "metric": metric,
                "evidence": evidence,
                "c0_floor": coef[0],
                "c_half_regular": coef[1],
                "c_one_higher_order": coef[2],
                "p0_at_budget8": coef[0] / max(coef.sum(), 1e-12),
                "p_half_at_budget8": coef[1] / max(coef.sum(), 1e-12),
                "p_one_at_budget8": coef[2] / max(coef.sum(), 1e-12),
                "free_power_alpha": free_alpha,
                "descriptive_component_mae": float(np.mean(np.abs(fitted - truth))),
                "descriptive_free_power_mae": float(np.mean(np.abs(free_pred - truth))),
                "early_component_late_mae": float(np.mean(np.abs(early_pred[late_mask] - truth[late_mask]))),
                "frozen_class_late_mae": float(np.mean(np.abs(frozen_pred[late_mask] - truth[late_mask]))),
                "rootn_late_mae": float(np.mean(np.abs(rootn_pred[late_mask] - truth[late_mask]))),
            }
        )

        alphas = effective_alpha(coef, budgets)
        for budget, value in zip(budgets, alphas):
            alpha_rows.append(
                {
                    "dataset": dataset,
                    "target": target,
                    "metric": metric,
                    "evidence": evidence,
                    "budget": int(budget),
                    "effective_alpha": float(value),
                    "free_power_alpha": free_alpha,
                    "frozen_class_alpha": frozen_alpha,
                }
            )

        for idx, budget in enumerate(budgets):
            pred_rows.append(
                {
                    "dataset": dataset,
                    "target": target,
                    "metric": metric,
                    "evidence": evidence,
                    "budget": int(budget),
                    "truth_mae": truth[idx],
                    "component_full_pred": fitted[idx],
                    "component_early_pred": early_pred[idx],
                    "free_power_pred": free_pred[idx],
                    "frozen_class_pred": frozen_pred[idx],
                    "rootn_pred": rootn_pred[idx],
                    "is_late_prediction": bool(late_mask[idx]),
                }
            )

    return (
        pd.DataFrame(fit_rows),
        pd.DataFrame(alpha_rows),
        pd.DataFrame(pred_rows),
    )


def derive_expiry_map(
    leverage: pd.DataFrame,
    true_metrics: pd.DataFrame,
    descriptors: pd.DataFrame,
    curves: pd.DataFrame,
) -> pd.DataFrame:
    merged = (
        leverage.merge(true_metrics[TARGET_COLUMNS + ["auc"]], on=TARGET_COLUMNS)
        .merge(descriptors[TARGET_COLUMNS + ["transport_auc"]], on=TARGET_COLUMNS)
        .sort_values(TARGET_COLUMNS + ["budget"])
    )
    direct_auc_curves = curves[
        (curves["metric"] == "auc") & (curves["evidence"] == "direct")
    ].copy()

    rows: List[dict] = []
    for keys, group in merged.groupby(TARGET_COLUMNS, sort=True):
        group = group.sort_values("budget")
        benefit = group["direct_mae"].to_numpy() - group["fusion_mae"].to_numpy()
        budgets = group["budget"].to_numpy(dtype=int)
        positive = benefit > 0
        expiry_budget = None
        for i in range(1, len(budgets)):
            if positive[:i].any() and not positive[i]:
                expiry_budget = int(budgets[i])
                break
        if expiry_budget is None:
            expiry_budget = 256 if positive[-1] else int(budgets[0])

        dataset, target = keys
        auc_truth = float(group["auc"].iloc[0])
        transport = float(group["transport_auc"].iloc[0])
        transport_bias_abs = abs(transport - auc_truth)

        cgroup = direct_auc_curves[
            (direct_auc_curves["dataset"] == dataset)
            & (direct_auc_curves["target"] == target)
        ].sort_values("budget")
        amp, alpha = fit_free_power(cgroup["budget"], cgroup["truth_mae"])
        fixed_floor_proxy = 0.6 * transport_bias_abs
        if fixed_floor_proxy <= 1e-12 or alpha <= 1e-12:
            predicted_expiry = 256.0
        else:
            predicted_expiry = B0 * (amp / fixed_floor_proxy) ** (1.0 / alpha)
        predicted_expiry = float(np.clip(predicted_expiry, 8, 256))

        rows.append(
            {
                "dataset": dataset,
                "target": target,
                "transport_auc": transport,
                "true_auc": auc_truth,
                "transport_signed_bias": transport - auc_truth,
                "transport_absolute_bias": transport_bias_abs,
                "empirical_expiry_budget": expiry_budget,
                "model_predicted_expiry_budget": predicted_expiry,
                "positive_at_budget8": bool(positive[0]),
                "positive_budget_count": int(positive.sum()),
                "benefit_budget8": float(benefit[0]),
                "benefit_budget16": float(benefit[1]),
                "benefit_budget32": float(benefit[2]),
                "benefit_budget64": float(benefit[3]),
                "benefit_budget128": float(benefit[4]),
            }
        )
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class AdaptiveParams:
    bias_fraction: float
    residual_quantile: float
    max_transport_weight: float
    disagreement_scale: float
    support_scale: float
    no_harm_slack: float


def target_keys(frame: pd.DataFrame) -> List[Tuple[str, str]]:
    return [
        (str(dataset), str(target))
        for dataset, target in frame[TARGET_COLUMNS].drop_duplicates().itertuples(index=False, name=None)
    ]


def prepare_audit_data(
    replicates: pd.DataFrame,
    true_metrics: pd.DataFrame,
    descriptors: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    target_table = true_metrics[TARGET_COLUMNS + ["auc"]].merge(
        descriptors[TARGET_COLUMNS + ["transport_auc"] + DESCRIPTOR_COLUMNS],
        on=TARGET_COLUMNS,
        validate="one_to_one",
    )
    frame = replicates.merge(
        target_table[TARGET_COLUMNS + ["auc", "transport_auc"]],
        on=TARGET_COLUMNS,
        validate="many_to_one",
    )
    derived_transport = (
        frame["auc_fusion"] - 0.4 * frame["auc_direct"]
    ) / 0.6
    if not np.allclose(derived_transport, frame["transport_auc"], atol=1e-10):
        raise ValueError("Frozen fusion does not match 0.6 transport + 0.4 direct.")
    return frame, target_table


def calibration_summary(
    calibration_keys: Sequence[Tuple[str, str]],
    target_table: pd.DataFrame,
    residual_quantile: float,
) -> Dict[str, object]:
    index = target_table.set_index(TARGET_COLUMNS)
    cal = index.loc[list(calibration_keys)].reset_index()
    residual = (cal["transport_auc"] - cal["auc"]).to_numpy(dtype=float)
    bias = float(np.median(residual))
    centered = residual - bias
    scale = float(max(np.quantile(np.abs(centered), residual_quantile), 0.01))

    x = cal[DESCRIPTOR_COLUMNS].to_numpy(dtype=float)
    mean = x.mean(axis=0)
    std = x.std(axis=0, ddof=1)
    std = np.where(np.isfinite(std) & (std > 1e-8), std, 1.0)
    z = (x - mean) / std
    return {
        "bias": bias,
        "transport_scale": scale,
        "descriptor_mean": mean,
        "descriptor_std": std,
        "calibration_z": z,
    }


def evaluate_one_target(
    evaluation_key: Tuple[str, str],
    calibration_keys: Sequence[Tuple[str, str]],
    params: AdaptiveParams,
    audit_frame: pd.DataFrame,
    target_table: pd.DataFrame,
    keep_replicates: bool,
) -> pd.DataFrame:
    summary = calibration_summary(
        calibration_keys, target_table, params.residual_quantile
    )
    indexed = target_table.set_index(TARGET_COLUMNS)
    row = indexed.loc[evaluation_key]
    x = row[DESCRIPTOR_COLUMNS].to_numpy(dtype=float)
    z = (x - summary["descriptor_mean"]) / summary["descriptor_std"]
    d_min = float(
        np.min(
            np.sqrt(
                np.sum((summary["calibration_z"] - z.reshape(1, -1)) ** 2, axis=1)
            )
        )
    )
    support_gate = float(
        math.exp(-0.5 * (d_min / max(params.support_scale, 1e-8)) ** 2)
    )

    subset = audit_frame[
        (audit_frame["dataset"] == evaluation_key[0])
        & (audit_frame["target"] == evaluation_key[1])
    ]
    records: List[pd.DataFrame] = []
    for budget, group in subset.groupby("budget", sort=True):
        direct = group["auc_direct"].to_numpy(dtype=float)
        fixed = group["auc_fusion"].to_numpy(dtype=float)
        truth = float(group["auc"].iloc[0])
        transport = float(group["transport_auc"].iloc[0])
        direct_sd = float(np.std(direct, ddof=1))
        corrected_transport = float(
            np.clip(
                transport - params.bias_fraction * float(summary["bias"]),
                0.0,
                1.0,
            )
        )

        transport_risk_proxy = (
            float(summary["transport_scale"]) ** 2
            + ((1.0 - params.bias_fraction) * float(summary["bias"])) ** 2
        )
        base_weight = direct_sd**2 / (
            direct_sd**2 + transport_risk_proxy + 1e-12
        )
        disagreement_denom = (
            max(params.disagreement_scale, 1e-8)
            * math.sqrt(direct_sd**2 + transport_risk_proxy + 1e-12)
        )
        disagreement_gate = np.exp(
            -0.5 * ((direct - corrected_transport) / disagreement_denom) ** 2
        )
        weight = np.minimum(
            params.max_transport_weight,
            base_weight * support_gate * disagreement_gate,
        )

        direct_risk_proxy = direct_sd**2
        fusion_risk_upper = (
            (1.0 - weight) ** 2 * direct_risk_proxy
            + weight**2 * transport_risk_proxy
        )
        allow = fusion_risk_upper <= (
            (1.0 + params.no_harm_slack) * direct_risk_proxy + 1e-12
        )
        weight = np.where(allow, weight, 0.0)
        adaptive = (1.0 - weight) * direct + weight * corrected_transport

        base = pd.DataFrame(
            {
                "dataset": evaluation_key[0],
                "target": evaluation_key[1],
                "budget": int(budget),
                "truth_auc": truth,
                "direct_error": np.abs(direct - truth),
                "fixed_error": np.abs(fixed - truth),
                "adaptive_error": np.abs(adaptive - truth),
                "transport_weight": weight,
                "support_gate": support_gate,
                "direct_sd_surrogate": direct_sd,
                "transport_risk_proxy": transport_risk_proxy,
                "corrected_transport": corrected_transport,
            }
        )
        if keep_replicates:
            base["replicate"] = group["replicate"].to_numpy()
            base["auc_direct"] = direct
            base["auc_fixed_fusion"] = fixed
            base["auc_adaptive"] = adaptive
        records.append(base)
    return pd.concat(records, ignore_index=True)


def state_summary(replicate_results: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "direct_error",
        "fixed_error",
        "adaptive_error",
        "transport_weight",
        "support_gate",
        "direct_sd_surrogate",
        "transport_risk_proxy",
    ]
    return (
        replicate_results.groupby(TARGET_COLUMNS + ["budget"], as_index=False)[columns]
        .mean()
        .rename(
            columns={
                "direct_error": "direct_mae",
                "fixed_error": "fixed_fusion_mae",
                "adaptive_error": "adaptive_mae",
                "transport_weight": "mean_transport_weight",
            }
        )
    )


def candidate_score(results: pd.DataFrame) -> float:
    states = state_summary(results)
    regret = states["adaptive_mae"] - states["direct_mae"]
    mean_error = float(states["adaptive_mae"].mean())
    worst_regret = float(max(0.0, regret.max()))
    violation_rate = float(np.mean(regret > 0.005))
    late_weight_penalty = float(
        states.loc[states["budget"] >= 64, "mean_transport_weight"].mean()
    )
    return (
        mean_error
        + 2.0 * worst_regret
        + 0.02 * violation_rate
        + 0.005 * late_weight_penalty
    )


def parameter_grid() -> List[AdaptiveParams]:
    return [
        AdaptiveParams(*values)
        for values in product(
            [0.0, 0.5, 1.0],
            [0.8, 1.0],
            [0.25, 0.5],
            [1.0, 2.0],
            [2.0, 4.0],
            [0.0],
        )
    ]


def nested_loto_safe_audit(
    audit_frame: pd.DataFrame,
    target_table: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    keys = target_keys(target_table)
    grid = parameter_grid()
    outer_parts: List[pd.DataFrame] = []
    selected_rows: List[dict] = []

    for outer_key in keys:
        training_keys = [key for key in keys if key != outer_key]
        best_score = math.inf
        best_params: AdaptiveParams | None = None

        for params in grid:
            inner_parts: List[pd.DataFrame] = []
            for validation_key in training_keys:
                calibration_keys = [
                    key for key in training_keys if key != validation_key
                ]
                inner_parts.append(
                    evaluate_one_target(
                        validation_key,
                        calibration_keys,
                        params,
                        audit_frame,
                        target_table,
                        keep_replicates=False,
                    )
                )
            score = candidate_score(pd.concat(inner_parts, ignore_index=True))
            if score < best_score:
                best_score = score
                best_params = params

        assert best_params is not None
        selected_rows.append(
            {
                "held_dataset": outer_key[0],
                "held_target": outer_key[1],
                "inner_cv_score": best_score,
                **asdict(best_params),
            }
        )
        outer_parts.append(
            evaluate_one_target(
                outer_key,
                training_keys,
                best_params,
                audit_frame,
                target_table,
                keep_replicates=True,
            )
        )

    outer_replicates = pd.concat(outer_parts, ignore_index=True)
    states = state_summary(outer_replicates)
    states["adaptive_regret_vs_direct"] = (
        states["adaptive_mae"] - states["direct_mae"]
    )
    states["adaptive_gain_vs_fixed"] = (
        states["fixed_fusion_mae"] - states["adaptive_mae"]
    )
    states["adaptive_gain_vs_direct"] = (
        states["direct_mae"] - states["adaptive_mae"]
    )
    return outer_replicates, states, pd.DataFrame(selected_rows)


def equivalent_budget(
    direct_curve: pd.DataFrame,
    target_error: float,
) -> float:
    curve = direct_curve.sort_values("budget")
    budgets = curve["budget"].to_numpy(dtype=float)
    errors = curve["direct_mae"].to_numpy(dtype=float)
    if target_error >= errors[0]:
        return float(budgets[0] * max(0.25, errors[0] / max(target_error, 1e-12)))
    if target_error <= errors[-1]:
        amp, alpha = fit_free_power(budgets, errors)
        if alpha <= 1e-12:
            return float(budgets[-1])
        return float(np.clip(B0 * (amp / max(target_error, 1e-12)) ** (1 / alpha), 8, 2048))
    order = np.argsort(errors)[::-1]
    e = errors[order]
    b = budgets[order]
    return float(np.exp(np.interp(np.log(target_error), np.log(e[::-1]), np.log(b[::-1]))))


def add_adaptive_label_leverage(states: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []
    for keys, group in states.groupby(TARGET_COLUMNS, sort=True):
        direct_curve = group[["budget", "direct_mae"]].copy()
        for record in group.to_dict("records"):
            eq = equivalent_budget(direct_curve, float(record["adaptive_mae"]))
            record["adaptive_equivalent_direct_budget"] = eq
            record["adaptive_label_leverage"] = eq / float(record["budget"])
            rows.append(record)
    return pd.DataFrame(rows)


def aggregate_method_results(states: pd.DataFrame) -> Dict[str, float]:
    target_means = states.groupby(TARGET_COLUMNS)[
        ["direct_mae", "fixed_fusion_mae", "adaptive_mae"]
    ].mean()
    regret = states["adaptive_mae"] - states["direct_mae"]
    budget_weight = states.groupby("budget")["mean_transport_weight"].median()
    monotonic_weight = bool(np.all(np.diff(budget_weight.to_numpy()) <= 1e-10))
    low = states[states["budget"] == 8]

    return {
        "direct_overall_mae": float(states["direct_mae"].mean()),
        "fixed_fusion_overall_mae": float(states["fixed_fusion_mae"].mean()),
        "adaptive_overall_mae": float(states["adaptive_mae"].mean()),
        "adaptive_relative_gain_vs_direct": float(
            1.0 - states["adaptive_mae"].mean() / states["direct_mae"].mean()
        ),
        "adaptive_relative_gain_vs_fixed": float(
            1.0 - states["adaptive_mae"].mean() / states["fixed_fusion_mae"].mean()
        ),
        "worst_state_regret_vs_direct": float(regret.max()),
        "states_regret_gt_0p005": int(np.sum(regret > 0.005)),
        "targets_mean_adaptive_better_than_direct": int(
            np.sum(target_means["adaptive_mae"] < target_means["direct_mae"])
        ),
        "budget8_positive_targets": int(
            np.sum(low["adaptive_mae"] < low["direct_mae"])
        ),
        "median_budget8_label_leverage": float(
            low["adaptive_label_leverage"].median()
        ),
        "median_transport_weight_by_budget": {
            str(int(k)): float(v) for k, v in budget_weight.items()
        },
        "median_transport_weight_nonincreasing": monotonic_weight,
    }


def make_figures(
    output_dir: Path,
    curves: pd.DataFrame,
    component_fits: pd.DataFrame,
    alpha_map: pd.DataFrame,
    expiry: pd.DataFrame,
    states: pd.DataFrame,
) -> List[Path]:
    figures: List[Path] = []

    fig = plt.figure(figsize=(8, 6))
    for _, group in curves[
        (curves["metric"] == "auc") & (curves["evidence"] == "direct")
    ].groupby(TARGET_COLUMNS):
        plt.plot(group["budget"], group["truth_mae"], marker="o")
    plt.xscale("log", base=2)
    plt.yscale("log")
    plt.xlabel("Target-label budget")
    plt.ylabel("AUC witness MAE")
    plt.title("Direct AUC observability trajectories")
    plt.tight_layout()
    path = output_dir / "Figure_U4A_1_Direct_AUC_Trajectories.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    figures.append(path)

    fig = plt.figure(figsize=(8, 6))
    auc_alpha = alpha_map[
        (alpha_map["metric"] == "auc") & (alpha_map["evidence"] == "direct")
    ]
    for _, group in auc_alpha.groupby(TARGET_COLUMNS):
        plt.plot(group["budget"], group["effective_alpha"], marker="o")
    plt.xscale("log", base=2)
    plt.xlabel("Target-label budget")
    plt.ylabel("Effective exponent")
    plt.title("Effective exponents emerge from component mixtures")
    plt.tight_layout()
    path = output_dir / "Figure_U4A_2_Effective_Exponent_Continuum.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    figures.append(path)

    fig = plt.figure(figsize=(8, 6))
    fit_plot = component_fits[
        (component_fits["metric"] == "auc")
        & (component_fits["evidence"] == "direct")
    ].copy()
    x = np.arange(len(fit_plot))
    plt.bar(x - 0.25, fit_plot["p0_at_budget8"], width=0.25, label="floor")
    plt.bar(x, fit_plot["p_half_at_budget8"], width=0.25, label="regular")
    plt.bar(x + 0.25, fit_plot["p_one_at_budget8"], width=0.25, label="higher-order")
    plt.xticks(x, fit_plot["target"], rotation=30, ha="right")
    plt.ylabel("Budget-8 component fraction")
    plt.title("Target-specific mixtures of shared error components")
    plt.legend()
    plt.tight_layout()
    path = output_dir / "Figure_U4A_3_Component_Fractions.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    figures.append(path)

    fig = plt.figure(figsize=(8, 6))
    for _, row in expiry.iterrows():
        benefits = [
            row["benefit_budget8"],
            row["benefit_budget16"],
            row["benefit_budget32"],
            row["benefit_budget64"],
            row["benefit_budget128"],
        ]
        plt.plot(BUDGETS, benefits, marker="o", label=row["target"])
    plt.axhline(0.0)
    plt.xscale("log", base=2)
    plt.xlabel("Target-label budget")
    plt.ylabel("Direct MAE − fixed-fusion MAE")
    plt.title("Transport evidence has a finite validity horizon")
    plt.legend()
    plt.tight_layout()
    path = output_dir / "Figure_U4A_4_Evidence_Expiry.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    figures.append(path)

    fig = plt.figure(figsize=(8, 6))
    method_by_budget = states.groupby("budget")[
        ["direct_mae", "fixed_fusion_mae", "adaptive_mae"]
    ].median()
    for column in method_by_budget.columns:
        plt.plot(method_by_budget.index, method_by_budget[column], marker="o", label=column)
    plt.xscale("log", base=2)
    plt.yscale("log")
    plt.xlabel("Target-label budget")
    plt.ylabel("Median AUC estimation MAE")
    plt.title("Nested-LOTO safe sequential audit")
    plt.legend()
    plt.tight_layout()
    path = output_dir / "Figure_U4A_5_Method_Comparison.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    figures.append(path)

    fig = plt.figure(figsize=(8, 6))
    weight_by_budget = states.groupby("budget")["mean_transport_weight"].agg(
        ["median", "min", "max"]
    )
    plt.plot(weight_by_budget.index, weight_by_budget["median"], marker="o")
    plt.fill_between(
        weight_by_budget.index,
        weight_by_budget["min"],
        weight_by_budget["max"],
        alpha=0.2,
    )
    plt.xscale("log", base=2)
    plt.xlabel("Target-label budget")
    plt.ylabel("Transport weight")
    plt.title("Transport evidence automatically exits as direct evidence accumulates")
    plt.tight_layout()
    path = output_dir / "Figure_U4A_6_Adaptive_Transport_Weight.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    figures.append(path)

    return figures


def write_manuscript_insert(
    output_dir: Path,
    component_summary: Mapping[str, object],
    method_summary: Mapping[str, object],
    gates: pd.DataFrame,
) -> Path:
    text = f"""# Stage U4A transparent development result

## Claim boundary

Stage U3C remains a preregistered partial/failed prospective reserve. Stage U4A
does not reinterpret that result. It uses the revealed reserve as transparent
development evidence to replace hard exponent classes with an evidence-component
model and to construct a reliability-gated sequential audit.

## Revised theoretical result

Finite-budget performance observability is represented as

E(b) = c0 + c1/2 (b / b0)^(-1/2) + c1 (b / b0)^(-1),

with non-negative coefficients. The effective exponent is therefore an emergent,
budget-dependent quantity rather than a universal constant attached only to a
metric name.

Early-budget component prediction gain versus the frozen hard-class law:
{component_summary['component_gain_vs_frozen_class']:.6f}.

Early-budget component prediction gain versus root-n:
{component_summary['component_gain_vs_rootn']:.6f}.

## Evidence-expiry result

A transport estimate may reduce uncertainty at very small target-label budgets,
yet any persistent transport bias creates a non-vanishing floor. Consequently,
the optimal transport weight decreases as direct evidence accumulates, and a
target-specific validity horizon separates helpful from harmful transport use.

## Safe sequential auditing result

Nested leave-one-target-out development produced the following transparent
development performance:

- Direct-only overall MAE: {method_summary['direct_overall_mae']:.6f}
- Frozen fixed-fusion overall MAE: {method_summary['fixed_fusion_overall_mae']:.6f}
- Adaptive audit overall MAE: {method_summary['adaptive_overall_mae']:.6f}
- Relative gain versus direct-only: {method_summary['adaptive_relative_gain_vs_direct']:.6f}
- Relative gain versus fixed fusion: {method_summary['adaptive_relative_gain_vs_fixed']:.6f}
- Worst target-budget regret versus direct-only: {method_summary['worst_state_regret_vs_direct']:.6f}
- Budget-8 targets improved: {method_summary['budget8_positive_targets']}/6
- Median budget-8 label leverage: {method_summary['median_budget8_label_leverage']:.6f}

## Status

This is outcome-revealed method development, not confirmatory evidence. A new,
untouched reserve is required to test component-mixture prediction, evidence
validity-horizon prediction, and the no-harm sequential audit. No new blind
reserve and no Stage 12 execution are authorised by Stage U4A.

## Gates

{gates.to_markdown(index=False)}
"""
    path = output_dir / "StageU4A_Manuscript_Insert_v1.0.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_u4b_draft(
    output_dir: Path,
    method_summary: Mapping[str, object],
) -> Path:
    text = f"""# Stage U4B prospective reserve preregistration — DRAFT ONLY

## Status

DRAFT ONLY. NOT SEALED. NOT AUTHORISED FOR EXECUTION.

This draft is produced automatically from Stage U4A transparent development.
It must be reviewed, completed, hashed and separately authorised before any new
reserve outcome is accessed.

## Central prospective claim

The transferable object is a low-dimensional set of evidence-limited error
components, not a fixed metric-specific exponent. Transport evidence has a
target-specific validity horizon, and a reliability-gated budget-adaptive audit
can exploit transport at low budget while withdrawing it before it becomes
harmful.

## Required independent reserve

At least three new task families and at least twelve untouched target
environments, with no reuse of U3C targets. The reserve should include:

1. a medical or biological imaging family not used in U0–U3;
2. a non-medical vision family not used in U3C;
3. a language, tabular, time-series or structured-prediction family not used in U3C.

## Frozen evidence budgets

At minimum: 8, 16, 32, 64, 128. Additional larger budgets may be included only
if frozen before access.

## Primary prospective tests

P1. Component-mixture late-budget prediction from budgets 8–32 improves over
the frozen hard-class exponent and root-n benchmarks.

P2. Predicted evidence-validity horizon is within one adjacent budget level for
at least two thirds of target environments.

P3. The reliability-gated adaptive audit has non-inferior pooled MAE relative
to direct-only, with a preregistered no-harm margin.

P4. The adaptive audit improves low-budget estimation in a majority of targets.

P5. Median transport weight is non-increasing with target-label budget.

P6. Neither family nor target may be removed or substituted after outcome access.

## Candidate gates requiring final review

- pooled adaptive MAE no worse than direct-only by more than 2%;
- worst family-level regret no greater than a frozen tolerance;
- positive low-budget leverage in at least 8 of 12 targets;
- median budget-8 label leverage at least 1.25;
- predicted expiry within one budget level in at least 8 of 12 targets;
- no post-outcome retuning of component basis, calibration rule, weight rule,
  support gate, direct uncertainty estimator, or stopping rule.

## U4A development reference

Observed U4A adaptive relative gain versus direct-only:
{method_summary['adaptive_relative_gain_vs_direct']:.6f}.

This number is development evidence only and must not be used as a prospective
reserve outcome.

## Authorisation state

U4B final preregistration authorised: FALSE.
U4C reserve execution authorised: FALSE.
New blind accessed: FALSE.
Stage 12 authorised: FALSE.
"""
    path = output_dir / "StageU4B_Prospective_Reserve_Preregistration_DRAFT_v0.1.md"
    path.write_text(text, encoding="utf-8")
    return path


def build_manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "StageU4A_Durable_Manifest_v1.0.csv",
            "StageU4A_Canonical_Records_v1.0.zip",
        }:
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
    np.random.seed(RANDOM_SEED)

    project_root = locate_project_root()
    inputs = locate_inputs(project_root)
    integrity = verify_parent_integrity(inputs)
    if not integrity["parent_integrity_pass"]:
        raise RuntimeError(f"Parent integrity failed: {integrity}")

    data = load_inputs(inputs)
    curves = reconstruct_budget8_trajectories(
        data["trajectory"], data["leverage"]
    )

    output_dir = (
        project_root
        / "06_Data_Records"
        / "Cross_Modal"
        / STAGE
    )
    if output_dir.exists():
        backup = output_dir.with_name(
            output_dir.name + "_PREVIOUS_" + datetime.now().strftime("%Y%m%dT%H%M%S")
        )
        shutil.move(str(output_dir), str(backup))
    output_dir.mkdir(parents=True, exist_ok=False)

    component_fits, alpha_map, component_predictions = component_analysis(curves)
    component_fits.to_csv(
        output_dir / "StageU4A_Component_Fits_v1.0.csv", index=False
    )
    alpha_map.to_csv(
        output_dir / "StageU4A_Effective_Exponent_Map_v1.0.csv", index=False
    )
    component_predictions.to_csv(
        output_dir / "StageU4A_Component_Trajectory_Predictions_v1.0.csv",
        index=False,
    )

    late = component_fits.copy()
    component_late_mae = float(late["early_component_late_mae"].mean())
    frozen_late_mae = float(late["frozen_class_late_mae"].mean())
    rootn_late_mae = float(late["rootn_late_mae"].mean())
    component_summary = {
        "component_late_mae": component_late_mae,
        "frozen_class_late_mae": frozen_late_mae,
        "rootn_late_mae": rootn_late_mae,
        "component_gain_vs_frozen_class": (
            1.0 - component_late_mae / frozen_late_mae
            if frozen_late_mae > 0 else float("nan")
        ),
        "component_gain_vs_rootn": (
            1.0 - component_late_mae / rootn_late_mae
            if rootn_late_mae > 0 else float("nan")
        ),
        "effective_alpha_min": float(alpha_map["effective_alpha"].min()),
        "effective_alpha_max": float(alpha_map["effective_alpha"].max()),
    }

    expiry = derive_expiry_map(
        data["leverage"], data["true"], data["descriptors"], curves
    )
    expiry.to_csv(output_dir / "StageU4A_Evidence_Expiry_Map_v1.0.csv", index=False)

    audit_frame, target_table = prepare_audit_data(
        data["replicates"], data["true"], data["descriptors"]
    )
    outer_replicates, states, selected_params = nested_loto_safe_audit(
        audit_frame, target_table
    )
    states = add_adaptive_label_leverage(states)
    outer_replicates.to_csv(
        output_dir / "StageU4A_Adaptive_Audit_Replicates_v1.0.csv", index=False
    )
    states.to_csv(
        output_dir / "StageU4A_Adaptive_Audit_State_Results_v1.0.csv", index=False
    )
    selected_params.to_csv(
        output_dir / "StageU4A_Nested_LOTO_Selected_Parameters_v1.0.csv",
        index=False,
    )
    method_summary = aggregate_method_results(states)

    gates = pd.DataFrame(
        [
            {
                "gate": "parent_u3c_integrity",
                "passed": bool(integrity["parent_integrity_pass"]),
                "observed": EXPECTED_U3C_FINAL_RECORD_SHA256,
            },
            {
                "gate": "component_prediction_beats_frozen_class",
                "passed": component_summary["component_gain_vs_frozen_class"] > 0,
                "observed": component_summary["component_gain_vs_frozen_class"],
            },
            {
                "gate": "component_prediction_beats_rootn",
                "passed": component_summary["component_gain_vs_rootn"] > 0,
                "observed": component_summary["component_gain_vs_rootn"],
            },
            {
                "gate": "effective_exponent_is_nonconstant",
                "passed": (
                    component_summary["effective_alpha_max"]
                    - component_summary["effective_alpha_min"]
                ) > 0.10,
                "observed": (
                    f"{component_summary['effective_alpha_min']:.6f}–"
                    f"{component_summary['effective_alpha_max']:.6f}"
                ),
            },
            {
                "gate": "transport_expiry_observed",
                "passed": int(np.sum(expiry["empirical_expiry_budget"] <= 128)) >= 4,
                "observed": int(np.sum(expiry["empirical_expiry_budget"] <= 128)),
            },
            {
                "gate": "adaptive_overall_noninferior_to_direct",
                "passed": (
                    method_summary["adaptive_overall_mae"]
                    <= 1.02 * method_summary["direct_overall_mae"]
                ),
                "observed": method_summary["adaptive_relative_gain_vs_direct"],
            },
            {
                "gate": "adaptive_improves_over_fixed_fusion",
                "passed": (
                    method_summary["adaptive_overall_mae"]
                    < method_summary["fixed_fusion_overall_mae"]
                ),
                "observed": method_summary["adaptive_relative_gain_vs_fixed"],
            },
            {
                "gate": "adaptive_low_budget_positive_targets",
                "passed": method_summary["budget8_positive_targets"] >= 4,
                "observed": method_summary["budget8_positive_targets"],
            },
            {
                "gate": "adaptive_weight_exits_monotonically",
                "passed": method_summary["median_transport_weight_nonincreasing"],
                "observed": json.dumps(
                    method_summary["median_transport_weight_by_budget"]
                ),
            },
            {
                "gate": "new_blind_accessed",
                "passed": True,
                "observed": False,
            },
            {
                "gate": "stage12_authorised",
                "passed": True,
                "observed": False,
            },
        ]
    )
    gates.to_csv(output_dir / "StageU4A_Gate_Table_v1.0.csv", index=False)

    figures = make_figures(
        output_dir, curves, component_fits, alpha_map, expiry, states
    )
    manuscript = write_manuscript_insert(
        output_dir, component_summary, method_summary, gates
    )
    u4b_draft = write_u4b_draft(output_dir, method_summary)

    scientific_pass = bool(
        gates.loc[
            gates["gate"].isin(
                [
                    "component_prediction_beats_frozen_class",
                    "component_prediction_beats_rootn",
                    "effective_exponent_is_nonconstant",
                    "transport_expiry_observed",
                    "adaptive_overall_noninferior_to_direct",
                    "adaptive_improves_over_fixed_fusion",
                    "adaptive_low_budget_positive_targets",
                    "adaptive_weight_exits_monotonically",
                ]
            ),
            "passed",
        ].all()
    )
    decision = (
        "SEAL_STAGEU4A_COMPONENT_UNIVERSALITY_AND_SAFE_SEQUENTIAL_AUDIT_"
        "DEVELOPMENT_SUPPORTED_AUTHORISE_U4B_FINAL_PREREGISTRATION_ONLY"
        if scientific_pass
        else
        "SEAL_STAGEU4A_PARTIAL_DEVELOPMENT_SUPPORT_RETAIN_RESULTS_"
        "CONTINUE_TRANSPARENT_METHOD_REFINEMENT_U4B_NOT_YET_AUTHORISED"
    )

    pre_record = {
        "stage": STAGE,
        "status": "TRANSPARENT_REVEALED_RESERVE_DEVELOPMENT_ONLY",
        "created_utc": utc_now(),
        "decision": decision,
        "parent_u3c_final_record_sha256": EXPECTED_U3C_FINAL_RECORD_SHA256,
        "parent_u3c_canonical_zip_sha256": EXPECTED_U3C_CANONICAL_ZIP_SHA256,
        "parent_integrity": integrity,
        "component_summary": component_summary,
        "method_summary": method_summary,
        "scientific_development_supported": scientific_pass,
        "u4b_final_preregistration_authorised": scientific_pass,
        "u4c_new_reserve_execution_authorised": False,
        "new_blind_accessed": False,
        "stage12_authorised": False,
        "runtime_seconds": time.time() - started,
        "python": sys.version,
        "platform": platform.platform(),
    }
    pre_hash = sha256_text(canonical_json(pre_record))
    final_record = dict(pre_record)
    final_record["final_record_sha256"] = pre_hash
    complete_path = output_dir / "StageU4A_Complete_v1.0.json"
    complete_path.write_text(
        json.dumps(final_record, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest = build_manifest(output_dir)
    manifest_path = output_dir / "StageU4A_Durable_Manifest_v1.0.csv"
    manifest.to_csv(manifest_path, index=False)

    zip_path = output_dir / "StageU4A_Canonical_Records_v1.0.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(path, arcname=str(path.relative_to(output_dir)))

    zip_sha = sha256_file(zip_path)
    commit = {
        "stage": STAGE,
        "final_record_sha256": pre_hash,
        "canonical_zip_sha256": zip_sha,
        "committed_utc": utc_now(),
    }
    (output_dir / "StageU4A_Canonical_Zip_Commit_v1.0.json").write_text(
        json.dumps(commit, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("\n========== STAGE U4A COMPLETE ==========")
    print("Decision:", decision)
    print("Scientific development supported:", scientific_pass)
    print("Component late-budget MAE:", component_late_mae)
    print("Frozen hard-class late-budget MAE:", frozen_late_mae)
    print("Root-n late-budget MAE:", rootn_late_mae)
    print("Adaptive overall MAE:", method_summary["adaptive_overall_mae"])
    print("Direct overall MAE:", method_summary["direct_overall_mae"])
    print("Fixed-fusion overall MAE:", method_summary["fixed_fusion_overall_mae"])
    print("Worst adaptive regret:", method_summary["worst_state_regret_vs_direct"])
    print("Budget-8 positive targets:", method_summary["budget8_positive_targets"])
    print("U4B final preregistration authorised:", scientific_pass)
    print("U4C new reserve execution authorised:", False)
    print("New blind accessed:", False)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", pre_hash)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gates.to_string(index=False))


if __name__ == "__main__":
    main()

