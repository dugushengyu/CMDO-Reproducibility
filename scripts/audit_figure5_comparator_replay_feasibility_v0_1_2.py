#!/usr/bin/env python3
"""CMDO Figure 5 comparator-replay feasibility audit v0.1.2.

Schema-corrected feasibility audit.

Changes from v0.1.1
-------------------
* retains gzip-safe inspection of CSV.GZ members nested in canonical ZIPs;
* fixes the U7 completed-replicate schema check: the frozen U7 pipeline writes
  `true_metric`, not `true_value`;
* does not execute any comparator and does not change prospective U6/U7 status.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import audit_figure5_comparator_replay_feasibility_v0_1_1 as base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--canonical-dir", default=None)
    args = ap.parse_args()

    repo_arg = Path(args.repo).expanduser()
    repo = repo_arg.resolve()
    base.require(repo.is_dir(), f"Repository does not exist: {repo}")
    canonical = base.resolve_canonical_dir(repo, args.canonical_dir)
    manifest = base.read_manifest(repo)

    print("=" * 96)
    print(" CMDO FIGURE 5 COMPARATOR-REPLAY FEASIBILITY AUDIT v0.1.2")
    print(" gzip-safe inspection + corrected U7 frozen schema")
    print("=" * 96)
    print(f"Repository argument : {repo_arg}")
    print(f"Repository resolved : {repo}")
    print(f"Canonical           : {canonical}")

    zips: dict[str, Path] = {}
    names: dict[str, list[str]] = {}

    print("\n[1] Canonical archive integrity")
    for archive in base.ARCHIVES:
        zp = canonical / archive
        base.require(zp.is_file(), f"Missing canonical archive: {zp}")
        base.require(archive in manifest, f"Archive absent from provenance manifest: {archive}")
        actual = base.sha256_file(zp).lower()
        expected = manifest[archive]
        base.require(actual == expected, f"SHA256 mismatch for {archive}: {actual} != {expected}")
        zips[archive] = zp
        names[archive] = base.zip_names(zp)
        print(f"  [OK] {archive}  {actual}")

    # ----------------------------- U5 ---------------------------------
    u5b = zips["StageU5B_Canonical_Records_v1.0.zip"]
    u5d = zips["StageU5D_Canonical_Records_v1.0.zip"]
    u5e = zips["StageU5E_Canonical_Records_v1.0.zip"]

    u5_raw_name = "StageU5D_Reconstructed_Target_Scores_And_Labels_v1.0.csv.gz"
    u5_desc_name = "StageU5B_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    u5_rep_name = "StageU5E_Pair_Complete_Replicates_v1.0.csv.gz"

    u5_raw_cols = base.header_columns(u5d, u5_raw_name)
    u5_desc_cols = base.header_columns(u5b, u5_desc_name)
    u5_rep_cols = base.header_columns(u5e, u5_rep_name)

    u5_has_raw = {"family", "target", "score", "label"}.issubset(u5_raw_cols)
    u5_has_desc = {
        "family", "target", "transport_auc", "support_gate", "transport_risk_proxy"
    }.issubset(u5_desc_cols)
    u5_has_rep = {"family", "target", "budget", "replicate", "method"}.issubset(u5_rep_cols)
    u5_exact = u5_has_raw and u5_has_desc and u5_has_rep

    # ----------------------------- U6 ---------------------------------
    u6 = zips["StageU6_Canonical_Records_v1.0.zip"]
    u6_desc_name = "StageU6_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    u6_rep_name = "StageU6_Pair_Complete_Witness_Replicates_v1.0.csv.gz"
    u6_truth_name = "StageU6_Target_True_Metrics_v1.0.csv"

    u6_desc_cols = base.header_columns(u6, u6_desc_name)
    u6_rep_cols = base.header_columns(u6, u6_rep_name)
    u6_truth_cols = base.header_columns(u6, u6_truth_name)
    u6_score_hash = "target_score_sha256" in u6_desc_cols
    u6_has_completed = {"true_auc", "transport_auc", "direct_full_auc"}.issubset(u6_rep_cols)
    u6_has_truth = {"family", "target", "true_auc"}.issubset(u6_truth_cols)
    u6_per_example_candidates = [
        n for n in names["StageU6_Canonical_Records_v1.0.zip"]
        if any(k in Path(n).name.lower() for k in [
            "scores_and_labels", "target_scores", "raw_scores", "outcomes_and_scores"
        ])
        and Path(n).suffix.lower() in {".csv", ".gz", ".npz", ".parquet"}
        and Path(n).name != u6_desc_name
    ]
    u6_has_raw = len(u6_per_example_candidates) > 0
    u6_pipeline = repo / base.U6_PIPELINE_REL
    u6_exact = u6_has_raw and bool(u6_desc_cols) and u6_has_completed and u6_has_truth
    u6_reconstruction_route = (
        (not u6_exact)
        and (not u6_has_raw)
        and u6_score_hash
        and u6_pipeline.is_file()
        and u6_has_completed
        and u6_has_truth
    )

    # ----------------------------- U7 ---------------------------------
    u7 = zips["StageU7_Canonical_Records_v1.0.zip"]
    u7_desc_name = "StageU7_PreOutcome_Clinical_Descriptors_v1.0.csv"
    u7_rep_name = "StageU7_Witness_Replicates_v1.0.csv.gz"
    u7_truth_name = "StageU7_Clinical_Strata_Truth_v1.0.csv"

    u7_desc_cols = base.header_columns(u7, u7_desc_name)
    u7_rep_cols = base.header_columns(u7, u7_rep_name)
    u7_truth_cols = base.header_columns(u7, u7_truth_name)
    u7_score_hash = "score_sha256" in u7_desc_cols

    # Frozen U7 result_row() writes true_metric and direct.
    u7_required_replicate_cols = {
        "stratum", "budget", "replicate", "metric", "true_metric", "direct"
    }
    u7_has_completed = u7_required_replicate_cols.issubset(u7_rep_cols)
    u7_has_truth = "eligible" in u7_truth_cols and any(
        c.startswith("true_") for c in u7_truth_cols
    )
    u7_per_example_candidates = [
        n for n in names["StageU7_Canonical_Records_v1.0.zip"]
        if any(k in Path(n).name.lower() for k in [
            "scores_and_labels", "target_scores", "raw_scores", "outcomes_and_scores"
        ])
        and Path(n).suffix.lower() in {".csv", ".gz", ".npz", ".parquet"}
        and Path(n).name != u7_desc_name
    ]
    u7_has_raw = len(u7_per_example_candidates) > 0
    u7_pipeline = repo / base.U7_PIPELINE_REL
    u7_exact = u7_has_raw and bool(u7_desc_cols) and u7_has_completed and u7_has_truth
    u7_reconstruction_route = (
        (not u7_exact)
        and (not u7_has_raw)
        and u7_score_hash
        and u7_pipeline.is_file()
        and u7_has_completed
        and u7_has_truth
    )

    rows = [
        {
            "regime": "U5_development",
            "targets_or_strata": 16,
            "per_example_scores_and_outcomes": u5_has_raw,
            "transport_descriptors": u5_has_desc,
            "completed_replicate_record": u5_has_rep,
            "score_hashes_for_reconstruction": True,
            "pipeline_route_present": True,
            "replay_state": base.replay_state(u5_exact, False),
            "next_action": "direct frozen comparator replay" if u5_exact else "repair U5 record inputs",
        },
        {
            "regime": "U6_independent_cross_domain",
            "targets_or_strata": 16,
            "per_example_scores_and_outcomes": u6_has_raw,
            "transport_descriptors": bool(u6_desc_cols),
            "completed_replicate_record": u6_has_completed,
            "score_hashes_for_reconstruction": u6_score_hash,
            "pipeline_route_present": u6_pipeline.is_file(),
            "replay_state": base.replay_state(u6_exact, u6_reconstruction_route),
            "next_action": (
                "direct frozen comparator replay" if u6_exact
                else "reconstruct scores/outcomes post-completion and require exact score-hash match"
                if u6_reconstruction_route
                else "cannot replay without additional provenance"
            ),
        },
        {
            "regime": "U7_natural_clinical",
            "targets_or_strata": 16,
            "per_example_scores_and_outcomes": u7_has_raw,
            "transport_descriptors": bool(u7_desc_cols),
            "completed_replicate_record": u7_has_completed,
            "score_hashes_for_reconstruction": u7_score_hash,
            "pipeline_route_present": u7_pipeline.is_file(),
            "replay_state": base.replay_state(u7_exact, u7_reconstruction_route),
            "next_action": (
                "direct frozen comparator replay" if u7_exact
                else "reconstruct scores/outcomes post-completion and require exact score-hash match"
                if u7_reconstruction_route
                else "cannot replay without additional provenance"
            ),
        },
    ]

    print("\n[2] Replay feasibility by regime")
    for r in rows:
        print(
            f"  {r['regime']:<29s} | raw={base.bool_text(r['per_example_scores_and_outcomes'])} "
            f"| descriptors={base.bool_text(r['transport_descriptors'])} "
            f"| replicates={base.bool_text(r['completed_replicate_record'])} "
            f"| {r['replay_state']}"
        )

    print("\n[3] U7 schema check")
    print("  Required frozen replicate columns:", sorted(u7_required_replicate_cols))
    print("  Detected frozen replicate columns:", u7_rep_cols)
    print(f"  completed_replicate_record={u7_has_completed}")

    all_exact = all(r["replay_state"] == "EXACT_CANONICAL_REPLAY_READY" for r in rows)
    reconstruction_needed = any(
        r["replay_state"] == "RECONSTRUCTION_ROUTE_PRESENT_NOT_VERIFIED" for r in rows
    )
    if all_exact:
        overall = "READY_FOR_EXACT_THREE_REGIME_COMPARATOR_REPLAY"
    elif reconstruction_needed:
        overall = "NOT_YET_READY_RECONSTRUCTION_REQUIRED"
    else:
        overall = "BLOCKED_BY_MISSING_REPLAY_INGREDIENTS"

    outdir = repo / "source_data" / "figure5_final_system" / "comparator_replay_feasibility"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_out = outdir / "CMDO_Figure5_Comparator_Replay_Feasibility_v0.1.2.csv"
    json_out = outdir / "CMDO_Figure5_Comparator_Replay_Feasibility_v0.1.2.json"

    pd.DataFrame(rows).to_csv(csv_out, index=False)
    result = {
        "schema": "CMDO_FIGURE5_COMPARATOR_REPLAY_FEASIBILITY_v0.1.2",
        "status": "FEASIBILITY_AUDIT_COMPLETE",
        "overall": overall,
        "candidate_family": [
            "PC_PAIRED_HOEFFDING",
            "PC_USTAT_MCDIARMID",
            "PC_DELONG",
            "PC_DELONG_VARGATE",
            "PC_PLUGIN",
            "PC_PLUGIN_VARGATE",
        ],
        "primary_metrics_if_replay_becomes_valid": {
            "pooled_gain_pct": "100*(1 - MAE_method/MAE_direct)",
            "worst_excess_mae": "max(MAE_method - MAE_direct) over frozen target-budget cells",
            "breadth": "fraction/count of frozen targets with positive pooled gain",
        },
        "regimes": rows,
        "guardrails": [
            "Do not report U6/U7 comparator results unless reconstructed target scores exactly match the frozen score hashes.",
            "Any U6/U7 comparator benchmark is post-completion and must not be described as prospective.",
            "Do not retrain or retune comparators based on U6/U7 outcomes.",
            "Do not alter frozen CMDO prospective U6/U7 results or the U10 verdict.",
        ],
        "bugfixes": [
            "v0.1.1: gzip-safe nested CSV.GZ inspection.",
            "v0.1.2: U7 completed-replicate schema uses true_metric, matching frozen result_row().",
        ],
        "u7_required_replicate_columns": sorted(u7_required_replicate_cols),
        "u7_detected_replicate_columns": u7_rep_cols,
        "files": {
            "csv": str(csv_out.relative_to(repo)).replace("\\", "/"),
        },
    }
    json_out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print("\n" + "=" * 96)
    print(" FIGURE 5 COMPARATOR-REPLAY FEASIBILITY AUDIT v0.1.2: COMPLETE")
    print("=" * 96)
    print(f"Overall: {overall}")
    print("Guardrail: U6/U7 competitor numbers remain unavailable until exact score-hash reconstruction succeeds.")
    print("Generated local files:")
    print(f"  {csv_out}")
    print(f"  {json_out}")


if __name__ == "__main__":
    main()
