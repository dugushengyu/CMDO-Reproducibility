#!/usr/bin/env python3
"""Build the final CMDO reviewer submission artifacts after strict preflight."""
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
        raise RuntimeError(f"command failed ({process.returncode}): {' '.join(command)}")


def git(*args: str) -> str:
    process = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode:
        raise RuntimeError(process.stderr)
    return process.stdout.strip()


def artifact(path: Path) -> dict[str, object]:
    return {"file": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CMDO final reviewer submission builder")
    parser.add_argument("--output-dir", type=Path, default=DIST)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()

    plan = {
        "classification": "CMDO_FINAL_REVIEWER_SUBMISSION_BUILD",
        "preflight": [
            "HEAD equals origin/main and tracked worktree is clean",
            "RUN_REVIEWER.py check",
            "seven canonical archives byte-verify",
        ],
        "artifacts": [
            "CMDO-Reviewer-Assets-v1.0.zip",
            "CMDO-Reproducibility-Reviewer-Portable-v1.0.zip",
            "CMDO-Submission-Candidate-v1.0_MANIFEST.json",
            "CMDO-Submission-Candidate-v1.0_SHA256.txt",
        ],
        "scope": "No restricted raw data and no deferred eICU data are distributed.",
    }
    if args.plan:
        print(json.dumps(plan, indent=2, sort_keys=True))
        print("=== CMDO SUBMISSION BUILDER PLAN PASS ===")
        return 0

    if not (ROOT / ".git").exists():
        raise RuntimeError("submission artifacts must be built from the canonical Git checkout")
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    if head != origin:
        raise RuntimeError(f"HEAD {head} does not equal origin/main {origin}")
    status = git("status", "--porcelain", "--untracked-files=no")
    if status:
        raise RuntimeError(f"tracked worktree is dirty before packaging:\n{status}")

    run([sys.executable, "RUN_REVIEWER.py", "check"])
    run([sys.executable, "scripts/verify_repository.py", "--require-canonical"])

    output_dir.mkdir(parents=True, exist_ok=True)
    asset = output_dir / "CMDO-Reviewer-Assets-v1.0.zip"
    portable = output_dir / "CMDO-Reproducibility-Reviewer-Portable-v1.0.zip"
    run([sys.executable, "scripts/build_reviewer_asset_bundle.py", "--output", str(asset)])
    run([sys.executable, "scripts/build_portable_bundle.py", "--output", str(portable), "--require-reviewer-assets"])

    manifest = {
        "schema_version": 1,
        "classification": "CMDO_FINAL_REVIEWER_SUBMISSION_CANDIDATE",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": head,
        "git_worktree_clean": True,
        "raw_restricted_data_included": False,
        "u9_eicu_data_included": False,
        "standard_reviewer_entrypoint": "python RUN_REVIEWER.py all --allow-network",
        "cleanroom_maintainer_entrypoint": "powershell -ExecutionPolicy Bypass -File .\\RUN_CLEANROOM_REVIEWER.ps1",
        "artifacts": [artifact(asset), artifact(portable)],
        "binding_records": {
            "canonical_archives_manifest_sha256": sha256(ROOT / "provenance/canonical_archives_manifest.csv"),
            "final_figure56_seal_sha256": sha256(ROOT / "provenance/final_figure56_seal.json"),
        },
        "interpretation_boundary": (
            "The standard package reproduces engineering acceptance, public smoke, byte-verified frozen manuscript assets, "
            "and figure regeneration. It does not reinterpret the disclosed fresh T2-D scientific divergence or claim a fresh U9/eICU replay."
        ),
    }
    manifest_path = output_dir / "CMDO-Submission-Candidate-v1.0_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    sha_path = output_dir / "CMDO-Submission-Candidate-v1.0_SHA256.txt"
    targets = [
        asset,
        asset.with_suffix(asset.suffix + ".sha256.txt"),
        portable,
        portable.with_suffix(portable.suffix + ".sha256"),
        manifest_path,
    ]
    sha_path.write_text("".join(f"{sha256(path)}  {path.name}\n" for path in targets), encoding="utf-8", newline="\n")

    print("\n=== CMDO FINAL REVIEWER SUBMISSION BUILD PASS ===")
    print("Commit:", head)
    print("Manifest:", manifest_path)
    print("SHA list:", sha_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
