#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Stage U5F — Final Observer Freeze and U6 Preregistration Framework v1.0

Transparent post-outcome method selection from the already sealed U5E
development results. U5E's official primary decision remains partial. This
stage applies an explicit lexicographic selection rule to the frozen U5E
candidate table and freezes one method for future independent U6 evaluation.

No new blind is accessed. Stage 12 remains prohibited.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

PROJECT = "Cross-Modal_Diagnostic_Observability"
STAGE = "StageU5F_Final_Observer_Freeze_And_U6_Preregistration_v1.0"

EXPECTED_U5E_FINAL = "cdfc1a03ebb4ae81d44f5deae459dffb9fc05bcc19915a778844b1fb01e1ea53"
EXPECTED_U5E_COMPLETE_FILE_SHA = "a685130915065105fa81f678cf3b73784153a8c6c45bab73c9778614a63ba578"
EXPECTED_U5E_STATES_SHA = "0dfa4b5d24a21dddf350c14cd778145c77ee3196cca9729ac0b0c5883c78283a"
EXPECTED_U5E_TARGETS_SHA = "8e4aff9d2b92cdbd06a3dd743b33db0d256fdaaa5711ccbcaf1ef24e7b2654f4"
EXPECTED_U5E_PIPELINE_SHA = "a0a488456a62e87744b95440bc7f7242585d6b33d7666b8d5d00e2f426d02205"

STRICT_CANDIDATES = ["PC_PAIRED_HOEFFDING", "PC_USTAT_MCDIARMID"]
EXPECTED_SELECTED_METHOD = "PC_PAIRED_HOEFFDING"


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


def candidate_table(states: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    summary = (
        states.groupby("method", as_index=False)
        .agg(
            pooled_mae=("mae", "mean"),
            pooled_direct_mae=("direct_full_mae", "mean"),
            worst_target_budget_regret=("mae_regret_vs_full_direct", "max"),
            mean_weight=("mean_weight", "mean"),
            fallback_rate=("fallback_rate", "mean"),
            mean_simultaneous_coverage=("simultaneous_coverage", "mean"),
            minimum_simultaneous_coverage=("simultaneous_coverage", "min"),
            minimum_block_no_harm_rate=("block_no_harm_rate", "min"),
            maximum_identity_residual=("maximum_identity_residual", "max"),
        )
    )
    summary["pooled_gain"] = 1.0 - summary["pooled_mae"] / summary["pooled_direct_mae"]

    positive = (
        targets.assign(positive=targets["gain_vs_full_direct"] > 0)
        .groupby("method", as_index=False)
        .agg(
            positive_targets=("positive", "sum"),
            target_count=("positive", "size"),
            minimum_target_gain=("gain_vs_full_direct", "min"),
            median_target_gain=("gain_vs_full_direct", "median"),
        )
    )
    summary = summary.merge(positive, on="method", how="left")
    summary["strict_candidate"] = summary["method"].isin(STRICT_CANDIDATES)
    summary["eligible"] = (
        summary["strict_candidate"]
        & (summary["maximum_identity_residual"] < 1e-12)
        & (summary["mean_simultaneous_coverage"] >= 0.99)
        & (summary["minimum_simultaneous_coverage"] >= 0.98)
        & (summary["minimum_block_no_harm_rate"] >= 0.999)
        & (summary["pooled_gain"] > 0)
        & (summary["worst_target_budget_regret"] <= 0.005)
        & (summary["positive_targets"] >= 9)
        & (summary["mean_weight"] > 0)
    )
    return summary


def select_candidate(table: pd.DataFrame) -> Dict[str, Any]:
    eligible = table[table["eligible"]].copy()
    if len(eligible) == 0:
        raise RuntimeError("No strict U5E candidate satisfies the U5F eligibility rule.")
    # Transparent post-outcome lexicographic selection:
    # 1) maximise pooled gain among certified eligible candidates;
    # 2) minimise worst target-budget regret;
    # 3) maximise positive target count;
    # 4) deterministic method-name tie break.
    eligible = eligible.sort_values(
        [
            "pooled_gain",
            "worst_target_budget_regret",
            "positive_targets",
            "method",
        ],
        ascending=[False, True, False, True],
    )
    row = eligible.iloc[0]
    return {
        "selected_method": str(row["method"]),
        "pooled_mae": float(row["pooled_mae"]),
        "pooled_direct_mae": float(row["pooled_direct_mae"]),
        "pooled_gain": float(row["pooled_gain"]),
        "worst_target_budget_regret": float(row["worst_target_budget_regret"]),
        "mean_weight": float(row["mean_weight"]),
        "positive_targets": int(row["positive_targets"]),
        "target_count": int(row["target_count"]),
        "mean_simultaneous_coverage": float(row["mean_simultaneous_coverage"]),
        "minimum_simultaneous_coverage": float(row["minimum_simultaneous_coverage"]),
        "minimum_block_no_harm_rate": float(row["minimum_block_no_harm_rate"]),
        "fallback_rate": float(row["fallback_rate"]),
    }


def frozen_spec(selection: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "observer_name": "CMDO Pair-Complete Opposite-Block Hoeffding Observer",
        "observer_id": "PC_PAIRED_HOEFFDING",
        "selection_status": (
            "TRANSPARENT_POST_OUTCOME_SELECTION_FOR_FUTURE_INDEPENDENT_VALIDATION"
        ),
        "witness_budgets": [8, 16, 32, 64, 128],
        "balanced_sampling": True,
        "partition": (
            "Split positive and negative witness samples independently into "
            "equal A/B halves."
        ),
        "pair_blocks": ["AA", "AB", "BA", "BB"],
        "opposite_block_map": {
            "AA": "BB",
            "BB": "AA",
            "AB": "BA",
            "BA": "AB",
        },
        "direct_identity": (
            "The arithmetic mean of AA, AB, BA and BB block AUCs equals the "
            "full balanced-witness AUC exactly."
        ),
        "bias_sensor": (
            "For each estimation block, use matched positive-negative "
            "comparisons from its sample-disjoint opposite block."
        ),
        "confidence_rule": {
            "delta_total": 0.10,
            "delta_per_block": 0.025,
            "radius": "sqrt(log(2/delta_per_block)/(2*n_paired_sensor))",
            "bias_upper_sq": "min(1, abs(sensor_auc-transport_auc)+radius)^2",
        },
        "weight_rule": (
            "support_gate * min(0.35, V_block / "
            "(V_block + bias_upper_sq + 8*transport_risk_proxy + 1e-12))"
        ),
        "max_weight": 0.35,
        "risk_coefficient": 8.0,
        "variance_gate": False,
        "aggregation": (
            "Average the four blockwise shrinkage estimates with equal weight."
        ),
        "zero_weight_fallback": "Exactly full direct AUC.",
        "development_selection_metrics": selection,
        "permitted_change_before_u6": "NONE",
    }


def u6_preregistration_text(spec_sha: str, selection: Dict[str, Any]) -> str:
    return f"""CMDO STAGE U6 — INDEPENDENT PAIR-COMPLETE OBSERVER RESERVE
PREREGISTRATION FRAMEWORK v1.0

STATUS
FRAMEWORK ONLY. TARGET ROSTER AND ACQUISITION MANIFEST MUST BE SEALED IN A
SEPARATE OUTCOME-BLIND RECORD BEFORE ANY U6 TARGET LABEL IS ACCESSED.

1. FROZEN OBSERVER

Observer: PC_PAIRED_HOEFFDING
Frozen specification SHA-256: {spec_sha}

No variance gate.
No parameter tuning.
No candidate switching.
No reuse of U4/U5 development targets as primary U6 targets.

2. REQUIRED RESERVE

At least 16 new target environments across at least 3 families.
At least one clinically credible medical family.
Target labels must remain inaccessible until source-only descriptors,
transport estimates, score hashes, target roster and this observer identity
are sealed.

3. PRIMARY EVIDENCE DOMAINS

A. Structural integrity
- exact four-block/full-direct identity;
- exact observer hash;
- exact target roster and acquisition hashes.

B. Certification
- mean simultaneous opposite-block coverage >= 0.90;
- minimum target-budget simultaneous coverage >= 0.85;
- minimum blockwise no-harm geometry rate >= 0.999.

C. Full-direct tail safety
- worst target-budget MAE regret versus full direct <= 0.005;
- worst family-level MAE regret <= 0.005.

D. Same-budget utility
- pooled MAE no worse than full direct;
- at least 9 of 16 targets improve;
- mean transport weight > 0.

E. Mechanistic observability
- sentinel bias estimate versus true transport error Spearman >= 0.75.

4. DECISION STRUCTURE

U6 will not collapse all evidence into a single arbitrary percentage-gain
threshold. It will report separate outcomes for:
- identifiability and bias observability;
- finite-sample certification;
- full-direct tail safety;
- same-budget efficiency.

Final observer confirmation requires all primary safety and integrity gates,
pooled non-inferiority, and selective utility. Efficiency magnitude is reported
with confidence intervals rather than an arbitrary 10% pass threshold.

5. DEVELOPMENT HISTORY

U5E official primary method PC_DELONG_VARGATE remained a partial result.
U5F transparently selected PC_PAIRED_HOEFFDING from the frozen U5E candidate
set for future independent validation because it was the certified eligible
candidate with the largest pooled gain.

U5E development metrics for the frozen observer:
- pooled MAE: {selection['pooled_mae']:.9f}
- full-direct MAE: {selection['pooled_direct_mae']:.9f}
- pooled gain: {selection['pooled_gain']:.9f}
- worst target-budget regret: {selection['worst_target_budget_regret']:.9f}
- positive targets: {selection['positive_targets']}/{selection['target_count']}
- mean simultaneous coverage: {selection['mean_simultaneous_coverage']:.9f}
- minimum simultaneous coverage: {selection['minimum_simultaneous_coverage']:.9f}
- minimum block no-harm rate: {selection['minimum_block_no_harm_rate']:.9f}

These are development results, not U6 confirmation.

6. GOVERNANCE

New blind accessed in U5F: FALSE.
U6 target-label access authorised by this framework: FALSE.
Stage 12 authorised: FALSE.
"""


def durable_manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    excluded = {
        "StageU5F_Durable_Manifest_v1.0.csv",
        "StageU5F_Canonical_Records_v1.0.zip",
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
    protocol_path = Path(os.environ["CMDO_U5F_PROTOCOL_PATH"]).resolve()
    auth_path = Path(os.environ["CMDO_U5F_AUTH_PATH"]).resolve()
    theory_path = Path(os.environ["CMDO_U5F_THEORY_PATH"]).resolve()
    pipeline_path = Path(__file__).resolve()

    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    release_ok = bool(
        auth.get("u5f_protocol_sha256") == sha256_file(protocol_path)
        and auth.get("u5f_pipeline_sha256") == sha256_file(pipeline_path)
        and auth.get("u5f_theory_sha256") == sha256_file(theory_path)
        and auth.get("parent_u5e_final_record_sha256") == EXPECTED_U5E_FINAL
        and auth.get("new_blind_access_authorised") is False
        and auth.get("stage12_authorised") is False
    )
    if not release_ok:
        raise RuntimeError("U5F release integrity failed.")

    root = locate_project_root()
    cross_modal = root / "06_Data_Records" / "Cross_Modal"
    u5e_dir = cross_modal / "StageU5E_Pair_Complete_Cross_Fitted_Observer_v1.0"
    complete_path = u5e_dir / "StageU5E_Complete_v1.0.json"
    states_path = u5e_dir / "StageU5E_Pair_Complete_State_Results_v1.0.csv"
    targets_path = u5e_dir / "StageU5E_Target_Summary_v1.0.csv"
    u5e_pipeline_path = u5e_dir / "StageU5E_Pair_Complete_Cross_Fitted_Observer_v1.0.py"

    complete = json.loads(complete_path.read_text(encoding="utf-8"))
    parent_ok = bool(
        complete.get("final_record_sha256") == EXPECTED_U5E_FINAL
        and sha256_file(complete_path) == EXPECTED_U5E_COMPLETE_FILE_SHA
        and sha256_file(states_path) == EXPECTED_U5E_STATES_SHA
        and sha256_file(targets_path) == EXPECTED_U5E_TARGETS_SHA
        and sha256_file(u5e_pipeline_path) == EXPECTED_U5E_PIPELINE_SHA
        and complete.get("new_blind_accessed") is False
        and complete.get("stage12_authorised") is False
    )
    if not parent_ok:
        raise RuntimeError("U5F parent U5E integrity failed.")

    output_dir = cross_modal / STAGE
    if output_dir.exists():
        completed = output_dir / "StageU5F_Complete_v1.0.json"
        if completed.exists():
            raise RuntimeError("Completed U5F exists; rerun is prohibited.")
        backup = output_dir.with_name(
            output_dir.name + "_PARTIAL_" + datetime.now().strftime("%Y%m%dT%H%M%S")
        )
        output_dir.rename(backup)
    output_dir.mkdir(parents=True, exist_ok=False)

    for source in [protocol_path, auth_path, theory_path, pipeline_path]:
        shutil.copy2(source, output_dir / source.name)

    states = pd.read_csv(states_path)
    targets = pd.read_csv(targets_path)
    candidates = candidate_table(states, targets)
    candidates.to_csv(
        output_dir / "StageU5F_Candidate_Selection_Audit_v1.0.csv",
        index=False,
    )

    selection = select_candidate(candidates)
    if selection["selected_method"] != EXPECTED_SELECTED_METHOD:
        raise RuntimeError(
            f"Unexpected selected method: {selection['selected_method']}"
        )

    spec = frozen_spec(selection)
    spec_text = json.dumps(spec, indent=2, sort_keys=True)
    spec_path = output_dir / "StageU5F_Frozen_Observer_Specification_v1.0.json"
    spec_path.write_text(spec_text, encoding="utf-8")
    spec_sha = sha256_file(spec_path)

    prereg_path = output_dir / "StageU6_Independent_Reserve_Preregistration_Framework_v1.0.txt"
    prereg_path.write_text(
        u6_preregistration_text(spec_sha, selection),
        encoding="utf-8",
    )

    gates = pd.DataFrame(
        [
            (
                "release_and_parent_integrity",
                bool(release_ok and parent_ok),
                str(release_ok and parent_ok),
            ),
            (
                "u5e_official_partial_decision_preserved",
                "PARTIAL_PAIR_COMPLETE_OBSERVER_SUPPORT" in str(complete.get("decision", "")),
                str(complete.get("decision")),
            ),
            (
                "strict_candidate_set_fixed",
                set(STRICT_CANDIDATES).issubset(set(candidates["method"])),
                ",".join(STRICT_CANDIDATES),
            ),
            (
                "eligible_certified_candidate_exists",
                bool(candidates["eligible"].any()),
                f"eligible={int(candidates['eligible'].sum())}",
            ),
            (
                "lexicographic_selection_reproducible",
                selection["selected_method"] == EXPECTED_SELECTED_METHOD,
                selection["selected_method"],
            ),
            (
                "selected_pooled_utility",
                selection["pooled_gain"] > 0,
                f"gain={selection['pooled_gain']:.6f}",
            ),
            (
                "selected_tail_safety",
                selection["worst_target_budget_regret"] <= 0.005,
                f"worst={selection['worst_target_budget_regret']:.6f}",
            ),
            (
                "selected_target_breadth",
                selection["positive_targets"] >= 9,
                f"positive={selection['positive_targets']}/{selection['target_count']}",
            ),
            (
                "selected_certification",
                (
                    selection["mean_simultaneous_coverage"] >= 0.99
                    and selection["minimum_simultaneous_coverage"] >= 0.98
                    and selection["minimum_block_no_harm_rate"] >= 0.999
                ),
                (
                    f"mean_cov={selection['mean_simultaneous_coverage']:.6f};"
                    f"min_cov={selection['minimum_simultaneous_coverage']:.6f};"
                    f"no_harm={selection['minimum_block_no_harm_rate']:.6f}"
                ),
            ),
            ("new_blind_accessed", True, "False"),
            ("u6_target_label_access_authorised", True, "False"),
            ("stage12_authorised", True, "False"),
        ],
        columns=["gate", "passed", "observed"],
    )
    gates.to_csv(output_dir / "StageU5F_Gate_Table_v1.0.csv", index=False)

    core = gates[
        ~gates["gate"].isin(
            [
                "new_blind_accessed",
                "u6_target_label_access_authorised",
                "stage12_authorised",
            ]
        )
    ]
    if bool(core["passed"].all()):
        decision = (
            "SEAL_STAGEU5F_PC_PAIRED_HOEFFDING_OBSERVER_FROZEN_"
            "AUTHORISE_U6_RESERVE_DESIGN_AND_OUTCOME_BLIND_PREREGISTRATION_ONLY_"
            "NO_NEW_BLIND_STAGE12_PROHIBITED"
        )
    else:
        decision = (
            "SEAL_STAGEU5F_OBSERVER_FREEZE_NOT_AUTHORISED_RETAIN_ALL_RESULTS_"
            "NO_NEW_BLIND_STAGE12_PROHIBITED"
        )

    record_pre = {
        "stage": STAGE,
        "created_utc": utc_now(),
        "decision": decision,
        "parent_u5e_final_record_sha256": EXPECTED_U5E_FINAL,
        "u5e_official_decision_preserved": complete.get("decision"),
        "selection_status": "TRANSPARENT_POST_OUTCOME_METHOD_SELECTION",
        "selection_rule": (
            "Among strict certified eligible U5E candidates, maximise pooled "
            "gain; then minimise worst target-budget regret; then maximise "
            "positive target count; then deterministic method-name tie break."
        ),
        "selection": selection,
        "frozen_observer_specification_sha256": spec_sha,
        "u6_preregistration_framework_sha256": sha256_file(prereg_path),
        "new_blind_accessed": False,
        "u6_target_label_access_authorised": False,
        "stage12_authorised": False,
        "runtime_seconds": time.time() - started,
    }
    final_sha = sha256_text(canonical_json(record_pre))
    record = dict(record_pre)
    record["final_record_sha256"] = final_sha
    (output_dir / "StageU5F_Complete_v1.0.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = f"""# Stage U5F — Observer Freeze

Official U5E decision preserved:
`{complete.get('decision')}`

Selected future observer:
`{selection['selected_method']}`

Development evidence:
- pooled MAE: {selection['pooled_mae']:.9f}
- full-direct MAE: {selection['pooled_direct_mae']:.9f}
- pooled gain: {selection['pooled_gain']:.6%}
- worst target-budget regret: {selection['worst_target_budget_regret']:.9f}
- positive targets: {selection['positive_targets']}/{selection['target_count']}
- mean coverage: {selection['mean_simultaneous_coverage']:.6f}
- minimum coverage: {selection['minimum_simultaneous_coverage']:.6f}
- minimum block no-harm rate: {selection['minimum_block_no_harm_rate']:.6f}
- mean weight: {selection['mean_weight']:.6f}

This is transparent method selection for future independent confirmation, not
a retrospective conversion of U5E into a prospective success.
"""
    (output_dir / "StageU5F_Observer_Freeze_Report_v1.0.md").write_text(
        report,
        encoding="utf-8",
    )

    manifest = durable_manifest(output_dir)
    manifest.to_csv(
        output_dir / "StageU5F_Durable_Manifest_v1.0.csv",
        index=False,
    )
    zip_path = output_dir / "StageU5F_Canonical_Records_v1.0.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(path, arcname=str(path.relative_to(output_dir)))
    zip_sha = sha256_file(zip_path)
    (output_dir / "StageU5F_Canonical_Zip_Commit_v1.0.json").write_text(
        json.dumps(
            {
                "stage": STAGE,
                "final_record_sha256": final_sha,
                "canonical_zip_sha256": zip_sha,
                "committed_utc": utc_now(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("\n========== STAGE U5F COMPLETE ==========")
    print("Decision:", decision)
    print("U5E official decision preserved:", complete.get("decision"))
    print("Selected observer:", selection["selected_method"])
    print(
        "Pooled MAE / direct / gain:",
        selection["pooled_mae"],
        selection["pooled_direct_mae"],
        selection["pooled_gain"],
    )
    print(
        "Worst regret / positive targets / mean weight:",
        selection["worst_target_budget_regret"],
        selection["positive_targets"],
        selection["mean_weight"],
    )
    print(
        "Coverage mean / minimum / block no-harm:",
        selection["mean_simultaneous_coverage"],
        selection["minimum_simultaneous_coverage"],
        selection["minimum_block_no_harm_rate"],
    )
    print("New blind accessed:", False)
    print("U6 target-label access authorised:", False)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", final_sha)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gates.to_string(index=False))


if __name__ == "__main__":
    main()

