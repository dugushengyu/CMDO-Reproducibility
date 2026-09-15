#!/usr/bin/env python3
"""One-command CMDO end-to-end reviewer audit.

This optional audit supplements (but never replaces) the frozen submission-v2
reviewer path. It performs:
1. frozen manifest/science verification;
2. public CIFAR acquisition + real U2 12-epoch training + 38-target inference;
3. tolerance comparison with frozen U2 reference metrics;
4. fresh current-outcome audit source data;
5. strict regeneration of the current 5 main + 3 Extended Data displays;
6. a machine-readable end-to-end report.

Historical T2/T3 developmental replay is intentionally excluded.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("\n$", " ".join(command), flush=True)
    p = subprocess.run(command, cwd=cwd)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(command)}")


def git_status() -> str:
    if not (ROOT / ".git").exists():
        return ""
    p = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode:
        raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()


def git_head() -> str | None:
    if not (ROOT / ".git").exists():
        return None
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package_results(work: Path) -> tuple[Path, str]:
    package = work / "CMDO_E2E_REVIEWER_RESULTS.zip"
    if package.exists():
        package.unlink()
    include_roots = [work / "u2_fresh", work / "submission_v2_figures"]
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for root in include_roots:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(work).as_posix())
        report = work / "CMDO_E2E_REVIEWER_REPORT.json"
        if report.is_file():
            zf.write(report, arcname=report.name)
    digest = sha256(package)
    (work / "CMDO_E2E_REVIEWER_RESULTS.zip.sha256.txt").write_text(
        f"{digest}  {package.name}\n", encoding="utf-8"
    )
    return package, digest


def main() -> int:
    parser = argparse.ArgumentParser(description="CMDO end-to-end reviewer audit")
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--matlab", default=None)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--witness-reps", type=int, default=100)
    args = parser.parse_args()

    if git_status():
        raise SystemExit("Repository must be clean before E2E reviewer audit")

    work = args.work_root.expanduser().resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    started = time.time()

    run([sys.executable, "scripts/verify_submission_v2_manifest.py"])
    run([sys.executable, "scripts/verify_submission_v2_science.py"])

    train_cmd = [
        sys.executable,
        "scripts/reviewer_u2_fresh_training.py",
        "--work-root", str(work),
        "--epochs", str(args.epochs),
        "--device", args.device,
        "--witness-reps", str(args.witness_reps),
    ]
    if args.data_root:
        train_cmd += ["--data-root", str(args.data_root.expanduser().resolve())]
    run(train_cmd)

    figures = work / "submission_v2_figures"
    cmd = [
        sys.executable,
        "RUN_REVIEWER.py",
        "figures",
        "--output-dir", str(figures),
    ]
    if args.matlab:
        cmd += ["--matlab", args.matlab]
    run(cmd)

    if len(list(figures.glob("*.png"))) != 8 or len(list(figures.glob("*.pdf"))) != 8:
        raise RuntimeError("final manuscript figure inventory is not 8 PNG + 8 PDF")

    status = git_status()
    if status:
        raise RuntimeError(f"repository became dirty after E2E run:\n{status}")

    u2_report = json.loads((work / "u2_fresh" / "fresh_u2_report.json").read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "classification": "CMDO_OPTIONAL_END_TO_END_REVIEWER_AUDIT",
        "status": "PASS" if u2_report["status"] == "PASS" else u2_report["status"],
        "git_commit": git_head(),
        "historical_t2_t3_replay_executed": False,
        "fresh_public_data_acquisition": True,
        "fresh_model_training": True,
        "fresh_external_prediction_targets": u2_report["targets"],
        "fresh_u2_tolerance_comparison": u2_report["status"],
        "fresh_current_outcome_audit_generated": True,
        "manuscript_figures_regenerated": 8,
        "final_png_count": len(list(figures.glob("*.png"))),
        "final_pdf_count": len(list(figures.glob("*.pdf"))),
        "git_worktree_clean_after_run": True,
        "duration_seconds": round(time.time() - started, 3),
        "work_root": str(work),
        "scientific_boundary": (
            "Fresh U2 training is an additional platform-tolerant reviewer replay. "
            "It does not replace frozen manuscript records or sealed prospective verdicts."
        ),
    }
    report_path = work / "CMDO_E2E_REVIEWER_REPORT.json"
    report["results_package"] = str(work / "CMDO_E2E_REVIEWER_RESULTS.zip")
    report["results_package_sha256_sidecar"] = str(
        work / "CMDO_E2E_REVIEWER_RESULTS.zip.sha256.txt"
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    package, package_sha = package_results(work)

    print(f"\n=== CMDO END-TO-END REVIEWER AUDIT: {report['status']} ===")
    print(json.dumps(report, indent=2), flush=True)
    print("Results package:", package)
    print("Results package SHA256:", package_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
