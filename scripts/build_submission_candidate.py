#!/usr/bin/env python3
"""Build the lean CMDO submission-v2 reviewer package after strict preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "v2.1.4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    print("\n$", " ".join(command), flush=True)
    process = subprocess.run(command, cwd=ROOT)
    if process.returncode:
        raise RuntimeError(
            f"command failed ({process.returncode}): {' '.join(command)}"
        )


def git(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode:
        raise RuntimeError(process.stderr)
    return process.stdout.strip()


def artifact(path: Path) -> dict[str, object]:
    return {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CMDO submission-v2 reviewer package builder"
    )
    parser.add_argument("--output-dir", type=Path, default=DIST)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()

    plan = {
        "classification": "CMDO_SUBMISSION_V2_REVIEWER_BUILD",
        "preflight": [
            "build from a Git checkout with a fully clean visible worktree",
            "run submission-v2 static scientific-integrity gate",
            "package repository-tracked reviewer files only",
            "byte-verify the portable ZIP and emit SHA-256 manifest",
        ],
        "reviewer_acceptance": [
            "python RUN_REVIEWER.py all",
            "8 submission-v2 PNG + 8 submission-v2 PDF outputs",
            "Git worktree remains clean",
        ],
        "excluded_from_reviewer_requirements": [
            "historical developmental DAG replay",
            "full-claim/deep-plan/archival-continuation",
            "legacy seven-canonical-archive asset bundle",
            "restricted raw eICU/PhysioNet patient-level data",
        ],
    }
    if args.plan:
        print(json.dumps(plan, indent=2, sort_keys=True))
        print("=== CMDO SUBMISSION-V2 BUILDER PLAN PASS ===")
        return 0

    if not (ROOT / ".git").exists():
        raise RuntimeError(
            "submission artifacts must be built from the canonical Git checkout"
        )

    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"worktree is not clean before packaging:\n{status}")

    run([sys.executable, "RUN_REVIEWER.py", "check"])

    output_dir.mkdir(parents=True, exist_ok=True)
    portable = output_dir / f"CMDO-Reproducibility-Reviewer-Portable-{VERSION}.zip"
    run(
        [
            sys.executable,
            "scripts/build_portable_bundle.py",
            "--output",
            str(portable),
        ]
    )

    manifest = {
        "schema_version": 2,
        "classification": "CMDO_SUBMISSION_V2_REVIEWER_CANDIDATE",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": head,
        "git_worktree_clean": True,
        "raw_restricted_data_included": False,
        "restricted_eicu_patient_level_data_included": False,
        "share_safe_eicu_aggregate_records_included": True,
        "submission_v2_displays": 8,
        "standard_reviewer_entrypoint": "python RUN_REVIEWER.py all",
        "historical_deep_replay_required": False,
        "legacy_canonical_archive_bundle_required": False,
        "artifacts": [artifact(portable)],
        "binding_records": {
            "submission_v2_science_verifier_sha256": sha256(
                ROOT / "scripts/verify_submission_v2_science.py"
            ),
            "submission_v2_matlab_runner_sha256": sha256(
                ROOT / "RUN_SUBMISSION_V2_FIGURES.m"
            ),
            "reviewer_entrypoint_sha256": sha256(ROOT / "RUN_REVIEWER.py"),
        },
        "interpretation_boundary": (
            "The reviewer package verifies the frozen scientific invariants and "
            "regenerates the eight displays used by the current manuscript from "
            "tracked share-safe source data. Historical developmental replay is "
            "retained in the repository for provenance but is not a reviewer "
            "acceptance requirement."
        ),
    }

    manifest_path = (
        output_dir / f"CMDO-Submission-Candidate-{VERSION}_MANIFEST.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    sha_path = output_dir / f"CMDO-Submission-Candidate-{VERSION}_SHA256.txt"
    targets = [
        portable,
        portable.with_suffix(portable.suffix + ".sha256"),
        manifest_path,
    ]
    sha_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in targets),
        encoding="utf-8",
        newline="\n",
    )

    final_status = git("status", "--porcelain", "--untracked-files=all")
    # dist/ may be ignored; any visible source-worktree change is still forbidden.
    if final_status:
        raise RuntimeError(
            f"worktree changed while building reviewer package:\n{final_status}"
        )

    print("\n=== CMDO SUBMISSION-V2 REVIEWER BUILD PASS ===")
    print("Commit:", head)
    print("Portable:", portable)
    print("Manifest:", manifest_path)
    print("SHA list:", sha_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
