#!/usr/bin/env python3
"""Build a non-destructive, exact-ID Drive cleanup proposal."""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "provenance/drive_targeted_inventory_2026-08-10.json"
OUTPUT = ROOT / "cleanup/drive_cleanup_manifest.csv"
SUMMARY = ROOT / "cleanup/drive_cleanup_summary.json"


def local_backups() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for manifest in [
        ROOT / "provenance/drive_import_manifest.csv",
        ROOT / "provenance/drive_supporting_import_manifest.csv",
        ROOT / "provenance/canonical_archives_manifest.csv",
    ]:
        with manifest.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                drive_id = row.get("drive_file_id")
                if not drive_id:
                    continue
                result[drive_id] = {
                    "local_path": row.get("repository_path") or (
                        "data/canonical_records/" + row.get("archive", "")
                    ),
                    "sha256": row.get("repository_sha256") or row.get("sha256", ""),
                }
    return result


def classify(path: str, backed_up: bool) -> tuple[str, str, str]:
    lower = path.lower()
    if "__pycache__" in lower or lower.endswith((".pyc", ".pyo")):
        return (
            "DELETE_CANDIDATE",
            "generated Python bytecode; reproducible from authoritative source",
            "EXPLICIT_CONFIRMATION_REQUIRED",
        )
    if any(token in lower for token in ["legacy", "99_superseded", "before_target_style"]):
        return (
            "ARCHIVE_CANDIDATE",
            "explicitly labelled legacy/superseded/pre-style artifact",
            "ARCHIVE_AND_CONFIRM",
        )
    if "rendered_one_figure_at_a_time" in lower:
        return (
            "ARCHIVE_CANDIDATE",
            "older rendered figure export; current MATLAB source package is authoritative",
            "VERIFY_CURRENT_FIGURES_THEN_CONFIRM",
        )
    if "cmdo_nature_main_figures_v3.0_rebuilt" in lower or lower.endswith("_draft.png"):
        return (
            "ARCHIVE_CANDIDATE",
            "older draft/v3 rendered figure package retained for provenance only",
            "VERIFY_CURRENT_FIGURES_THEN_CONFIRM",
        )
    if backed_up:
        return (
            "KEEP",
            "hash-backed local import or canonical record",
            "NO_DELETION",
        )
    if path.startswith("12_Governance/"):
        return ("KEEP", "governance and claim-boundary evidence", "NO_DELETION")
    if "00_current_figure_source_package/matlab_source_current" in lower:
        return ("KEEP", "current figure source package", "NO_DELETION")
    if "00_one_figure_colabs_current" in lower and not any(
        token in lower for token in ["before_target_style", "legacy"]
    ):
        return ("KEEP", "current editable figure source", "NO_DELETION")
    return (
        "REVIEW",
        "not enough evidence in the targeted inventory for safe disposition",
        "MANUAL_REVIEW_REQUIRED",
    )


def build() -> tuple[str, dict[str, object]]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    backups = local_backups()
    rows = []
    counts: Counter[str] = Counter()
    bytes_by_action: defaultdict[str, int] = defaultdict(int)
    for item in sorted(inventory["files"], key=lambda row: row["path"]):
        backup = backups.get(item["id"])
        action, reason, gate = classify(item["path"], bool(backup))
        size = int(item.get("size") or 0)
        counts[action] += 1
        bytes_by_action[action] += size
        rows.append(
            {
                "drive_file_id": item["id"],
                "drive_path": item["path"],
                "size_bytes": size,
                "proposed_action": action,
                "reason": reason,
                "local_backup_path": backup["local_path"] if backup else "",
                "local_backup_sha256": backup["sha256"] if backup else "",
                "second_backup_verified": "false",
                "delete_authorized": "false",
                "next_gate": gate,
            }
        )
    stream = io.StringIO(newline="")
    fieldnames = list(rows[0])
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    summary = {
        "schema_version": 1,
        "scope": json.loads(
            (ROOT / "provenance/drive_inventory_summary.json").read_text(encoding="utf-8")
        )["scope"],
        "inventory_complete_within_scope": inventory["complete"],
        "full_drive_inventory": False,
        "deletion_performed": False,
        "deletion_authorized": False,
        "counts": dict(sorted(counts.items())),
        "bytes": dict(sorted(bytes_by_action.items())),
        "rule": "No Drive mutation until two backups, replay validation, public snapshot and explicit row-level confirmation.",
    }
    return stream.getvalue(), summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text, summary = build()
    expected_summary = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        errors = []
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8-sig") != text:
            errors.append("cleanup/drive_cleanup_manifest.csv is stale")
        if not SUMMARY.is_file() or SUMMARY.read_text(encoding="utf-8-sig") != expected_summary:
            errors.append("cleanup/drive_cleanup_summary.json is stale")
        if errors:
            print("CMDO cleanup manifest FAILED")
            for error in errors:
                print(f"- {error}")
            return 1
        print("CMDO cleanup manifest PASS (no deletion performed)")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    SUMMARY.write_text(expected_summary, encoding="utf-8")
    print("CMDO cleanup proposal WRITTEN (no deletion performed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
