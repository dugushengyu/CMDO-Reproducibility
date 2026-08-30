#!/usr/bin/env python3
"""
CMDO Figure 5 theory-axis audit
===============================

Purpose
-------
Audit the remaining two theory quantities proposed for the final CMDO system
story, directly from frozen GitHub evidence:

    Lambda = B^2 / V

and

    kappa = H / (A + C).

Lambda is a dimensionless bias-to-variance ratio. Under the quadratic fixed-
historical-anchor risk model

    R(w) / V = (1-w)^2 + Lambda * w^2,

its oracle shrinkage weight is

    w* = 1 / (1 + Lambda).

Thus Lambda does not act as a binary certificate; it describes how strongly
historical bias competes with current-audit variance.

kappa is a dimensionless adaptive benefit-to-cost ratio. The HAC frontier
H > A + C is equivalent to

    kappa > 1.

The role-separated kappa is a post-completion prediction/control only. This
script does not change the prospective U10 verdict MECHANISM_NOT_CONFIRMED.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean


U10_REL = Path("U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv")
FINAL_SUMMARY_REL = Path("source_data/figure5_final_system/CMDO_Figure5_Final_System_v1.0.json")
OBJECTIVE_JSON_REL = Path("source_data/figure5_final_system/objective_audit/CMDO_Figure5_System_Objectives_v0.1.json")
IDENT_JSON_REL = Path("source_data/figure5_final_system/identification_audit/CMDO_Figure5_Identification_Radius_v0.1.json")

EXPECTED_U10_SHA256 = "580a0480391ea40cad021fc0264350f6eba357d24a219a670687163159470bcc"
EXPECTED_DATASETS = {"georgia", "cpsc_2018"}
EXPECTED_BUDGETS = {128, 256, 512, 1024}
TOL = 5e-10


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str) -> float:
    try:
        x = float(row[key])
    except Exception as exc:
        raise RuntimeError(f"Invalid numeric field {key}: {row.get(key)!r}") from exc
    require(math.isfinite(x), f"Non-finite field {key}: {x}")
    return x


def pearson(x: list[float], y: list[float]) -> float:
    require(len(x) == len(y) and len(x) >= 2, "Invalid vectors for correlation.")
    mx = mean(x)
    my = mean(y)
    num = sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx = math.sqrt(sum((a-mx)**2 for a in x))
    dy = math.sqrt(sum((b-my)**2 for b in y))
    require(dx > 0 and dy > 0, "Degenerate vectors for correlation.")
    return num/(dx*dy)


def almost(a: float, b: float, tol: float=TOL) -> bool:
    return abs(a-b) <= tol * max(1.0, abs(a), abs(b))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    require(repo.is_dir(), f"Repository does not exist: {repo}")

    u10_path = repo / U10_REL
    final_path = repo / FINAL_SUMMARY_REL
    objective_path = repo / OBJECTIVE_JSON_REL
    ident_path = repo / IDENT_JSON_REL

    for p in (u10_path, final_path, objective_path, ident_path):
        require(p.is_file(), f"Required frozen input missing: {p}")

    print("="*92)
    print(" CMDO FIGURE 5 THEORY-AXIS AUDIT")
    print(" R_id -> Lambda = B^2/V -> kappa = H/(A+C)")
    print("="*92)
    print(f"Repository : {repo}")

    # ------------------------------------------------------------------
    # Integrity and frozen boundaries.
    # ------------------------------------------------------------------
    u10_sha = sha256_file(u10_path).lower()
    require(u10_sha == EXPECTED_U10_SHA256, f"U10 dependence CSV SHA mismatch: {u10_sha}")

    final_summary = json.loads(final_path.read_text(encoding="utf-8"))
    objective = json.loads(objective_path.read_text(encoding="utf-8"))
    ident = json.loads(ident_path.read_text(encoding="utf-8"))

    require(str(final_summary["preserve_u10_prospective"]["primary_verdict"]) == "MECHANISM_NOT_CONFIRMED", "Prospective U10 verdict changed.")
    require(str(objective["prospective_verdict"]) == "MECHANISM_NOT_CONFIRMED", "Objective audit prospective verdict changed.")
    rid = float(ident["u11"]["common_minimax_abs_auc_error_lower_bound"])
    require(almost(rid, 0.5), f"Unexpected frozen R_id witness: {rid}")

    rows = list(csv.DictReader(u10_path.open("r", encoding="utf-8")))
    require(len(rows) == 8, f"Expected 8 U10 dataset-budget rows, found {len(rows)}")
    require({r["dataset"] for r in rows} == EXPECTED_DATASETS, "Unexpected U10 dataset roster.")
    for ds in EXPECTED_DATASETS:
        ds_budgets = {int(float(r["budget"])) for r in rows if r["dataset"] == ds}
        require(ds_budgets == EXPECTED_BUDGETS, f"Unexpected budgets for {ds}: {sorted(ds_budgets)}")

    required_cols = {
        "dataset","budget","B","direct_mse","shared_constant_mean_weight",
        "shared_adaptive_mse","shared_constant_mean_mse","shared_permuted_weight_mse",
        "shared_tax_weight_heterogeneity",
    }
    require(required_cols.issubset(rows[0].keys()), f"U10 table missing columns: {sorted(required_cols-set(rows[0].keys()))}")

    # ------------------------------------------------------------------
    # Lambda = B^2 / V and w* = 1/(1+Lambda)
    # ------------------------------------------------------------------
    lambda_rows: list[dict] = []
    all_lam: list[float] = []
    all_wstar: list[float] = []
    all_wobs: list[float] = []

    print("\n[1] REUSE axis: Lambda = B^2 / V")
    for r in sorted(rows, key=lambda z: (z["dataset"], int(float(z["budget"])))):
        ds = r["dataset"]
        budget = int(float(r["budget"]))
        B = f(r,"B")
        V = f(r,"direct_mse")
        require(V > 0, f"{ds}/{budget}: direct_mse must be > 0")
        lam = (B*B)/V
        wstar = 1.0/(1.0+lam)
        wobs = f(r,"shared_constant_mean_weight")
        require(lam >= 0, f"{ds}/{budget}: Lambda < 0")
        require(0 < wstar <= 1, f"{ds}/{budget}: invalid w*={wstar}")

        lambda_rows.append({
            "dataset": ds,
            "budget": budget,
            "B": B,
            "V_direct_mse": V,
            "lambda_B2_over_V": lam,
            "oracle_quadratic_weight_wstar": wstar,
            "observed_shared_constant_mean_weight": wobs,
            "weight_gap_observed_minus_wstar": wobs-wstar,
            "bias_variance_regime": "bias_dominant" if lam > 1 else ("balanced" if almost(lam,1.0,1e-6) else "variance_dominant"),
        })
        all_lam.append(lam)
        all_wstar.append(wstar)
        all_wobs.append(wobs)
        print(f"  {ds:<10s} m={budget:4d} | Lambda={lam:7.3f} | w*={wstar:6.3f} | observed fixed w={wobs:6.3f}")

    # As current-audit variance shrinks with budget, Lambda should rise and w* fall.
    for ds in sorted(EXPECTED_DATASETS):
        rr = [x for x in lambda_rows if x["dataset"] == ds]
        rr.sort(key=lambda x: x["budget"])
        lams = [x["lambda_B2_over_V"] for x in rr]
        wstars = [x["oracle_quadratic_weight_wstar"] for x in rr]
        require(all(lams[i+1] > lams[i] for i in range(len(lams)-1)), f"{ds}: Lambda is not strictly increasing with budget.")
        require(all(wstars[i+1] < wstars[i] for i in range(len(wstars)-1)), f"{ds}: w* is not strictly decreasing with budget.")

    corr_w = pearson(all_wstar, all_wobs)
    require(corr_w > 0.75, f"Observed fixed weights do not track w*: correlation={corr_w}")
    print(f"  corr(w*, observed fixed weight) = {corr_w:.3f}")
    print(f"  Lambda range                    = {min(all_lam):.3f} to {max(all_lam):.3f}")

    # ------------------------------------------------------------------
    # Recompute H, A, C and kappa from frozen U10 rows.
    # ------------------------------------------------------------------
    mean_lambda = mean(all_lam)
    wglobal = 1.0/(1.0+mean_lambda)

    H_rows: list[float] = []
    A_rows: list[float] = []
    Cshared_rows: list[float] = []
    Cperm_rows: list[float] = []
    Crole_rows: list[float] = []

    # preserve original CSV ordering; lambda/wstar recomputed row-wise
    for r in rows:
        B = f(r,"B")
        V = f(r,"direct_mse")
        lam = (B*B)/V
        wstar = 1.0/(1.0+lam)
        wbar = f(r,"shared_constant_mean_weight")
        H_rows.append((1.0+lam)*(wstar-wglobal)**2)
        A_rows.append((1.0+lam)*(wbar-wstar)**2)
        Cshared_rows.append((f(r,"shared_adaptive_mse")-f(r,"shared_constant_mean_mse"))/V)
        Cperm_rows.append((f(r,"shared_permuted_weight_mse")-f(r,"shared_constant_mean_mse"))/V)
        Crole_rows.append(f(r,"shared_tax_weight_heterogeneity")/V)

    H = mean(H_rows)
    A = mean(A_rows)
    Cshared = mean(Cshared_rows)
    Cperm = mean(Cperm_rows)
    Crole = mean(Crole_rows)

    frozen_hac = objective["hac"]
    checks = {
        "H": H,
        "A": A,
        "C_shared": Cshared,
        "C_permuted": Cperm,
        "C_role_separated_prediction": Crole,
    }
    frozen_map = {
        "H": float(frozen_hac["H"]),
        "A": float(frozen_hac["A"]),
        "C_shared": float(frozen_hac["C_shared"]),
        "C_permuted": float(frozen_hac["C_permuted"]),
        "C_role_separated_prediction": float(frozen_hac["C_role_separated_prediction"]),
    }
    for key,val in checks.items():
        require(almost(val,frozen_map[key]), f"HAC recomputation mismatch for {key}: {val} vs {frozen_map[key]}")

    scenarios = [
        ("shared_adaptive", Cshared, "observed_postcompletion"),
        ("permuted_control", Cperm, "mechanistic_control"),
        ("role_separated_prediction", Crole, "postcompletion_prediction"),
    ]

    kappa_rows: list[dict] = []
    print("\n[2] PRESERVE axis: kappa = H / (A + C)")
    for name,C,status_src in scenarios:
        denom = A+C
        require(denom > 0, f"{name}: A+C must be positive")
        kappa = H/denom
        margin = H-denom
        status = "COMPOSABLE" if kappa > 1.0 else "FIXED_RULE_PREFERABLE"
        kappa_rows.append({
            "scenario": name,
            "H": H,
            "A": A,
            "C": C,
            "A_plus_C": denom,
            "kappa_H_over_A_plus_C": kappa,
            "H_minus_A_plus_C": margin,
            "threshold": 1.0,
            "status": status,
            "evidence_role": status_src,
        })
        print(f"  {name:<27s} | kappa={kappa:6.3f} | H-(A+C)={margin:+.6f} | {status}")

    require(kappa_rows[0]["kappa_H_over_A_plus_C"] < 1.0, "Shared adaptive unexpectedly crosses kappa=1.")
    require(kappa_rows[1]["kappa_H_over_A_plus_C"] > 1.0, "Permuted control does not cross kappa=1.")
    require(kappa_rows[2]["kappa_H_over_A_plus_C"] > 1.0, "Role-separated prediction does not cross kappa=1.")

    # ------------------------------------------------------------------
    # Freeze local audit products only after user review.
    # ------------------------------------------------------------------
    outdir = repo / "source_data" / "figure5_final_system" / "theory_axis_audit"
    outdir.mkdir(parents=True, exist_ok=True)
    lambda_csv = outdir / "CMDO_Figure5_Lambda_By_State_v0.1.csv"
    kappa_csv = outdir / "CMDO_Figure5_Kappa_v0.1.csv"
    json_out = outdir / "CMDO_Figure5_Theory_Axes_v0.1.json"

    write_csv(lambda_csv, lambda_rows, [
        "dataset","budget","B","V_direct_mse","lambda_B2_over_V",
        "oracle_quadratic_weight_wstar","observed_shared_constant_mean_weight",
        "weight_gap_observed_minus_wstar","bias_variance_regime",
    ])
    write_csv(kappa_csv, kappa_rows, [
        "scenario","H","A","C","A_plus_C","kappa_H_over_A_plus_C",
        "H_minus_A_plus_C","threshold","status","evidence_role",
    ])

    result = {
        "schema": "CMDO_FIGURE5_THEORY_AXES_v0.1",
        "status": "FROZEN_DATA_THEORY_AXIS_AUDIT_PASS",
        "source_integrity": {"u10_dependence_csv_sha256": u10_sha},
        "theory_chain": ["IDENTIFY:R_id", "REUSE:Lambda=B^2/V", "PRESERVE:kappa=H/(A+C)"],
        "R_id": {
            "value": rid,
            "source": str(IDENT_JSON_REL).replace("\\","/"),
            "meaning": "algorithm-independent minimax absolute AUC-error lower-bound witness within the same outcome-independent telemetry information class",
        },
        "Lambda": {
            "definition": "B^2 / V",
            "name": "bias-to-variance ratio",
            "quadratic_risk": "R(w)/V=(1-w)^2+Lambda*w^2",
            "oracle_weight": "w*=1/(1+Lambda)",
            "min": min(all_lam),
            "max": max(all_lam),
            "mean": mean(all_lam),
            "corr_wstar_observed_fixed_weight": corr_w,
            "interpretation": "larger Lambda means historical bias dominates current-audit variance more strongly, so the ideal borrowing weight shrinks",
        },
        "kappa": {
            "definition": "H/(A+C)",
            "name": "adaptive benefit-to-cost ratio",
            "threshold": 1.0,
            "shared_adaptive": kappa_rows[0]["kappa_H_over_A_plus_C"],
            "permuted_control": kappa_rows[1]["kappa_H_over_A_plus_C"],
            "role_separated_prediction": kappa_rows[2]["kappa_H_over_A_plus_C"],
            "interpretation": "kappa>1 is algebraically equivalent to the HAC frontier H>A+C",
        },
        "claim_boundary": {
            "Lambda": "Post-completion U10 bias-to-variance geometry; the oracle quadratic weight is a theory reference, not a deployed estimator.",
            "kappa": "Post-completion mechanistic summary. The role-separated value is a prediction/control only.",
            "prospective": "U10 prospective verdict remains MECHANISM_NOT_CONFIRMED.",
            "R_id": "U11 constructive information-class witness; not real clinical outcomes.",
        },
        "files": {
            "lambda_csv": str(lambda_csv.relative_to(repo)).replace("\\","/"),
            "kappa_csv": str(kappa_csv.relative_to(repo)).replace("\\","/"),
        },
    }
    json_out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    print("\n"+"="*92)
    print(" FIGURE 5 THEORY-AXIS AUDIT: PASS")
    print("="*92)
    print("Compact result:")
    print(f"  R_id lower-bound witness            : {rid:.3f}")
    print(f"  Lambda range                        : {min(all_lam):.3f} -> {max(all_lam):.3f}")
    print(f"  corr(w*, observed fixed weight)     : {corr_w:.3f}")
    print(f"  kappa shared adaptive               : {kappa_rows[0]['kappa_H_over_A_plus_C']:.3f}")
    print(f"  kappa permuted control              : {kappa_rows[1]['kappa_H_over_A_plus_C']:.3f}")
    print(f"  kappa role-separated prediction     : {kappa_rows[2]['kappa_H_over_A_plus_C']:.3f}")
    print("Interpretation boundary:")
    print("  - Lambda is a dimensionless bias-to-variance ratio, not a pass/fail certificate.")
    print("  - w*=1/(1+Lambda) is the oracle quadratic reference weight under the stated risk model.")
    print("  - kappa>1 is exactly equivalent to H>A+C.")
    print("  - Role-separated kappa is post-completion prediction/control, not prospective confirmation.")
    print("  - U10 prospective verdict remains MECHANISM_NOT_CONFIRMED.")
    print("\nGenerated local files:")
    print(f"  {lambda_csv}")
    print(f"  {kappa_csv}")
    print(f"  {json_out}")


if __name__ == "__main__":
    main()
