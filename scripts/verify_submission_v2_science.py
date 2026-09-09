#!/usr/bin/env python3
"""Static scientific-integrity checks for the CMDO submission-v2 freeze.

This verifier is intentionally independent of MATLAB. It checks frozen
source/provenance records, submission-v2 display wiring and claim boundaries
before the graphical fresh-clone acceptance run. It does not re-run sealed
prospective stages.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_EICU_CODE_SHA = "5f72a5aba7650bc7ac51ac48c72db8e5d7ede19d856a75d29b8367387da43352"
EXPECTED_EICU_ZIP_SHA = "815bbc9a575a3e2eca5e227ad24d6d4f4e210eedac086f09287dac22c950b701"
EXPECTED_U10_VERDICT = "MECHANISM_NOT_CONFIRMED"
EXPECTED_EICU_VERDICT = "INTEGRITY_SUPPORTED_EMPIRICAL_SAFETY_NOT_CONFIRMED"
EXPECTED_185_COUNTS = {"U6": 80, "U7": 80, "U8": 12, "U9A": 9, "U9B": 4}
EXPECTED_FAILED_GATES = {
    "hospital_breadth",
    "stable_decision_cost_reduction",
    "max_budget_correct_resolution_noninferiority",
}
EXPECTED_PCC_SHA256 = {
    "matlab/submission_figures/Figure1_Evidential_Order_PCC.m": "dcdf139ad12e0f0bc237744f30ad19f3208e9b50f3add4cd19eeec729101be8d",
    "source_data/pcc/CMDO_185_realized_projection.csv": "90d391bb0a2656ed780f516deb3d85037620a150cca94e1af05fcc0c97a902d3",
    "source_data/pcc/PCC_frontier_classified.csv": "f707921c346375d99ea1520d3f5cb756091882c50714399bf865f44e16d8bc7d",
}
REQUIRED_SUBMISSION_V2_FILES = [
    "RUN_SUBMISSION_V2_FIGURES.m",
    "matlab/submission_figures/Figure1_Evidential_Order_PCC.m",
    "matlab/submission_figures/Figure2_IDENTIFY_Validation.m",
    "matlab/submission_figures/Figure3_REUSE_Refined.m",
    "matlab/submission_figures/Figure4_CERTIFY.m",
    "matlab/submission_figures/Figure5_PRESERVE_PCC.m",
    "matlab/submission_figures/ED1_OutcomeFreeBoundary_v9.m",
    "matlab/submission_figures/ED2_IntegrityControls_v2.m",
    "matlab/submission_figures/ED3_RobustnessEfficiency_v1.m",
    "source_data/pcc/CMDO_185_realized_projection.csv",
    "source_data/pcc/PCC_frontier_classified.csv",
    "source_data/pcc/PCC_scaling_summary_v12.csv",
    "source_data/pcc/CMDO_U9_REUSE_PRESERVE_bridge.csv",
]


def fail(msg: str) -> None:
    raise AssertionError(msg)


def close(a: float, b: float, tol: float = 1e-10) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"missing required CSV: {path.relative_to(ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def assert_185_stage_counts(rows: list[dict[str, str]], label: str) -> None:
    if len(rows) != 185:
        fail(f"{label} changed: expected 185 rows, found {len(rows)}")
    if not rows or "stage" not in rows[0]:
        fail(f"{label} has no stage column")
    counts = Counter(r["stage"].strip() for r in rows)
    for stage, n in EXPECTED_185_COUNTS.items():
        if counts.get(stage, 0) != n:
            fail(f"{label} stage count changed for {stage}: expected {n}, found {counts.get(stage, 0)}")
    unexpected = {k: v for k, v in counts.items() if k not in EXPECTED_185_COUNTS}
    if unexpected:
        fail(f"unexpected stages in {label}: {unexpected}")


def check_185_state_freeze() -> None:
    path = ROOT / "source_data" / "figure6_admissibility" / "CMDO_Admissibility_State_MSE_Audit.csv"
    rows = read_csv(path)
    assert_185_stage_counts(rows, "185-state synthesis")
    print("PASS 185-state synthesis: 80 U6 + 80 U7 + 12 U8 + 9 U9A + 4 U9B = 185")


def check_eicu() -> None:
    base = ROOT / "source_data" / "figure3_eicu"
    allowed = {
        "README.md",
        "StageU9_Hospital_Summary_v1_0.csv",
        "StageU9_Gate_Table_v1_0.csv",
        "StageU9_Method_Summary_v1_0.csv",
        "StageU9_Decision_Summary_v1_0.csv",
        "StageU9_Telemetry_Pair_Results_v1_0.csv",
        "StageU9_Report_v1_0.md",
    }
    if not base.is_dir():
        fail("missing share-safe eICU source directory")
    actual = {p.name for p in base.iterdir() if p.is_file()}
    unexpected = actual - allowed
    if unexpected:
        fail(f"unexpected file(s) in share-safe eICU directory: {sorted(unexpected)}")
    prohibited_suffixes = {".gz", ".zip", ".xlsx", ".mat", ".xpt"}
    bad = [p.name for p in base.iterdir() if p.is_file() and p.suffix.lower() in prohibited_suffixes]
    if bad:
        fail(f"raw/binary eICU material must not be tracked in share-safe directory: {bad}")

    hosp = read_csv(base / "StageU9_Hospital_Summary_v1_0.csv")
    if len(hosp) != 20 or len({r["hospital"] for r in hosp}) != 20:
        fail("deferred eICU reserve must contain exactly 20 independent hospital summaries")
    direct = [float(r["direct_mae"]) for r in hosp]
    cmdo = [float(r["cmdo_mae"]) for r in hosp]
    breadth = sum(c <= d for c, d in zip(cmdo, direct))
    if breadth != 14:
        fail(f"eICU breadth changed: expected 14/20, found {breadth}/20")
    pooled_direct = sum(direct) / len(direct)
    pooled_cmdo = sum(cmdo) / len(cmdo)
    if not close(pooled_direct, 0.0277722933900823, 1e-12):
        fail(f"eICU pooled direct MAE changed: {pooled_direct}")
    if not close(pooled_cmdo, 0.0267622449243006, 1e-12):
        fail(f"eICU pooled CMDO MAE changed: {pooled_cmdo}")

    gates = read_csv(base / "StageU9_Gate_Table_v1_0.csv")
    if len(gates) != 13:
        fail(f"eICU formal gate count changed: expected 13, found {len(gates)}")
    passed = sum(int(r["passed"]) for r in gates)
    failed = {r["gate"] for r in gates if int(r["passed"]) == 0}
    if passed != 10 or failed != EXPECTED_FAILED_GATES:
        fail(f"eICU formal verdict gates changed: passed={passed}/13 failed={sorted(failed)}")

    methods = read_csv(base / "StageU9_Method_Summary_v1_0.csv")
    by_method = {r["method"]: r for r in methods}
    expected_mae = {
        "DIRECT": 0.0277722933900823,
        "CMDO": 0.0267622449243006,
        "PPI_PLUS_PLUS_STYLE": 0.016252438484247,
    }
    for method, expected in expected_mae.items():
        if method not in by_method or not close(float(by_method[method]["mae"]), expected, 1e-12):
            fail(f"eICU method summary changed for {method}")

    tele = read_csv(base / "StageU9_Telemetry_Pair_Results_v1_0.csv")
    if len(tele) != 10:
        fail(f"eICU telemetry witness pair count changed: expected 10, found {len(tele)}")
    max_gap = max(float(r["TRUE_ACCURACY_GAP"]) for r in tele)
    if not close(max_gap, 0.0805285089844487, 1e-12):
        fail(f"eICU telemetry witness max gap changed: {max_gap}")

    prov_path = ROOT / "provenance" / "eicu_deferred_execution_v1_0.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    if prov.get("canonical_verdict") != EXPECTED_EICU_VERDICT:
        fail("eICU canonical verdict changed")
    if prov.get("executed_amendment_a1_code_sha256") != EXPECTED_EICU_CODE_SHA:
        fail("eICU executed A1 code SHA changed")
    if prov.get("canonical_shareable_zip_sha256") != EXPECTED_EICU_ZIP_SHA:
        fail("eICU canonical ZIP SHA changed")
    if prov.get("included_in_frozen_185_state_synthesis") is not False:
        fail("eICU must remain excluded from frozen 185-state synthesis")
    if prov.get("used_to_revise_pcc_projection") is not False:
        fail("eICU must not revise the frozen PCC projection")
    if prov.get("raw_patient_data_redistributed") is not False:
        fail("raw eICU patient data must not be redistributed")

    fig3 = (ROOT / "matlab" / "submission_figures" / "Figure3_REUSE_Refined.m").read_text(encoding="utf-8")
    if "F:\\" in fig3 or "F:/" in fig3:
        fail("Figure 3 renderer contains an author-machine F-drive path")
    if "height(T)==185" not in fig3 or "height(H)==20" not in fig3:
        fail("Figure 3 renderer is missing frozen 185-state / 20-hospital assertions")
    print("PASS deferred eICU: 20 hospitals, 10/13 gates, 14/20 breadth, immutable provenance")


def check_u10_lock() -> None:
    path = ROOT / "U10_Prospective_ECG" / "01_Prospective_Result" / "U10_PRIMARY_RESULT.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("primary_verdict") != EXPECTED_U10_VERDICT:
        fail(f"U10 locked verdict changed: {obj.get('primary_verdict')}")
    print(f"PASS U10 locked verdict: {EXPECTED_U10_VERDICT}")


def check_pcc_and_display_wiring() -> None:
    missing = [rel for rel in REQUIRED_SUBMISSION_V2_FILES if not (ROOT / rel).is_file()]
    if missing:
        fail("missing submission-v2 file(s): " + ", ".join(missing))

    for rel, expected in EXPECTED_PCC_SHA256.items():
        actual = sha256(ROOT / rel)
        if actual != expected:
            fail(f"frozen PCC file SHA changed for {rel}: {actual}")

    projection = read_csv(ROOT / "source_data" / "pcc" / "CMDO_185_realized_projection.csv")
    assert_185_stage_counts(projection, "PCC completed-state projection")

    frontier = read_csv(ROOT / "source_data" / "pcc" / "PCC_frontier_classified.csv")
    if not frontier:
        fail("PCC frontier is empty")
    required_frontier_columns = {
        "AUC_true", "h_hist", "mismatch", "m_application", "C_labels",
        "max_labels_tested", "Vmin", "rho", "robust_oracle_cap", "status",
    }
    if not required_frontier_columns.issubset(frontier[0].keys()):
        fail("PCC frontier columns changed")
    statuses = {r["status"] for r in frontier}
    if "finite_within_grid" not in statuses:
        fail("PCC frontier has no finite_within_grid states")

    runner = (ROOT / "RUN_SUBMISSION_V2_FIGURES.m").read_text(encoding="utf-8")
    expected_calls = [
        "Figure1_Evidential_Order_PCC",
        "Figure2_IDENTIFY_Validation",
        "Figure3_REUSE_Refined",
        "Figure4_CERTIFY",
        "Figure5_PRESERVE_PCC",
        "ED1_OutcomeFreeBoundary_v9",
        "ED2_IntegrityControls_v2",
        "ED3_RobustnessEfficiency_v1",
    ]
    for call in expected_calls:
        if call not in runner:
            fail(f"submission-v2 runner is missing display call: {call}")
    if "8/8 PASS" not in runner and "%d/8 PASS" not in runner:
        fail("submission-v2 runner is missing the eight-display acceptance summary")

    fig5 = (ROOT / "matlab" / "submission_figures" / "Figure5_PRESERVE_PCC.m").read_text(encoding="utf-8")
    frozen_ticks = "{'128','256','512','1024','128','256','512','1024'}"
    if frozen_ticks not in fig5:
        fail("Figure 5 panel B no longer contains the frozen 8 budget tick labels")
    if "Georgia" not in fig5 or "CPSC 2018" not in fig5:
        fail("Figure 5 panel B cohort labels changed")

    fig4 = (ROOT / "matlab" / "submission_figures" / "Figure4_CERTIFY.m").read_text(encoding="utf-8")
    for source_name in ("PCC_frontier_classified.csv", "PCC_scaling_summary_v12.csv", "CMDO_185_realized_projection.csv"):
        if source_name not in fig4:
            fail(f"Figure 4 CERTIFY renderer no longer reads {source_name}")

    print("PASS PCC/display wiring: frozen 185-state PCC projection, frozen Figure 5 budgets, 8 submission displays")


def main() -> int:
    print("CMDO submission-v2 static scientific-integrity audit")
    print(f"repo: {ROOT}")
    check_185_state_freeze()
    check_eicu()
    check_u10_lock()
    check_pcc_and_display_wiring()
    print("PASS STATIC SCIENTIFIC INTEGRITY")
    print("NOTE: this is not the final fresh-clone graphical acceptance gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
