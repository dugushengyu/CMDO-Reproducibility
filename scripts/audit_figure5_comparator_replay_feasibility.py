#!/usr/bin/env python3
"""
CMDO Figure 5 comparator-replay feasibility audit
=================================================

Purpose
-------
Determine, without running a new benchmark, whether the frozen canonical
records contain enough information to replay the U5E comparator family on:

  * U5 development targets,
  * U6 independent cross-domain targets,
  * U7 natural clinical strata.

The audit distinguishes three states:

  EXACT_CANONICAL_REPLAY_READY
      Per-example target scores and outcomes plus frozen transport descriptors
      are present in the canonical records, so the comparator family can be
      replayed without reconstructing the deployed model outputs.

  RECONSTRUCTION_ROUTE_PRESENT_NOT_VERIFIED
      The canonical record contains score hashes, frozen protocol/pipeline
      information and completed observer results, but not the per-example
      score/outcome arrays required by alternative comparator algorithms.
      A separate post-completion reconstruction would have to reproduce the
      original scores exactly and verify them against the frozen score hashes.

  NOT_REPLAYABLE_FROM_CURRENT_RECORDS
      Neither exact replay ingredients nor a verifiable reconstruction route
      were found.

This script does NOT run any comparator, does NOT alter prospective U6/U7
status, and does NOT infer missing results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import pandas as pd


ARCHIVES = [
    "StageU5B_Canonical_Records_v1.0.zip",
    "StageU5D_Canonical_Records_v1.0.zip",
    "StageU5E_Canonical_Records_v1.0.zip",
    "StageU6_Canonical_Records_v1.0.zip",
    "StageU7_Canonical_Records_v1.0.zip",
]

U6_PIPELINE_REL = Path(
    "legacy/original_authoritative/u6/"
    "StageU6_Independent_Pair_Complete_Observer_Reserve_v1.0.py"
)
U7_PIPELINE_REL = Path(
    "legacy/original_authoritative/u7/"
    "StageU7_General_Performance_Observability_And_Natural_Clinical_Deployment_v1.0.py"
)


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

    hits = []
    for p in repo.rglob("StageU7_Canonical_Records_v1.0.zip"):
        if p.is_file():
            hits.append(p.parent.resolve())
    for p in sorted(set(hits)):
        if all((p / a).is_file() for a in ARCHIVES):
            return p

    raise RuntimeError(
        "Could not resolve canonicalRecordDir. Set CMDO_CANONICAL_RECORD_DIR, "
        "config/local_paths.json, or pass --canonical-dir."
    )


def read_manifest(repo: Path) -> dict[str, str]:
    p = repo / "provenance" / "canonical_archives_manifest.csv"
    require(p.is_file(), f"Missing provenance manifest: {p}")
    df = pd.read_csv(p)
    require({"archive", "sha256"}.issubset(df.columns), "Malformed archive manifest")
    return {str(r.archive): str(r.sha256).lower() for r in df.itertuples(index=False)}


def zip_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path, "r") as zf:
        return zf.namelist()


def find_member(names: list[str], basename: str) -> str | None:
    hits = [n for n in names if Path(n).name == basename]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise RuntimeError(f"Duplicate {basename} entries in canonical archive")
    return None


def read_csv_member(zip_path: Path, basename: str) -> pd.DataFrame | None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        member = find_member(names, basename)
        if member is None:
            return None
        with zf.open(member, "r") as f:
            return pd.read_csv(f)


def header_columns(zip_path: Path, basename: str) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        member = find_member(zf.namelist(), basename)
        if member is None:
            return []
        with zf.open(member, "r") as f:
            return list(pd.read_csv(f, nrows=0).columns)


def bool_text(v: bool) -> str:
    return "YES" if v else "NO"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--canonical-dir", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    require(repo.is_dir(), f"Repository does not exist: {repo}")
    canonical = resolve_canonical_dir(repo, args.canonical_dir)
    manifest = read_manifest(repo)

    print("=" * 96)
    print(" CMDO FIGURE 5 COMPARATOR-REPLAY FEASIBILITY AUDIT")
    print(" exact canonical replay vs post-completion score reconstruction")
    print("=" * 96)
    print(f"Repository : {repo}")
    print(f"Canonical  : {canonical}")

    zips: dict[str, Path] = {}
    names: dict[str, list[str]] = {}

    print("\n[1] Canonical archive integrity")
    for archive in ARCHIVES:
        zp = canonical / archive
        require(zp.is_file(), f"Missing canonical archive: {zp}")
        require(archive in manifest, f"Archive absent from provenance manifest: {archive}")
        actual = sha256_file(zp).lower()
        expected = manifest[archive]
        require(actual == expected, f"SHA256 mismatch for {archive}")
        zips[archive] = zp
        names[archive] = zip_names(zp)
        print(f"  [OK] {archive}  {actual}")

    # ------------------------------------------------------------------
    # U5: exact replay ingredients are expected across U5B/U5D/U5E.
    # ------------------------------------------------------------------
    u5b = zips["StageU5B_Canonical_Records_v1.0.zip"]
    u5d = zips["StageU5D_Canonical_Records_v1.0.zip"]
    u5e = zips["StageU5E_Canonical_Records_v1.0.zip"]

    u5_raw_name = "StageU5D_Reconstructed_Target_Scores_And_Labels_v1.0.csv.gz"
    u5_desc_name = "StageU5B_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    u5_rep_name = "StageU5E_Pair_Complete_Replicates_v1.0.csv.gz"

    u5_raw_cols = header_columns(u5d, u5_raw_name)
    u5_desc_cols = header_columns(u5b, u5_desc_name)
    u5_rep_cols = header_columns(u5e, u5_rep_name)

    u5_has_raw = {"family", "target", "score", "label"}.issubset(u5_raw_cols)
    u5_has_desc = {"family", "target", "transport_auc", "support_gate", "transport_risk_proxy"}.issubset(u5_desc_cols)
    u5_has_rep = {"family", "target", "budget", "replicate", "method"}.issubset(u5_rep_cols)
    u5_exact = u5_has_raw and u5_has_desc and u5_has_rep

    # ------------------------------------------------------------------
    # U6: assess whether canonical archive contains per-example score/outcome
    # arrays. Existing replicate-level summaries are not sufficient to derive
    # alternative opposite-block sensors or DeLong/plugin weights.
    # ------------------------------------------------------------------
    u6 = zips["StageU6_Canonical_Records_v1.0.zip"]
    u6_desc_name = "StageU6_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    u6_rep_name = "StageU6_Pair_Complete_Witness_Replicates_v1.0.csv.gz"
    u6_truth_name = "StageU6_Target_True_Metrics_v1.0.csv"

    u6_desc_cols = header_columns(u6, u6_desc_name)
    u6_rep_cols = header_columns(u6, u6_rep_name)
    u6_truth_cols = header_columns(u6, u6_truth_name)
    u6_score_hash = "target_score_sha256" in u6_desc_cols
    u6_has_completed = {"true_auc", "transport_auc", "direct_full_auc"}.issubset(u6_rep_cols)
    u6_has_truth = {"family", "target", "true_auc"}.issubset(u6_truth_cols)

    u6_per_example_candidates = [
        n for n in names["StageU6_Canonical_Records_v1.0.zip"]
        if any(k in Path(n).name.lower() for k in ["scores_and_labels", "target_scores", "raw_scores", "outcomes_and_scores"])
        and Path(n).suffix.lower() in {".csv", ".gz", ".npz", ".parquet"}
    ]
    # Descriptor files contain hashes, not arrays; exclude them explicitly.
    u6_per_example_candidates = [
        n for n in u6_per_example_candidates
        if Path(n).name != u6_desc_name
    ]
    u6_has_raw = len(u6_per_example_candidates) > 0
    u6_pipeline = repo / U6_PIPELINE_REL
    u6_reconstruction_route = (
        (not u6_has_raw)
        and u6_score_hash
        and u6_pipeline.is_file()
        and u6_has_completed
        and u6_has_truth
    )

    # ------------------------------------------------------------------
    # U7.
    # ------------------------------------------------------------------
    u7 = zips["StageU7_Canonical_Records_v1.0.zip"]
    u7_desc_name = "StageU7_PreOutcome_Clinical_Descriptors_v1.0.csv"
    u7_rep_name = "StageU7_Witness_Replicates_v1.0.csv.gz"
    u7_truth_name = "StageU7_Clinical_Strata_Truth_v1.0.csv"

    u7_desc_cols = header_columns(u7, u7_desc_name)
    u7_rep_cols = header_columns(u7, u7_rep_name)
    u7_truth_cols = header_columns(u7, u7_truth_name)
    u7_score_hash = "score_sha256" in u7_desc_cols
    u7_has_completed = {"stratum", "budget", "replicate", "metric", "true_value", "direct"}.issubset(u7_rep_cols)
    # Older/current schema uses truth column names beginning true_. The presence
    # of eligible plus true metric columns is enough to confirm completed truth summaries.
    u7_has_truth = "eligible" in u7_truth_cols and any(c.startswith("true_") for c in u7_truth_cols)

    u7_per_example_candidates = [
        n for n in names["StageU7_Canonical_Records_v1.0.zip"]
        if any(k in Path(n).name.lower() for k in ["scores_and_labels", "target_scores", "raw_scores", "outcomes_and_scores"])
        and Path(n).suffix.lower() in {".csv", ".gz", ".npz", ".parquet"}
    ]
    u7_per_example_candidates = [
        n for n in u7_per_example_candidates
        if Path(n).name != u7_desc_name
    ]
    u7_has_raw = len(u7_per_example_candidates) > 0
    u7_pipeline = repo / U7_PIPELINE_REL
    u7_reconstruction_route = (
        (not u7_has_raw)
        and u7_score_hash
        and u7_pipeline.is_file()
        and u7_has_completed
        and u7_has_truth
    )

    def state(exact: bool, reconstruction: bool) -> str:
        if exact:
            return "EXACT_CANONICAL_REPLAY_READY"
        if reconstruction:
            return "RECONSTRUCTION_ROUTE_PRESENT_NOT_VERIFIED"
        return "NOT_REPLAYABLE_FROM_CURRENT_RECORDS"

    rows = [
        {
            "regime": "U5_development",
            "targets_or_strata": 16,
            "per_example_scores_and_outcomes": u5_has_raw,
            "transport_descriptors": u5_has_desc,
            "completed_replicate_record": u5_has_rep,
            "score_hashes_for_reconstruction": True,
            "pipeline_route_present": True,
            "replay_state": state(u5_exact, False),
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
            "replay_state": state(u6_has_raw, u6_reconstruction_route),
            "next_action": (
                "direct frozen comparator replay" if u6_has_raw
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
            "replay_state": state(u7_has_raw, u7_reconstruction_route),
            "next_action": (
                "direct frozen comparator replay" if u7_has_raw
                else "reconstruct scores/outcomes post-completion and require exact score-hash match"
                if u7_reconstruction_route
                else "cannot replay without additional provenance"
            ),
        },
    ]

    print("\n[2] Replay feasibility by regime")
    for r in rows:
        print(
            f"  {r['regime']:<29s} | raw={bool_text(r['per_example_scores_and_outcomes'])} "
            f"| descriptors={bool_text(r['transport_descriptors'])} "
            f"| replicates={bool_text(r['completed_replicate_record'])} "
            f"| {r['replay_state']}"
        )

    print("\n[3] Scientific interpretation")
    if u5_exact:
        print("  U5: exact head-to-head comparator replay is supported by frozen canonical inputs.")
    else:
        print("  U5: exact head-to-head replay is NOT supported by the detected canonical inputs.")

    if not u6_has_raw:
        print("  U6: canonical archive preserves score hashes and completed CMDO results, but not the per-example score/outcome arrays needed to derive alternative comparator weights.")
    if u6_reconstruction_route:
        print("      A post-completion reconstruction route exists in principle; it must reproduce every frozen target score hash exactly before any comparator result is accepted.")

    if not u7_has_raw:
        print("  U7: canonical archive preserves score hashes and completed clinical summaries, but not the per-example score/outcome arrays needed for alternative comparator replay.")
    if u7_reconstruction_route:
        print("      A post-completion reconstruction route exists in principle; exact frozen score-hash matching is mandatory before benchmarking.")

    # Do not call the cross-regime benchmark ready unless all three are exact.
    all_exact = all(r["replay_state"] == "EXACT_CANONICAL_REPLAY_READY" for r in rows)
    reconstruction_needed = any(r["replay_state"] == "RECONSTRUCTION_ROUTE_PRESENT_NOT_VERIFIED" for r in rows)

    if all_exact:
        overall = "READY_FOR_EXACT_THREE_REGIME_COMPARATOR_REPLAY"
    elif reconstruction_needed:
        overall = "NOT_YET_READY_RECONSTRUCTION_REQUIRED"
    else:
        overall = "BLOCKED_BY_MISSING_REPLAY_INGREDIENTS"

    outdir = repo / "source_data" / "figure5_final_system" / "comparator_replay_feasibility"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_out = outdir / "CMDO_Figure5_Comparator_Replay_Feasibility_v0.1.csv"
    json_out = outdir / "CMDO_Figure5_Comparator_Replay_Feasibility_v0.1.json"

    pd.DataFrame(rows).to_csv(csv_out, index=False)
    result = {
        "schema": "CMDO_FIGURE5_COMPARATOR_REPLAY_FEASIBILITY_v0.1",
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
            "Do not alter the frozen CMDO prospective U6/U7 results or U10 verdict.",
        ],
        "files": {
            "csv": str(csv_out.relative_to(repo)).replace("\\", "/"),
        },
    }
    json_out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print("\n" + "=" * 96)
    print(" FIGURE 5 COMPARATOR-REPLAY FEASIBILITY AUDIT: COMPLETE")
    print("=" * 96)
    print(f"Overall: {overall}")
    print("Guardrail: U6/U7 competitor numbers remain unavailable until exact score-hash reconstruction succeeds.")
    print("Generated local files:")
    print(f"  {csv_out}")
    print(f"  {json_out}")


if __name__ == "__main__":
    main()
