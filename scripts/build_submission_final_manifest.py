#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

FINAL_SCOPE = [
    # Figure 1 / frozen U4-U7 reviewer inputs
    "source_data/figure1_assets/Figure1_assets_selected_v1.mat",
    "source_data/submission_frozen/StageU4C_Audit_State_Results_v1.1.csv",
    "source_data/submission_frozen/StageU4C_Component_Fits_v1.1.csv",
    "source_data/submission_frozen/StageU4C_Component_Trajectory_Predictions_v1.1.csv",
    "source_data/submission_frozen/StageU4C_Evidence_Expiry_Map_v1.1.csv",
    "source_data/submission_frozen/StageU5B_Audit_State_Results_v1.0.csv",
    "source_data/submission_frozen/StageU6_Audit_State_Results_v1.0.csv",
    "source_data/submission_frozen/StageU6_Target_Summary_v1.0.csv",
    "source_data/submission_frozen/StageU7_State_Results_v1.0.csv",
    "source_data/submission_frozen/StageU7_Target_Metric_Summary_v1.0.csv",
    "source_data/submission_frozen/StageU7_Metric_Summary_v1.0.csv",
    # Figure 3 admissibility synthesis
    "source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv",
    # Figure 4 PRESERVE
    "source_data/figure4_submission/CMDO_Figure4_PRESERVE_Source_v1.csv",
    "source_data/figure4_submission/CMDO_Figure4_PRESERVE_Source_v1_provenance.json",
    "U10_Prospective_ECG/01_Prospective_Result/U10_PRIMARY_RESULT.json",
    "U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv",
    # Figure 5 authoritative and stability diagnostic
    "source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv",
    "source_data/figure5_submission/diagnostics/CMDO_Figure5_MC_Stability_5x200.csv",
    "source_data/figure5_submission/diagnostics/CMDO_Figure5_MC_Stability_5x200_provenance.json",
    # U11 information-closure witnesses used by Figure 2
    "U11_Information_Closure/01_Result/U11_WORLD_PLUS_georgia_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_MINUS_georgia_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_PLUS_cpsc_2018_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_MINUS_cpsc_2018_v0.1.csv",
    # Active reviewer-facing renderers and audit entry points
    "RUN_SUBMISSION_FIGURES.m",
    "RUN_REVIEWER_END_TO_END.m",
    "matlab/submission_figures/Figure1_IDA_RealData_Final.m",
    "matlab/submission_figures/Figure2_IDENTIFY_Validation.m",
    "matlab/submission_figures/Figure3_REUSE_Validation.m",
    "matlab/submission_figures/Figure4_PRESERVE_Refined.m",
    "matlab/submission_figures/Figure5_PhaseBoundary.m",
    "matlab/submission_figures/ED1_OutcomeFreeBoundary_v9.m",
    "matlab/submission_figures/ED2_IntegrityControls_v2.m",
    "matlab/submission_figures/cmdo_submission_load.m",
    "scripts/stress_replay/CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py",
    "scripts/stress_replay/run_figure5_mc_stability.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="Repository root; defaults to script parent repository")
    parser.add_argument("--out", default="provenance/submission_final_manifest_v1.csv")
    args = parser.parse_args()

    script = Path(__file__).resolve()
    repo = Path(args.repo).resolve() if args.repo else script.parents[1]
    out = repo / args.out

    missing = [rel for rel in FINAL_SCOPE if not (repo / rel).is_file()]
    if missing:
        raise SystemExit("Missing final-scope files:\n" + "\n".join(missing))

    rows = []
    for rel in FINAL_SCOPE:
        p = repo / rel
        rows.append({"path": rel.replace("/", "\\"), "bytes": p.stat().st_size, "sha256": sha256(p)})

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256"])
        w.writeheader()
        w.writerows(rows)

    print(f"[PASS] wrote {len(rows)} entries: {out}")
    print(f"manifest_sha256={sha256(out)}")


if __name__ == "__main__":
    main()
