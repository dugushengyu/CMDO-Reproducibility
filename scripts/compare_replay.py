#!/usr/bin/env python3
"""Compare a full replay with frozen records under explicit acceptance rules."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def flatten(payload: Any, prefix: str = "") -> dict[str, Any]:
    rows: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{prefix}.{key}" if prefix else key
            rows.update(flatten(value, child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            rows.update(flatten(value, f"{prefix}[{index}]"))
    else:
        rows[prefix] = payload
    return rows


def to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_csv_bytes(
    left: bytes, right: bytes, *, atol: float, rtol: float, label: str
) -> dict[str, Any]:
    left_rows = list(csv.DictReader(io.StringIO(left.decode("utf-8-sig"))))
    right_rows = list(csv.DictReader(io.StringIO(right.decode("utf-8-sig"))))
    left_columns = list(left_rows[0]) if left_rows else []
    right_columns = list(right_rows[0]) if right_rows else []
    errors: list[str] = []
    if left_columns != right_columns:
        errors.append("column order/name mismatch")
    if len(left_rows) != len(right_rows):
        errors.append(f"row count {len(left_rows)} != {len(right_rows)}")
    max_abs = 0.0
    max_rel = 0.0
    compared_numeric = 0
    compared_exact = 0
    for index, (lrow, rrow) in enumerate(zip(left_rows, right_rows)):
        for column in set(left_columns) & set(right_columns):
            lvalue = lrow[column]
            rvalue = rrow[column]
            lf = to_float(lvalue)
            rf = to_float(rvalue)
            if lf is not None and rf is not None:
                if math.isnan(lf) and math.isnan(rf):
                    continue
                absolute = abs(lf - rf)
                relative = absolute / max(abs(lf), abs(rf), 1e-15)
                max_abs = max(max_abs, absolute)
                max_rel = max(max_rel, relative)
                compared_numeric += 1
                if absolute > atol and relative > rtol:
                    errors.append(
                        f"row {index} column {column}: {lf} != {rf} "
                        f"(abs={absolute:.6g}, rel={relative:.6g})"
                    )
            else:
                compared_exact += 1
                if lvalue != rvalue:
                    errors.append(
                        f"row {index} column {column}: {lvalue!r} != {rvalue!r}"
                    )
            if len(errors) >= 50:
                break
        if len(errors) >= 50:
            break
    return {
        "file": label,
        "rows": min(len(left_rows), len(right_rows)),
        "numeric_values": compared_numeric,
        "exact_values": compared_exact,
        "max_absolute_difference": max_abs,
        "max_relative_difference": max_rel,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }


def compare_json_bytes(
    left: bytes,
    right: bytes,
    *,
    key_pattern: re.Pattern[str],
    ignore_pattern: re.Pattern[str],
    label: str,
) -> dict[str, Any]:
    left_flat = flatten(json.loads(left.decode("utf-8-sig")))
    right_flat = flatten(json.loads(right.decode("utf-8-sig")))
    compared = []
    errors = []
    for key in sorted(set(left_flat) & set(right_flat)):
        if ignore_pattern.search(key) or not key_pattern.search(key):
            continue
        compared.append(key)
        if left_flat[key] != right_flat[key]:
            errors.append(f"{key}: {left_flat[key]!r} != {right_flat[key]!r}")
    return {
        "file": label,
        "governance_fields_compared": compared,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }


def compare_archive(
    frozen_path: Path, replay_path: Path, rules: dict[str, Any]
) -> dict[str, Any]:
    csv_rule = rules["archive_csv"]
    key_pattern = re.compile(rules["governance_key_pattern"], re.I)
    ignore_pattern = re.compile(rules["ignored_json_key_pattern"], re.I)
    with zipfile.ZipFile(frozen_path) as frozen, zipfile.ZipFile(replay_path) as replay:
        broken_frozen = frozen.testzip()
        broken_replay = replay.testzip()
        frozen_names = {name for name in frozen.namelist() if not name.endswith("/")}
        replay_names = {name for name in replay.namelist() if not name.endswith("/")}
        overlap = len(frozen_names & replay_names) / max(len(frozen_names), 1)
        csv_results = []
        json_results = []
        for name in sorted(frozen_names & replay_names):
            if name.lower().endswith(".csv"):
                csv_results.append(
                    compare_csv_bytes(
                        frozen.read(name),
                        replay.read(name),
                        atol=float(csv_rule["absolute_tolerance"]),
                        rtol=float(csv_rule["relative_tolerance"]),
                        label=name,
                    )
                )
            elif name.lower().endswith(".json"):
                try:
                    json_results.append(
                        compare_json_bytes(
                            frozen.read(name),
                            replay.read(name),
                            key_pattern=key_pattern,
                            ignore_pattern=ignore_pattern,
                            label=name,
                        )
                    )
                except json.JSONDecodeError:
                    pass
    errors = []
    if broken_frozen or broken_replay:
        errors.append(f"corrupt member: frozen={broken_frozen}, replay={broken_replay}")
    if overlap < float(csv_rule["minimum_member_overlap_fraction"]):
        errors.append(f"member overlap {overlap:.3f} below threshold")
    if len(csv_results) < int(csv_rule["minimum_common_csv_files"]):
        errors.append("no comparable scientific CSV files")
    failed = [row["file"] for row in [*csv_results, *json_results] if row["status"] != "PASS"]
    if failed:
        errors.append(f"failed comparisons: {failed}")
    return {
        "archive": replay_path.name,
        "frozen_members": len(frozen_names),
        "replay_members": len(replay_names),
        "member_overlap_fraction": overlap,
        "csv_results": csv_results,
        "json_results": json_results,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }


def compare_u2(run_dir: Path, rules: dict[str, Any]) -> dict[str, Any]:
    references = ROOT / "provenance/u2_frozen_metrics.csv"
    candidates = list(
        run_dir.rglob("StageU2_External_Target_True_Metrics_v0.1.csv")
    )
    if len(candidates) != 1:
        return {
            "status": "FAIL",
            "errors": [f"expected one U2 target-metrics table, found {len(candidates)}"],
        }
    reference_rows = list(csv.DictReader(references.open(encoding="utf-8-sig")))
    replay_rows = list(csv.DictReader(candidates[0].open(encoding="utf-8-sig")))
    by_target = {row["target"]: row for row in reference_rows}
    replay_by_target = {row["target"]: row for row in replay_rows}
    rule = rules["u2_fresh_training"]
    errors = []
    metrics = []
    if set(by_target) != set(replay_by_target):
        errors.append("U2 target roster mismatch")
    if len(replay_rows) != int(rule["expected_targets"]):
        errors.append(f"U2 target count {len(replay_rows)} != {rule['expected_targets']}")
    for target in sorted(set(by_target) & set(replay_by_target)):
        left = by_target[target]
        right = replay_by_target[target]
        for column in rule["identity_columns"]:
            if column in {"n", "prevalence"}:
                lf = float(left[column])
                rf = float(right[column])
                if not math.isclose(lf, rf, rel_tol=1e-12, abs_tol=1e-12):
                    errors.append(f"{target} identity {column}: {lf} != {rf}")
            elif left[column] != right[column]:
                errors.append(f"{target} identity {column} mismatch")
        for column in rule["metric_columns"]:
            lf = float(left[column])
            rf = float(right[column])
            absolute = abs(lf - rf)
            relative = absolute / max(abs(lf), abs(rf), 1e-15)
            metrics.append(
                {
                    "target": target,
                    "metric": column,
                    "frozen": lf,
                    "replay": rf,
                    "absolute_difference": absolute,
                    "relative_difference": relative,
                }
            )
            if absolute > float(rule["absolute_tolerance"]) and relative > float(
                rule["relative_tolerance"]
            ):
                errors.append(f"{target} {column} outside tolerance")
    return {
        "status": "PASS" if not errors else "FAIL",
        "checkpoint_sha256_required": rule["checkpoint_sha256_must_match"],
        "metrics": metrics,
        "errors": errors[:100],
    }


def compare_u8(run_dir: Path, rules: dict[str, Any]) -> dict[str, Any]:
    candidates = list(run_dir.rglob("StageU8_Complete_v1_1_0.json"))
    if len(candidates) != 1:
        return {
            "status": "FAIL",
            "errors": [f"expected one U8 completion record, found {len(candidates)}"],
        }
    payload = json.loads(candidates[0].read_text(encoding="utf-8"))
    expected = rules["u8"]["expected_execution_status"]
    status = payload.get("execution_status")
    errors = [] if status == expected else [f"execution_status {status!r} != {expected!r}"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "record": str(candidates[0]),
        "execution_status": status,
        "expected_target_rows": rules["u8"]["expected_target_rows"],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--canonical-dir", type=Path, required=True)
    args = parser.parse_args()
    rules = json.loads(
        (ROOT / "provenance/replay_acceptance_rules.json").read_text(encoding="utf-8")
    )
    frozen_dir = ROOT / "data/canonical_records"
    archive_results = []
    for replay in sorted(args.canonical_dir.glob("*.zip")):
        frozen = frozen_dir / replay.name
        if not frozen.is_file():
            archive_results.append(
                {"archive": replay.name, "status": "FAIL", "errors": ["frozen reference missing"]}
            )
        else:
            archive_results.append(compare_archive(frozen, replay, rules))
    u2_result = compare_u2(args.run_dir, rules)
    u8_result = compare_u8(args.run_dir, rules)
    failed = [row["archive"] for row in archive_results if row["status"] != "PASS"]
    if u2_result["status"] != "PASS":
        failed.append("U2_FRESH_TRAINING")
    if u8_result["status"] != "PASS":
        failed.append("U8_RECONSTRUCTION")
    report = {
        "schema_version": 1,
        "classification": "RETROSPECTIVE_REPLAY_COMPARISON",
        "model_byte_identity_required": False,
        "archive_results": archive_results,
        "u2": u2_result,
        "u8": u8_result,
        "status": "PASS" if not failed else "FAIL",
        "failed": failed,
    }
    report_path = args.run_dir / "replay_comparison_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"CMDO replay comparison {report['status']}: {report_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
