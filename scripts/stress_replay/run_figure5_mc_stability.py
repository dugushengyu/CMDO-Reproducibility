#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

METHODS = {
    "CMDO": "PC_PAIRED_HOEFFDING",
    "U-stat": "PC_USTAT_MCDIARMID",
    "DeLong": "PC_DELONG",
    "Plug-in": "PC_PLUGIN",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cmdo_stress_replay", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_state_summary(directory: Path) -> Path:
    required = {
        "true_auc", "budget", "lambda_nominal", "method",
        "mae", "direct_mae", "mean_excess_mae", "gain_percent",
    }
    matches = []
    for path in directory.rglob("*.csv"):
        try:
            cols = set(pd.read_csv(path, nrows=3).columns)
        except Exception:
            continue
        if required.issubset(cols):
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one state-summary CSV, found {matches}")
    return matches[0]


def method_rows(df: pd.DataFrame, display: str, method_id: str) -> pd.DataFrame:
    sub = df[df["method"].astype(str) == method_id]
    if len(sub):
        return sub.copy()
    if "method_label" in df.columns:
        sub = df[df["method_label"].astype(str) == display]
        if len(sub):
            return sub.copy()
    raise RuntimeError(f"Method not found: {display} / {method_id}")


def all_budget_boundary(df: pd.DataFrame, display: str, method_id: str) -> float:
    sub = method_rows(df, display, method_id)
    lambdas = sorted(float(x) for x in sub["lambda_nominal"].dropna().unique())
    boundary = math.nan
    for lam in lambdas:
        cell = sub[np.isclose(sub["lambda_nominal"].astype(float), lam, rtol=0, atol=1e-12)]
        if cell.empty:
            break
        # Complete non-inferiority requires every tested AUC, mismatch direction,
        # and audit budget at this Lambda to have mean MAE <= same-budget direct MAE.
        all_ni = bool((cell["mean_excess_mae"].astype(float) <= 1e-15).all())
        if all_ni:
            boundary = lam
        else:
            break
    return boundary


def cmdo_ustat_efficiency(df: pd.DataFrame) -> tuple[float, float]:
    keys = ["true_auc", "budget", "lambda_nominal", "bias_sign"]
    c = method_rows(df, "CMDO", METHODS["CMDO"])[keys + ["gain_percent"]].copy()
    u = method_rows(df, "U-stat", METHODS["U-stat"])[keys + ["gain_percent"]].copy()
    c = c.rename(columns={"gain_percent": "gain_cmdo"})
    u = u.rename(columns={"gain_percent": "gain_ustat"})
    p = c.merge(u, on=keys, how="inner")
    p = p[p["lambda_nominal"].astype(float) <= 1.0 + 1e-12]
    d = p["gain_cmdo"].astype(float) - p["gain_ustat"].astype(float)
    return float(d.mean()), float((d > 0).mean())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--blocks", type=int, default=5)
    args = parser.parse_args()

    here = Path(__file__).resolve()
    repo = Path(args.repo).resolve() if args.repo else here.parents[2]
    outroot = Path(args.outdir).resolve()
    replay_script = repo / "scripts" / "stress_replay" / "CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py"
    if not replay_script.exists():
        raise FileNotFoundError(replay_script)

    outroot.mkdir(parents=True, exist_ok=True)
    mod = load_module(replay_script)
    if int(mod.N_REPLICATES) != 200 or int(mod.N_CALIBRATION) != 500:
        raise RuntimeError("Unexpected reconstructed stress design")

    original_seed = mod.evaluation_seed
    rows = []

    for block in range(1, args.blocks + 1):
        offset = block * 10_000_000_000

        def block_seed(auc_index, budget_index, lambda_index, sign_code, replicate, _offset=offset):
            return original_seed(auc_index, budget_index, lambda_index, sign_code, replicate) + _offset

        mod.evaluation_seed = block_seed
        block_dir = outroot / f"block_{block:02d}"
        mod.run(block_dir, save_replicates=False)
        df = pd.read_csv(find_state_summary(block_dir))

        boundaries = {
            display: all_budget_boundary(df, display, method_id)
            for display, method_id in METHODS.items()
        }
        adv, win = cmdo_ustat_efficiency(df)
        rows.append({
            "block": block,
            "cmdo_lambda_star": boundaries["CMDO"],
            "ustat_lambda_star": boundaries["U-stat"],
            "delong_lambda_star": boundaries["DeLong"],
            "plugin_lambda_star": boundaries["Plug-in"],
            "cmdo_minus_ustat_gain_pp": adv,
            "cmdo_higher_fraction": win,
        })

    result = pd.DataFrame(rows)
    csv_path = outroot / "CMDO_Figure5_MC_Stability_5x200.csv"
    result.to_csv(csv_path, index=False)

    summary = {
        "blocks": int(len(result)),
        "cmdo_boundary_range": [float(result.cmdo_lambda_star.min()), float(result.cmdo_lambda_star.max())],
        "ustat_boundary_range": [float(result.ustat_lambda_star.min()), float(result.ustat_lambda_star.max())],
        "delong_boundary_range": [float(result.delong_lambda_star.min()), float(result.delong_lambda_star.max())],
        "plugin_boundary_range": [float(result.plugin_lambda_star.min()), float(result.plugin_lambda_star.max())],
        "cmdo_ustat_boundaries_identical_all_blocks": bool((result.cmdo_lambda_star == result.ustat_lambda_star).all()),
        "cmdo_minus_ustat_gain_pp_range": [float(result.cmdo_minus_ustat_gain_pp.min()), float(result.cmdo_minus_ustat_gain_pp.max())],
        "cmdo_higher_fraction_values": sorted(float(x) for x in result.cmdo_higher_fraction.unique()),
        "claim_boundary": "post-completion diagnostic only; does not replace frozen authoritative Figure 5",
    }
    json_path = outroot / "CMDO_Figure5_MC_Stability_SUMMARY.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(result.to_string(index=False))
    print(json.dumps(summary, indent=2))
    print(f"[PASS] {csv_path}")
    print(f"[PASS] {json_path}")


if __name__ == "__main__":
    main()
