#!/usr/bin/env python3
"""Static scientific-integrity checks for the CMDO submission-v2 freeze.

This verifier is intentionally independent of MATLAB.  It checks frozen
source/provenance records and claim boundaries before the graphical
fresh-clone acceptance run.  It does not re-run sealed prospective stages.
"""
from __future__ import annotations

import csv
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


def fail(msg: str) -> None:
    raise AssertionError(msg)


def close(a: float, b: float, tol: float = 1e-10) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"missing required CSV: {path.relative_to(ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def check_185_state_freeze() -> None:
    path = ROOT / "source_data" / "figure6_admissibility" / "CMDO_Admissibility_State_MSE_Audit.csv"
    rows = read_csv(path)
    if len(rows) != 185:
        fail(f"185-state synthesis changed: expected 185 rows, found {len(rows)}")
    if "stage" not in rows[0]:
        fail("185-state synthesis has no stage column")
    counts = Counter(r["stage"].strip() for r in rows)
    for stage, n in EXPECTED_185_COUNTS.items():
        if counts.get(stage, 0) != n:
            fail(f"185-state stage count changed for {stage}: expected {n}, found {counts.get(stage, 0)}")
    unexpected = {k: v for k, v in counts.items() if k not in EXPECTED_185_COUNTS}
    if unexpected:
        fail(f"unexpected stages in frozen 185-state synthesis: {unexpected}")
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


def main() -> int:
    print("CMDO submission-v2 static scientific-integrity audit")
    print(f"repo: {ROOT}")
    check_185_state_freeze()
    check_eicu()
    check_u10_lock()
    print("PASS STATIC SCIENTIFIC INTEGRITY")
    print("NOTE: this is not the final fresh-clone graphical acceptance gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
