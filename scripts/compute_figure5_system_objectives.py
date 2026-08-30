#!/usr/bin/env python3
"""
CMDO Figure 5 system-objective audit
====================================

Purpose
-------
Build a compact, frozen-data benchmark for the system-level quantities that
CMDO was actually designed to optimize:

1) certified utility among the U5F frozen candidates;
2) generalization breadth of the frozen observer across development, U6 and U7;
3) composition cost C under shared, permuted and role-separated controls;
4) HAC composability margin H - (A + C).

This script DOES NOT change any prospective verdict and DOES NOT create a new
scientific experiment. It only recomputes descriptive quantities from frozen
canonical records and the already frozen U10 post-completion decomposition.

The role-separated quantity is explicitly retained as a post-completion
prediction/control, not prospective confirmation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd


EXPECTED_SELECTED = "PC_PAIRED_HOEFFDING"
STRICT_CANDIDATES = {"PC_PAIRED_HOEFFDING", "PC_USTAT_MCDIARMID"}

TH_IDENTITY = 1e-12
TH_MEAN_COV = 0.99
TH_MIN_COV = 0.98
TH_NO_HARM = 0.999
TH_REGRET = 0.005
TH_POS_TARGETS = 9

ARCHIVES = {
    "StageU5F_Canonical_Records_v1.0.zip": "StageU5F_Candidate_Selection_Audit_v1.0.csv",
    "StageU6_Canonical_Records_v1.0.zip": "StageU6_Target_Summary_v1.0.csv",
    "StageU7_Canonical_Records_v1.0.zip": "StageU7_Target_Metric_Summary_v1.0.csv",
}


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve_canonical_dir(repo: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        require(p.is_dir(), f"Canonical record directory does not exist: {p}")
        return p

    env = os.environ.get("CMDO_CANONICAL_RECORD_DIR", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        require(p.is_dir(), f"CMDO_CANONICAL_RECORD_DIR does not exist: {p}")
        return p

    local_cfg = repo / "config" / "local_paths.json"
    if local_cfg.is_file():
        cfg = json.loads(local_cfg.read_text(encoding="utf-8"))
        val = str(cfg.get("canonicalRecordDir", "")).strip()
        if val:
            p = Path(val).expanduser().resolve()
            if p.is_dir():
                return p

    default = repo / "data" / "canonical_records"
    if default.is_dir():
        return default.resolve()

    # Final fallback: locate all three required archives under the repository.
    candidates = []
    for p in repo.rglob("StageU5F_Canonical_Records_v1.0.zip"):
        if p.is_file():
            candidates.append(p.parent.resolve())
    candidates = sorted(set(candidates))
    for p in candidates:
        if all((p / name).is_file() for name in ARCHIVES):
            return p

    raise RuntimeError(
        "Could not resolve canonicalRecordDir. Set CMDO_CANONICAL_RECORD_DIR "
        "or config/local_paths.json, or pass --canonical-dir."
    )


def read_manifest(repo: Path) -> dict[str, str]:
    p = repo / "provenance" / "canonical_archives_manifest.csv"
    require(p.is_file(), f"Missing canonical archive manifest: {p}")
    df = pd.read_csv(p)
    require({"archive", "sha256"}.issubset(df.columns), "Malformed canonical archive manifest.")
    return {str(r.archive): str(r.sha256).lower() for r in df.itertuples(index=False)}


def read_csv_from_zip(zip_path: Path, basename: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as zf:
        matches = [n for n in zf.namelist() if Path(n).name == basename]
        require(len(matches) == 1, f"Expected exactly one {basename} in {zip_path.name}; found {len(matches)}")
        with zf.open(matches[0], "r") as f:
            return pd.read_csv(f)


def to_bool(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y", "pass", "passed"}


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def candidate_reasons(row: pd.Series) -> list[str]:
    reasons: list[str] = []
    method = str(row["method"])
    if method not in STRICT_CANDIDATES:
        reasons.append("not_strict_candidate")
    if not finite(row["maximum_identity_residual"]) or float(row["maximum_identity_residual"]) >= TH_IDENTITY:
        reasons.append("identity")
    if not finite(row["mean_simultaneous_coverage"]) or float(row["mean_simultaneous_coverage"]) < TH_MEAN_COV:
        reasons.append("mean_coverage")
    if not finite(row["minimum_simultaneous_coverage"]) or float(row["minimum_simultaneous_coverage"]) < TH_MIN_COV:
        reasons.append("minimum_coverage")
    if not finite(row["minimum_block_no_harm_rate"]) or float(row["minimum_block_no_harm_rate"]) < TH_NO_HARM:
        reasons.append("no_harm_geometry")
    if not finite(row["pooled_gain"]) or float(row["pooled_gain"]) <= 0:
        reasons.append("nonpositive_gain")
    if not finite(row["worst_target_budget_regret"]) or float(row["worst_target_budget_regret"]) > TH_REGRET:
        reasons.append("worst_regret")
    if not finite(row["positive_targets"]) or int(row["positive_targets"]) < TH_POS_TARGETS:
        reasons.append("breadth")
    if not finite(row["mean_weight"]) or float(row["mean_weight"]) <= 0:
        reasons.append("inactive_borrowing")
    return reasons


def recompute_hac(u10: pd.DataFrame) -> dict[str, float]:
    req = {
        "B",
        "direct_mse",
        "shared_constant_mean_weight",
        "shared_adaptive_mse",
        "shared_constant_mean_mse",
        "shared_permuted_weight_mse",
        "shared_tax_weight_heterogeneity",
    }
    require(req.issubset(u10.columns), f"U10 dependence table missing: {sorted(req - set(u10.columns))}")
    B = u10["B"].to_numpy(float)
    V = u10["direct_mse"].to_numpy(float)
    meanW = u10["shared_constant_mean_weight"].to_numpy(float)
    require(np.all(np.isfinite(V) & (V > 0)), "U10 direct_mse must be finite and positive.")

    lam = (B ** 2) / V
    wstar = 1.0 / (1.0 + lam)
    wglobal = 1.0 / (1.0 + float(np.mean(lam)))

    Hrows = (1.0 + lam) * (wstar - wglobal) ** 2
    Arows = (1.0 + lam) * (meanW - wstar) ** 2

    Cshared_rows = (
        u10["shared_adaptive_mse"].to_numpy(float)
        - u10["shared_constant_mean_mse"].to_numpy(float)
    ) / V
    Cperm_rows = (
        u10["shared_permuted_weight_mse"].to_numpy(float)
        - u10["shared_constant_mean_mse"].to_numpy(float)
    ) / V
    Crole_rows = u10["shared_tax_weight_heterogeneity"].to_numpy(float) / V

    H = float(np.mean(Hrows))
    A = float(np.mean(Arows))
    Cshared = float(np.mean(Cshared_rows))
    Cperm = float(np.mean(Cperm_rows))
    Crole = float(np.mean(Crole_rows))

    return {
        "H": H,
        "A": A,
        "C_shared": Cshared,
        "C_permuted": Cperm,
        "C_role_separated_prediction": Crole,
        "margin_shared": H - (A + Cshared),
        "margin_permuted": H - (A + Cperm),
        "margin_role_separated_prediction": H - (A + Crole),
        "C_reduction_permuted_pct": 100.0 * (Cshared - Cperm) / Cshared,
        "C_reduction_role_separated_prediction_pct": 100.0 * (Cshared - Crole) / Cshared,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--canonical-dir", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    require(repo.is_dir(), f"Repository does not exist: {repo}")
    canonical = resolve_canonical_dir(repo, args.canonical_dir)
    manifest = read_manifest(repo)

    print("=" * 92)
    print(" CMDO FIGURE 5 SYSTEM-OBJECTIVE AUDIT")
    print(" certified utility -> breadth -> composition cost -> HAC margin")
    print("=" * 92)
    print(f"Repository      : {repo}")
    print(f"Canonical records: {canonical}")

    # ------------------------------------------------------------------
    # Verify and load U5F/U6/U7 canonical archives.
    # ------------------------------------------------------------------
    loaded: dict[str, pd.DataFrame] = {}
    print("\n[1] Canonical archive integrity")
    for archive, csv_name in ARCHIVES.items():
        zp = canonical / archive
        require(zp.is_file(), f"Missing canonical archive: {zp}")
        require(archive in manifest, f"Archive absent from provenance manifest: {archive}")
        actual = sha256_file(zp).lower()
        expected = manifest[archive]
        require(actual == expected, f"SHA256 mismatch for {archive}: {actual} != {expected}")
        print(f"  [OK] {archive} {actual}")
        loaded[archive] = read_csv_from_zip(zp, csv_name)

    u5f = loaded["StageU5F_Canonical_Records_v1.0.zip"].copy()
    u6t = loaded["StageU6_Canonical_Records_v1.0.zip"].copy()
    u7t = loaded["StageU7_Canonical_Records_v1.0.zip"].copy()

    # U6 pooled gain requires state results from same archive.
    u6_state = read_csv_from_zip(canonical / "StageU6_Canonical_Records_v1.0.zip", "StageU6_Audit_State_Results_v1.0.csv")
    # U7 pooled AUC gain is frozen in the metric summary.
    u7_metric = read_csv_from_zip(canonical / "StageU7_Canonical_Records_v1.0.zip", "StageU7_Metric_Summary_v1.0.csv")

    # ------------------------------------------------------------------
    # Certified utility: exactly reconstruct U5F eligibility.
    # ------------------------------------------------------------------
    required_u5f = {
        "method",
        "pooled_gain",
        "worst_target_budget_regret",
        "mean_weight",
        "mean_simultaneous_coverage",
        "minimum_simultaneous_coverage",
        "minimum_block_no_harm_rate",
        "maximum_identity_residual",
        "positive_targets",
        "target_count",
    }
    require(required_u5f.issubset(u5f.columns), f"U5F audit missing: {sorted(required_u5f - set(u5f.columns))}")

    rows = []
    for _, r in u5f.iterrows():
        reasons = candidate_reasons(r)
        eligible = len(reasons) == 0
        raw_gain_pct = 100.0 * float(r["pooled_gain"])
        rows.append(
            {
                "method": str(r["method"]),
                "raw_pooled_gain_pct": raw_gain_pct,
                "eligible": eligible,
                "certified_utility_pct": raw_gain_pct if eligible else np.nan,
                "positive_targets": int(r["positive_targets"]),
                "target_count": int(r["target_count"]),
                "worst_target_budget_regret": float(r["worst_target_budget_regret"]),
                "inadmissibility_reason": "PASS" if eligible else ";".join(reasons),
            }
        )
    cand = pd.DataFrame(rows)
    eligible = cand[cand["eligible"]].sort_values(
        ["certified_utility_pct", "worst_target_budget_regret", "positive_targets", "method"],
        ascending=[False, True, False, True],
    )
    require(len(eligible) > 0, "No U5F candidate is eligible under the frozen rule.")
    selected = str(eligible.iloc[0]["method"])
    require(selected == EXPECTED_SELECTED, f"Frozen certified-utility winner changed: {selected}")
    cmdo = cand[cand["method"] == EXPECTED_SELECTED]
    require(len(cmdo) == 1 and bool(cmdo.iloc[0]["eligible"]), "CMDO row is not uniquely eligible.")

    print("\n[2] Certified utility")
    print(cand[["method", "raw_pooled_gain_pct", "eligible", "certified_utility_pct", "inadmissibility_reason"]].to_string(index=False))
    print(f"  winner among frozen eligible candidates = {selected}")

    # ------------------------------------------------------------------
    # Generalization breadth.
    # ------------------------------------------------------------------
    cmdo_row = cmdo.iloc[0]
    dev_pos = int(cmdo_row["positive_targets"])
    dev_n = int(cmdo_row["target_count"])
    dev_gain = float(cmdo_row["raw_pooled_gain_pct"])

    require({"gain_vs_full_direct", "mae", "direct_mae"}.issubset(u6t.columns), "U6 target summary missing expected fields.")
    u6_gain_vec = u6t["gain_vs_full_direct"].to_numpy(float)
    u6_pos = int(np.sum(np.isfinite(u6_gain_vec) & (u6_gain_vec > 0)))
    u6_n = int(np.sum(np.isfinite(u6_gain_vec)))
    u6_direct = u6_state["direct_mae"].to_numpy(float)
    u6_mae = u6_state["mae"].to_numpy(float)
    u6_pooled_gain = 100.0 * (float(np.nanmean(u6_direct)) - float(np.nanmean(u6_mae))) / float(np.nanmean(u6_direct))

    require({"metric", "gain", "direct_mae"}.issubset(u7t.columns), "U7 target summary missing expected fields.")
    u7_auc = u7t[u7t["metric"].astype(str) == "AUC"].copy()
    u7_gain_vec = u7_auc["gain"].to_numpy(float)
    u7_pos = int(np.sum(np.isfinite(u7_gain_vec) & (u7_gain_vec > 0)))
    u7_n = int(np.sum(np.isfinite(u7_gain_vec)))
    require({"metric", "relative_gain"}.issubset(u7_metric.columns), "U7 metric summary missing metric/relative_gain.")
    auc_metric = u7_metric[u7_metric["metric"].astype(str) == "AUC"]
    require(len(auc_metric) == 1, "U7 AUC metric row is not unique.")
    u7_pooled_gain = 100.0 * float(auc_metric.iloc[0]["relative_gain"])

    print("\n[3] Generalization breadth")
    print(f"  development : {dev_pos}/{dev_n} improved | pooled gain {dev_gain:+.3f}%")
    print(f"  cross-domain: {u6_pos}/{u6_n} improved | pooled gain {u6_pooled_gain:+.3f}%")
    print(f"  clinical AUC : {u7_pos}/{u7_n} improved | pooled gain {u7_pooled_gain:+.3f}%")

    # ------------------------------------------------------------------
    # U10 composition cost and HAC margin.
    # ------------------------------------------------------------------
    final_json_path = repo / "source_data" / "figure5_final_system" / "CMDO_Figure5_Final_System_v1.0.json"
    require(final_json_path.is_file(), f"Missing final-system JSON: {final_json_path}")
    final_json = json.loads(final_json_path.read_text(encoding="utf-8"))
    u10_rel = final_json["sources"]["u10_dependence_csv"]
    u10_path = repo / u10_rel
    require(u10_path.is_file(), f"Missing U10 dependence CSV: {u10_path}")
    u10 = pd.read_csv(u10_path)
    hac = recompute_hac(u10)

    frozen = final_json["preserve_u10_hac_postcompletion"]
    checks = {
        "H": "H",
        "A": "A",
        "C_shared": "C_shared",
        "C_permuted": "C_permuted",
        "C_role_separated_prediction": "C_role_separated_prediction",
    }
    for got_key, ref_key in checks.items():
        require(abs(hac[got_key] - float(frozen[ref_key])) <= 5e-7, f"HAC fingerprint mismatch: {got_key}")

    require(hac["margin_shared"] < 0, "Shared HAC margin expected negative.")
    require(hac["margin_permuted"] > 0, "Permuted HAC margin expected positive.")
    require(hac["margin_role_separated_prediction"] > 0, "Role-separated HAC margin expected positive.")

    print("\n[4] Composition cost and HAC margin")
    print(f"  C shared       = {hac['C_shared']:.8f}")
    print(f"  C permuted     = {hac['C_permuted']:.8f}  ({hac['C_reduction_permuted_pct']:.2f}% lower)")
    print(f"  C role-sep     = {hac['C_role_separated_prediction']:.8f}  ({hac['C_reduction_role_separated_prediction_pct']:.2f}% lower)")
    print(f"  margin shared  = {hac['margin_shared']:+.8f}")
    print(f"  margin perm    = {hac['margin_permuted']:+.8f}")
    print(f"  margin role    = {hac['margin_role_separated_prediction']:+.8f}")

    # ------------------------------------------------------------------
    # Freeze audit outputs locally. They remain untracked until user review.
    # ------------------------------------------------------------------
    outdir = repo / "source_data" / "figure5_final_system" / "objective_audit"
    outdir.mkdir(parents=True, exist_ok=True)

    cand_out = outdir / "CMDO_Figure5_Certified_Utility_Candidates_v0.1.csv"
    obj_out = outdir / "CMDO_Figure5_System_Objectives_v0.1.csv"
    json_out = outdir / "CMDO_Figure5_System_Objectives_v0.1.json"

    cand.to_csv(cand_out, index=False, float_format="%.12g")

    objective_rows = [
        {"panel": "A", "metric": "certified_utility_pct", "scenario": "CMDO", "value": float(cmdo_row["certified_utility_pct"]), "direction": "higher", "status": "eligible_winner", "note": "Largest pooled gain among U5F frozen eligible candidates."},
        {"panel": "B", "metric": "generalization_breadth_pct", "scenario": "development", "value": 100.0 * dev_pos / dev_n, "direction": "higher", "status": f"{dev_pos}/{dev_n}", "note": f"pooled_gain_pct={dev_gain:.12g}"},
        {"panel": "B", "metric": "generalization_breadth_pct", "scenario": "cross_domain_U6", "value": 100.0 * u6_pos / u6_n, "direction": "higher", "status": f"{u6_pos}/{u6_n}", "note": f"pooled_gain_pct={u6_pooled_gain:.12g}"},
        {"panel": "B", "metric": "generalization_breadth_pct", "scenario": "clinical_U7_AUC", "value": 100.0 * u7_pos / u7_n, "direction": "higher", "status": f"{u7_pos}/{u7_n}", "note": f"pooled_gain_pct={u7_pooled_gain:.12g}"},
        {"panel": "C", "metric": "composition_cost_C", "scenario": "shared_adaptive", "value": hac["C_shared"], "direction": "lower", "status": "observed_postcompletion", "note": "shared composition"},
        {"panel": "C", "metric": "composition_cost_C", "scenario": "permuted_control", "value": hac["C_permuted"], "direction": "lower", "status": "mechanistic_control", "note": f"reduction_pct={hac['C_reduction_permuted_pct']:.12g}"},
        {"panel": "C", "metric": "composition_cost_C", "scenario": "role_separated_prediction", "value": hac["C_role_separated_prediction"], "direction": "lower", "status": "postcompletion_prediction", "note": f"reduction_pct={hac['C_reduction_role_separated_prediction_pct']:.12g}"},
        {"panel": "D", "metric": "composability_margin_H_minus_A_plus_C", "scenario": "shared_adaptive", "value": hac["margin_shared"], "direction": "higher", "status": "FAIL", "note": "negative = fixed-rule-preferable side"},
        {"panel": "D", "metric": "composability_margin_H_minus_A_plus_C", "scenario": "permuted_control", "value": hac["margin_permuted"], "direction": "higher", "status": "PASS", "note": "post-completion mechanistic control"},
        {"panel": "D", "metric": "composability_margin_H_minus_A_plus_C", "scenario": "role_separated_prediction", "value": hac["margin_role_separated_prediction"], "direction": "higher", "status": "PASS", "note": "post-completion prediction; not prospective confirmation"},
    ]
    objectives = pd.DataFrame(objective_rows)
    objectives.to_csv(obj_out, index=False, float_format="%.12g")

    result = {
        "schema": "CMDO_FIGURE5_SYSTEM_OBJECTIVES_v0.1",
        "status": "DESCRIPTIVE_AUDIT_OF_FROZEN_SYSTEM_OBJECTIVES",
        "claim_boundary": {
            "certified_utility": "U5F frozen development selection objective; not an unrestricted-MAE claim.",
            "breadth": "Frozen U5F development, U6 cross-domain and U7 clinical AUC target summaries.",
            "hac": "Post-completion mechanistic analysis; does not replace U10 prospective MECHANISM_NOT_CONFIRMED verdict.",
            "role_separated": "Prediction/control only; not prospectively validated final CMDO implementation.",
        },
        "certified_utility": {
            "winner": selected,
            "cmdo_certified_utility_pct": float(cmdo_row["certified_utility_pct"]),
            "eligible_methods": eligible["method"].tolist(),
        },
        "breadth": {
            "development": {"improved": dev_pos, "total": dev_n, "breadth_pct": 100.0 * dev_pos / dev_n, "pooled_gain_pct": dev_gain},
            "cross_domain_U6": {"improved": u6_pos, "total": u6_n, "breadth_pct": 100.0 * u6_pos / u6_n, "pooled_gain_pct": u6_pooled_gain},
            "clinical_U7_AUC": {"improved": u7_pos, "total": u7_n, "breadth_pct": 100.0 * u7_pos / u7_n, "pooled_gain_pct": u7_pooled_gain},
        },
        "hac": hac,
        "prospective_verdict": str(final_json["preserve_u10_prospective"]["primary_verdict"]),
        "files": {
            "candidate_csv": str(cand_out.relative_to(repo)).replace("\\", "/"),
            "objectives_csv": str(obj_out.relative_to(repo)).replace("\\", "/"),
        },
    }
    json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\n" + "=" * 92)
    print(" FIGURE 5 SYSTEM-OBJECTIVE AUDIT: PASS")
    print("=" * 92)
    print("Interpretation boundary:")
    print("  - CMDO wins certified utility among the pre-specified U5F eligible candidates.")
    print("  - Breadth is reported from frozen development/U6/U7 targets; no target is omitted.")
    print("  - C and H-(A+C) are U10 post-completion mechanism quantities.")
    print("  - Role-separated PASS is a prediction/control, NOT prospective confirmation.")
    print("  - U10 prospective verdict remains MECHANISM_NOT_CONFIRMED.")
    print("\nGenerated local files:")
    print(f"  {cand_out}")
    print(f"  {obj_out}")
    print(f"  {json_out}")


if __name__ == "__main__":
    main()
