#!/usr/bin/env python3
"""Build the SHA-256 manifest for the CMDO submission-v2 reviewer pathway.

Run only after all submission-v2 scientific sources, renderers, provenance,
documentation and verifiers are frozen. The manifest intentionally does not
include itself, so it can be committed as the final content addition before
the exact fresh-clone acceptance run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

V2_SCOPE = [
    # Figure 1 frozen real-data / witness assets
    "source_data/figure1_assets/Figure1_assets_selected_v1.mat",
    "U11_Information_Closure/01_Result/U11_WORLD_PLUS_georgia_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_MINUS_georgia_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_PLUS_cpsc_2018_v0.1.csv",
    "U11_Information_Closure/01_Result/U11_WORLD_MINUS_cpsc_2018_v0.1.csv",

    # Frozen developmental / U6 / U7 reviewer tables
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

    # Frozen 185-state post-completion synthesis
    "source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv",

    # Deferred sealed eICU share-safe aggregate record
    "source_data/figure3_eicu/README.md",
    "source_data/figure3_eicu/StageU9_Hospital_Summary_v1_0.csv",
    "source_data/figure3_eicu/StageU9_Gate_Table_v1_0.csv",
    "source_data/figure3_eicu/StageU9_Method_Summary_v1_0.csv",
    "source_data/figure3_eicu/StageU9_Decision_Summary_v1_0.csv",
    "source_data/figure3_eicu/StageU9_Telemetry_Pair_Results_v1_0.csv",
    "source_data/figure3_eicu/StageU9_Report_v1_0.md",
    "provenance/eicu_deferred_execution_v1_0.json",

    # PCC / CERTIFY / PRESERVE frozen products
    "source_data/pcc/PCC_frontier_classified.csv",
    "source_data/pcc/PCC_scaling_summary_v12.csv",
    "source_data/pcc/CMDO_185_realized_projection.csv",
    "source_data/pcc/CMDO_U9_REUSE_PRESERVE_bridge.csv",
    "U10_Prospective_ECG/01_Prospective_Result/U10_PRIMARY_RESULT.json",
    "U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv",

    # Extended Data Figure 3 authoritative stress source
    "source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv",

    # Active submission-v2 runner and renderers
    "RUN_SUBMISSION_V2_FIGURES.m",
    "matlab/submission_figures/Figure1_Evidential_Order_PCC.m",
    "matlab/submission_figures/Figure2_IDENTIFY_Validation.m",
    "matlab/submission_figures/Figure3_REUSE_Refined.m",
    "matlab/submission_figures/Figure4_CERTIFY.m",
    "matlab/submission_figures/Figure5_PRESERVE_PCC.m",
    "matlab/submission_figures/ED1_OutcomeFreeBoundary_v9.m",
    "matlab/submission_figures/ED2_IntegrityControls_v2.m",
    "matlab/submission_figures/ED3_RobustnessEfficiency_v1.m",
    "matlab/submission_figures/cmdo_submission_load.m",

    # Submission-v2 audit/provenance/documentation controls
    "scripts/verify_submission_v2_science.py",
    "scripts/build_submission_v2_manifest.py",
    "scripts/verify_submission_v2_manifest.py",
    "provenance/stage_registry.json",
    "docs/SUBMISSION_V2_FREEZE_SCOPE_20260909.md",
    "README.md",
    ".gitattributes",
    ".github/workflows/static-integrity.yml",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="Repository root; defaults to script parent repository")
    parser.add_argument("--out", default="provenance/submission_v2_manifest.csv")
    args = parser.parse_args()

    script = Path(__file__).resolve()
    repo = Path(args.repo).resolve() if args.repo else script.parents[1]
    out = repo / args.out

    duplicates = [p for p in sorted(set(V2_SCOPE)) if V2_SCOPE.count(p) > 1]
    if duplicates:
        raise SystemExit("Duplicate manifest scope entries:\n" + "\n".join(duplicates))

    missing = [rel for rel in V2_SCOPE if not (repo / rel).is_file()]
    if missing:
        raise SystemExit("Missing submission-v2 scope files:\n" + "\n".join(missing))

    rows = []
    for rel in V2_SCOPE:
        p = repo / rel
        rows.append({
            "path": rel.replace("/", "\\"),
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[PASS] wrote {len(rows)} submission-v2 entries: {out}")
    print(f"manifest_sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
