#!/usr/bin/env python3
"""
CMDO Figure 5 identification-radius audit
=========================================

Purpose
-------
Build a frozen-data audit for the theory-first Figure-5 quantities:

1) an algorithm-independent minimax lower bound for any estimator restricted
   to the same outcome-independent telemetry information class, using the
   frozen U11 constructive information-closure witness;
2) empirical finite-budget error contraction after representative current
   outcomes are available, using the frozen U8 direct-audit errors embedded in
   the sealed MATLAB renderer.

The central witness quantity is

    R_id = 0.5 * |psi_plus - psi_minus|,

because two worlds have identical observable telemetry but opposite AUC values.
For any estimator T(O) measurable with respect to the same observable O,

    max(|T(O)-psi_plus|, |T(O)-psi_minus|) >= R_id.

This is a minimax lower bound over the constructed information class.  It is
NOT a claim about the true clinical outcomes of the U11 cohorts.

The U8 contraction is descriptive empirical evidence after current outcomes
are observed.  Its log-log slope is checked against the frozen sealed value;
it is not presented as a new asymptotic theorem.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable


U11_RESULT_REL = Path("U11_Information_Closure/01_Result/U11_INFORMATION_CLOSURE_RESULT_v0.1.json")
U11_MANIFEST_REL = Path("U11_Information_Closure/01_Result/U11_RESULT_SHA256_MANIFEST_v0.1.csv")
SEALED_FIG5_REL = Path("matlab/figures/main/Figure5.m")

EXPECTED_U11_VERDICT = "INFORMATION_CLOSURE_WITNESS_CONFIRMED"
EXPECTED_BUDGETS = [128.0, 256.0, 512.0, 1024.0]
SLOPE_TOL = 5e-10


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


def numeric_tokens(text: str) -> list[float]:
    pat = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    return [float(x) for x in re.findall(pat, text)]


def extract_matlab_array(text: str, name: str) -> list[list[float]]:
    m = re.search(
        rf"(?ms)^\s*{re.escape(name)}\s*=\s*\[(.*?)\];",
        text,
    )
    require(m is not None, f"Could not parse MATLAB array: {name}")
    body = m.group(1).replace("...", " ")
    body = re.sub(r"%[^\n\r]*", "", body)
    rows = []
    for piece in body.split(";"):
        vals = numeric_tokens(piece)
        if vals:
            rows.append(vals)
    require(len(rows) > 0, f"MATLAB array was empty: {name}")
    widths = {len(r) for r in rows}
    require(len(widths) == 1, f"MATLAB array is ragged: {name} widths={sorted(widths)}")
    return rows


def extract_matlab_scalar(text: str, name: str) -> float:
    m = re.search(
        rf"(?ms)^\s*{re.escape(name)}\s*=\s*(.*?)\s*;",
        text,
    )
    require(m is not None, f"Could not parse MATLAB scalar: {name}")
    body = m.group(1).replace("...", " ")
    vals = numeric_tokens(body)
    require(len(vals) == 1, f"Expected one scalar for {name}; found {vals}")
    return vals[0]


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    require(len(vals) > 0, "Cannot average an empty sequence.")
    return sum(vals) / len(vals)


def loglog_slope(x: list[float], y: list[float]) -> float:
    require(len(x) == len(y) and len(x) >= 2, "Invalid data for slope.")
    lx = [math.log(v) for v in x]
    ly = [math.log(v) for v in y]
    mx = mean(lx)
    my = mean(ly)
    denom = sum((v - mx) ** 2 for v in lx)
    require(denom > 0, "Degenerate x values for slope.")
    return sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / denom


def sample_cv(values: list[float]) -> float:
    require(len(values) >= 2, "Need at least two values for CV.")
    mu = mean(values)
    require(mu != 0, "Mean is zero in CV.")
    var = sum((x - mu) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var) / abs(mu)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    require(repo.is_dir(), f"Repository does not exist: {repo}")

    u11_path = repo / U11_RESULT_REL
    manifest_path = repo / U11_MANIFEST_REL
    fig5_path = repo / SEALED_FIG5_REL

    for path in (u11_path, manifest_path, fig5_path):
        require(path.is_file(), f"Required frozen source missing: {path}")

    print("=" * 92)
    print(" CMDO FIGURE 5 IDENTIFICATION-RADIUS AUDIT")
    print(" outcome-free minimax lower bound -> current-outcome sampling contraction")
    print("=" * 92)
    print(f"Repository : {repo}")

    # ------------------------------------------------------------------
    # 1) Verify U11 result integrity against its frozen SHA manifest.
    # ------------------------------------------------------------------
    manifest_rows = list(csv.DictReader(manifest_path.open("r", encoding="utf-8")))
    manifest_map = {str(r["file"]): str(r["sha256"]).lower() for r in manifest_rows}
    result_name = u11_path.name
    require(result_name in manifest_map, f"U11 result absent from manifest: {result_name}")
    u11_sha = sha256_file(u11_path).lower()
    require(u11_sha == manifest_map[result_name], "U11 result SHA256 mismatch.")

    u11 = json.loads(u11_path.read_text(encoding="utf-8"))
    require(str(u11.get("primary_verdict")) == EXPECTED_U11_VERDICT, "Unexpected U11 primary verdict.")

    witness_rows: list[dict] = []
    lower_bounds: list[float] = []

    print("\n[1] U11 information-closure witness")
    for cohort_name, cohort in u11["cohorts"].items():
        cons = cohort["construction"]
        plus_auc = float(cohort["world_plus"]["auc"])
        minus_auc = float(cohort["world_minus"]["auc"])
        gap = abs(plus_auc - minus_auc)
        radius = 0.5 * gap

        require(bool(cons["matched_prevalence"]), f"{cohort_name}: prevalence is not matched.")
        require(bool(cons["telemetry_byte_identity_claim"]), f"{cohort_name}: telemetry identity claim false.")
        require(
            str(cons["telemetry_sha256_world_plus"]) == str(cons["telemetry_sha256_world_minus"]),
            f"{cohort_name}: telemetry hashes differ.",
        )
        require(abs(float(cohort["prevalence_difference"])) <= 1e-15, f"{cohort_name}: prevalence differs.")
        require(bool(cohort["primary_success"]), f"{cohort_name}: primary witness failed.")
        require(abs(gap - 1.0) <= 1e-12, f"{cohort_name}: expected AUC gap 1, got {gap}.")
        require(abs(radius - 0.5) <= 1e-12, f"{cohort_name}: expected radius 0.5, got {radius}.")

        lower_bounds.append(radius)
        witness_rows.append(
            {
                "information_class": "outcome_independent_telemetry",
                "cohort": cohort_name,
                "n": int(cons["n"]),
                "matched_prevalence": True,
                "telemetry_identical": True,
                "auc_world_plus": plus_auc,
                "auc_world_minus": minus_auc,
                "auc_identified_diameter_witness": gap,
                "minimax_abs_auc_error_lower_bound": radius,
                "status": "WITNESS_CONFIRMED",
            }
        )
        print(
            f"  {cohort_name:<12s} same telemetry | AUC {plus_auc:.1f} vs {minus_auc:.1f} "
            f"| diameter witness={gap:.1f} | minimax |error| >= {radius:.3f}"
        )

    # ------------------------------------------------------------------
    # 2) Parse the sealed U8 direct-audit errors from the frozen renderer.
    #    This uses current outcomes and demonstrates sampling contraction.
    # ------------------------------------------------------------------
    fig5_text = fig5_path.read_text(encoding="utf-8")
    budget_matrix = extract_matlab_array(fig5_text, "budgetsU8")
    require(len(budget_matrix) == 1, "budgetsU8 should be a row vector.")
    budgets = budget_matrix[0]
    require(budgets == EXPECTED_BUDGETS, f"Unexpected U8 budgets: {budgets}")

    direct = extract_matlab_array(fig5_text, "u8_direct")
    require(len(direct) >= 2, "Expected multiple U8 temporal cycles.")
    require(all(len(row) == len(budgets) for row in direct), "U8 direct matrix width mismatch.")
    frozen_slope = extract_matlab_scalar(fig5_text, "u8_slope")

    mean_direct = [mean(row[j] for row in direct) for j in range(len(budgets))]
    recomputed_slope = loglog_slope(budgets, mean_direct)
    sqrt_scaled = [mae * math.sqrt(m) for m, mae in zip(budgets, mean_direct)]
    sqrt_scaled_cv = sample_cv(sqrt_scaled)

    require(
        abs(recomputed_slope - frozen_slope) <= SLOPE_TOL,
        f"U8 root-budget slope mismatch: recomputed {recomputed_slope} vs frozen {frozen_slope}",
    )
    require(all(mean_direct[i + 1] < mean_direct[i] for i in range(len(mean_direct) - 1)), "U8 mean direct MAE is not strictly decreasing with budget.")
    require(-0.65 <= recomputed_slope <= -0.35, f"U8 slope is not root-m-like: {recomputed_slope}")

    contraction_rows: list[dict] = []
    print("\n[2] Current-outcome direct-audit contraction (U8 temporal reserve)")
    for m, mae, scaled in zip(budgets, mean_direct, sqrt_scaled):
        rel = mae / mean_direct[0]
        contraction_rows.append(
            {
                "information_class": "representative_current_outcome_audit",
                "audit_budget_m": int(m),
                "n_temporal_cycles": len(direct),
                "mean_direct_mae": mae,
                "mae_relative_to_m128": rel,
                "mae_times_sqrt_m": scaled,
                "global_loglog_slope": recomputed_slope,
                "status": "EMPIRICAL_SAMPLING_CONTRACTION",
            }
        )
        print(
            f"  m={int(m):4d} | mean direct MAE={mae:.6f} | relative={rel:.3f} "
            f"| MAE*sqrt(m)={scaled:.6f}"
        )

    print(f"  log-log slope      = {recomputed_slope:+.6f}")
    print(f"  frozen slope       = {frozen_slope:+.6f}")
    print(f"  CV[MAE*sqrt(m)]    = {100.0 * sqrt_scaled_cv:.2f}%")

    # ------------------------------------------------------------------
    # 3) Write local audit products. They remain untracked until reviewed.
    # ------------------------------------------------------------------
    outdir = repo / "source_data" / "figure5_final_system" / "identification_audit"
    outdir.mkdir(parents=True, exist_ok=True)

    witness_csv = outdir / "CMDO_Figure5_Identification_Witness_v0.1.csv"
    contraction_csv = outdir / "CMDO_Figure5_Outcome_Audit_Contraction_v0.1.csv"
    json_out = outdir / "CMDO_Figure5_Identification_Radius_v0.1.json"

    write_csv(
        witness_csv,
        witness_rows,
        [
            "information_class",
            "cohort",
            "n",
            "matched_prevalence",
            "telemetry_identical",
            "auc_world_plus",
            "auc_world_minus",
            "auc_identified_diameter_witness",
            "minimax_abs_auc_error_lower_bound",
            "status",
        ],
    )
    write_csv(
        contraction_csv,
        contraction_rows,
        [
            "information_class",
            "audit_budget_m",
            "n_temporal_cycles",
            "mean_direct_mae",
            "mae_relative_to_m128",
            "mae_times_sqrt_m",
            "global_loglog_slope",
            "status",
        ],
    )

    result = {
        "schema": "CMDO_FIGURE5_IDENTIFICATION_RADIUS_v0.1",
        "status": "FROZEN_DATA_IDENTIFICATION_AUDIT_PASS",
        "definition": {
            "name": "performance identification radius witness",
            "symbol": "R_id",
            "formula": "R_id = 0.5 * |psi_plus - psi_minus| for two observationally identical worlds",
            "minimax_statement": "For any estimator T measurable with respect to the same outcome-independent telemetry O, max(|T(O)-psi_plus|, |T(O)-psi_minus|) >= R_id.",
        },
        "u11": {
            "primary_verdict": str(u11["primary_verdict"]),
            "result_sha256": u11_sha,
            "cohorts": witness_rows,
            "common_minimax_abs_auc_error_lower_bound": min(lower_bounds),
        },
        "u8_current_outcome_audit": {
            "source": str(SEALED_FIG5_REL).replace("\\", "/"),
            "budgets": [int(v) for v in budgets],
            "temporal_cycles": len(direct),
            "mean_direct_mae": mean_direct,
            "loglog_slope": recomputed_slope,
            "frozen_loglog_slope": frozen_slope,
            "mae_times_sqrt_m": sqrt_scaled,
            "mae_times_sqrt_m_cv_pct": 100.0 * sqrt_scaled_cv,
        },
        "claim_boundary": {
            "u11": "Constructive information-class witness; not a claim about the true clinical outcomes of either cohort.",
            "minimax": "Lower bound applies to estimators restricted to the same outcome-independent telemetry information class.",
            "u8": "Empirical finite-budget direct-audit contraction on the frozen temporal reserve; not the same-cohort numerical counterpart of the U11 lower bound.",
            "slope": "Descriptive root-budget scaling evidence, not a new asymptotic theorem.",
        },
        "files": {
            "witness_csv": str(witness_csv.relative_to(repo)).replace("\\", "/"),
            "contraction_csv": str(contraction_csv.relative_to(repo)).replace("\\", "/"),
        },
    }
    json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\n" + "=" * 92)
    print(" FIGURE 5 IDENTIFICATION-RADIUS AUDIT: PASS")
    print("=" * 92)
    print("Compact result:")
    print(f"  Outcome-free U11 minimax |AUC error| lower bound : >= {min(lower_bounds):.3f}")
    print(f"  Current-outcome U8 direct-audit slope            : {recomputed_slope:+.6f}")
    print(f"  U8 mean MAE: m=128 -> m=1024                    : {mean_direct[0]:.6f} -> {mean_direct[-1]:.6f}")
    print(f"  CV of MAE*sqrt(m)                               : {100.0 * sqrt_scaled_cv:.2f}%")
    print("Interpretation boundary:")
    print("  - The 0.5 lower bound is algorithm-independent only within the same outcome-free information class.")
    print("  - U11 is a constructive identification witness, not a real-outcome clinical claim.")
    print("  - U8 demonstrates empirical sampling-error contraction after current outcomes are observed.")
    print("  - Do not present the U11 lower bound and U8 MAE as a same-cohort head-to-head estimator benchmark.")
    print("\nGenerated local files:")
    print(f"  {witness_csv}")
    print(f"  {contraction_csv}")
    print(f"  {json_out}")


if __name__ == "__main__":
    main()
