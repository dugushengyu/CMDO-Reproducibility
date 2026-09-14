#!/usr/bin/env python3
"""Reviewer-facing acceptance for the current CMDO submission-v2 evidence package.

This entry point intentionally does not execute the historical developmental DAG.
It verifies the frozen submission-v2 science invariants and renders the eight
figures/Extended Data displays used by the manuscript.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCIENCE_CHECK = ROOT / "scripts" / "verify_submission_v2_science.py"

EXPECTED_STEMS = (
    "Figure1_Evidential_Order_PCC",
    "Figure2_IDENTIFY_Validation",
    "Figure3_REUSE_Refined",
    "Figure4_CERTIFY",
    "Figure5_PRESERVE_PCC",
    "ED1_OutcomeFreeBoundary_v9",
    "ED2_IntegrityControls_v2",
    "ED3_RobustnessEfficiency_v1",
)


def run(command: list[str]) -> int:
    print("\n$", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT).returncode


def git_status() -> str | None:
    if not (ROOT / ".git").exists():
        return None
    process = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git status failed")
    return process.stdout.strip()


def require_clean(label: str) -> None:
    status = git_status()
    if status is None:
        print(f"Git cleanliness ({label}): portable package, no .git metadata")
        return
    if status:
        raise RuntimeError(f"Git worktree is not clean ({label}):\n{status}")
    print(f"Git cleanliness ({label}): PASS")


def resolve_matlab(explicit: str | None) -> str | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_matlab = os.environ.get("CMDO_MATLAB", "").strip()
    if env_matlab:
        candidates.append(Path(env_matlab).expanduser())
    on_path = shutil.which("matlab")
    if on_path:
        candidates.append(Path(on_path))
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        matlab_root = program_files / "MATLAB"
        if matlab_root.is_dir():
            candidates.extend(
                sorted(matlab_root.glob("R20*/bin/matlab.exe"), reverse=True)
            )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def matlab_quote(value: Path) -> str:
    return str(value).replace("'", "''")


def verify_rendered_outputs(output_dir: Path) -> None:
    missing: list[str] = []
    for stem in EXPECTED_STEMS:
        for suffix in (".png", ".pdf"):
            path = output_dir / f"{stem}{suffix}"
            if not path.is_file() or path.stat().st_size == 0:
                missing.append(path.name)
    if missing:
        raise RuntimeError(
            "submission-v2 graphical run completed but required outputs are "
            f"missing/empty: {missing}"
        )

    png = sorted(output_dir.glob("*.png"))
    pdf = sorted(output_dir.glob("*.pdf"))
    if len(png) != 8 or len(pdf) != 8:
        raise RuntimeError(
            f"expected exactly 8 PNG and 8 PDF outputs, found {len(png)} PNG "
            f"and {len(pdf)} PDF"
        )
    print("PASS graphical inventory: 8 PNG + 8 PDF")


def static_check() -> int:
    require_clean("before static check")
    rc = run([sys.executable, str(SCIENCE_CHECK)])
    if rc:
        return rc
    require_clean("after static check")
    print("=== CMDO SUBMISSION-V2 STATIC REVIEWER PASS ===")
    return 0


def figures(output_dir: Path, matlab_exe: str | None) -> int:
    require_clean("before graphical run")
    matlab = resolve_matlab(matlab_exe)
    if not matlab:
        print(
            "MATLAB was not found. Put matlab on PATH, set CMDO_MATLAB, or pass "
            "--matlab <path>.",
            file=sys.stderr,
        )
        return 4

    output_dir = output_dir.expanduser().resolve()
    try:
        output_dir.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError(
            "Reviewer outputs must be outside the repository so the fresh-clone "
            "worktree remains clean."
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_q = matlab_quote(ROOT.resolve())
    out_q = matlab_quote(output_dir)
    expression = (
        f"cd('{repo_q}'); "
        f"RUN_SUBMISSION_V2_FIGURES('RepoRoot',pwd,'OutDir','{out_q}',"
        "'Strict',true)"
    )
    print("\n$ matlab -batch <RUN_SUBMISSION_V2_FIGURES Strict=true>", flush=True)
    rc = subprocess.run([matlab, "-batch", expression], cwd=ROOT).returncode
    if rc:
        return rc

    verify_rendered_outputs(output_dir)
    require_clean("after graphical run")
    print("=== CMDO SUBMISSION-V2 GRAPHICAL REVIEWER PASS ===")
    print("Output:", output_dir)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CMDO submission-v2 reviewer acceptance"
    )
    parser.add_argument("command", choices=["check", "figures", "all"])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "CMDO_submission_v2_reviewer",
        help="render directory outside the Git checkout",
    )
    parser.add_argument(
        "--matlab",
        help="optional path to MATLAB executable; otherwise CMDO_MATLAB/PATH/standard Windows installs are searched",
    )
    args = parser.parse_args(argv)

    if args.command == "check":
        return static_check()
    if args.command == "figures":
        return figures(args.output_dir, args.matlab)
    if args.command == "all":
        rc = static_check()
        if rc:
            return rc
        rc = figures(args.output_dir, args.matlab)
        if rc:
            return rc
        print("\n=== CMDO SUBMISSION-V2 REVIEWER ACCEPTANCE: PASS ===")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
