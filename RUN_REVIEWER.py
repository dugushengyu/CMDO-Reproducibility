#!/usr/bin/env python3
"""Single reviewer-facing entry point for CMDO."""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "RUN_REPRODUCTION.py"
ACCEPT = ROOT / "scripts" / "final_reviewer_acceptance.py"
INSTALL_ASSETS = ROOT / "scripts" / "install_reviewer_asset_bundle.py"
FIGURE56_AUDIT = ROOT / "scripts" / "audit_final_figure56.py"

def run(command: list[str]) -> int:
    print("\n$", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT).returncode

def audit_final_figures() -> int:
    return run([sys.executable, str(FIGURE56_AUDIT)])

def render_final_figures56(output_root: Path) -> int:
    if audit_final_figures():
        return 1
    matlab = shutil.which("matlab")
    if not matlab:
        print("\nMATLAB is not on PATH. Add MATLAB to PATH, then rerun:\n"
              "  python RUN_REVIEWER.py figures56\n")
        return 4
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CMDO_OUTPUT_ROOT"] = str(output_root)
    env["CMDO_BATCH_MODE"] = "1"
    matlab_expr = (
        "addpath(genpath(fullfile(pwd,'matlab'))); "
        "Figure5(); Figure6();"
    )
    print("\n$ matlab -batch <sealed Figure5/6 render>", flush=True)
    return subprocess.run([matlab, "-batch", matlab_expr], cwd=ROOT, env=env).returncode

def require_assets() -> int:
    rc = run([sys.executable, "scripts/verify_repository.py", "--require-canonical"])
    if rc:
        print("\nCanonical reviewer assets are not installed.\n"
              "Install the submission asset ZIP first:\n"
              "  python RUN_REVIEWER.py install-assets --bundle <CMDO-Reviewer-Assets-v1.0.zip>\n")
    return rc

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CMDO manuscript-reviewer quick path")
    parser.add_argument("command", choices=["check","install-assets","smoke","figures56","frozen","all","deep-plan"])
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "reviewer")
    parser.add_argument("--run-prefix", default="CMDO-REVIEWER")
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "check":
        return run([sys.executable, str(ACCEPT), "--skip-runtime"])
    if args.command == "install-assets":
        if args.bundle is None:
            parser.error("install-assets requires --bundle <zip>")
        return run([sys.executable, str(INSTALL_ASSETS), "--bundle", str(args.bundle)])
    if args.command == "smoke":
        command = [sys.executable, str(RUNNER), "smoke", "--run-id", f"{args.run_prefix}-SMOKE",
                   "--output-root", str(args.output_root)]
        if args.allow_network:
            command.append("--allow-network")
        return run(command)
    if args.command == "figures56":
        return render_final_figures56(args.output_root)
    if args.command == "frozen":
        if audit_final_figures():
            return 1
        if require_assets():
            return 3
        return run([sys.executable, str(RUNNER), "frozen", "--run-id", f"{args.run_prefix}-FROZEN",
                    "--output-root", str(args.output_root)])
    if args.command == "all":
        rc = run([sys.executable, str(ACCEPT), "--skip-runtime"])
        if rc:
            return rc
        smoke = [sys.executable, str(RUNNER), "smoke", "--run-id", f"{args.run_prefix}-SMOKE",
                 "--output-root", str(args.output_root)]
        if args.allow_network:
            smoke.append("--allow-network")
        rc = run(smoke)
        if rc:
            return rc
        if require_assets():
            return 3
        return run([sys.executable, str(RUNNER), "frozen", "--run-id", f"{args.run_prefix}-FROZEN",
                    "--output-root", str(args.output_root)])
    if args.command == "deep-plan":
        rc = run([sys.executable, str(RUNNER), "full-claim", "--plan", "--run-id",
                  f"{args.run_prefix}-FULL-PLAN"])
        if rc:
            return rc
        return run([sys.executable, str(RUNNER), "archival-continuation", "--plan", "--run-id",
                    f"{args.run_prefix}-ARCHIVAL-PLAN"])
    raise AssertionError(args.command)

if __name__ == "__main__":
    raise SystemExit(main())
