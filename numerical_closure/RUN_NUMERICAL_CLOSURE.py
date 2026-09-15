#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(HERE / script), *args]
    print("=" * 78)
    print("RUN:", " ".join(cmd))
    print("=" * 78)
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run the additive numerical-closure checks for PCC certification, "
            "tie-robust AUC validation, and exact U10 finite-cohort risk."
        )
    )
    ap.add_argument(
        "--quick",
        action="store_true",
        help="Use 20,000 independent tie-audit states instead of 120,000.",
    )
    args = ap.parse_args()

    run("reproduce_pcc.py")
    run("reproduce_u10_exact.py")
    tie_states = "20000" if args.quick else "120000"
    run("reproduce_tie_audit.py", "--states", tie_states)

    print("")
    print("=" * 78)
    print("CMDO NUMERICAL CLOSURE: PASS")
    print("=" * 78)
    print("PCC finite-grid generation: PASS")
    print("U10 exact hypergeometric risk check: PASS")
    print("Tie-robust audit archive + independent cross-check: PASS")


if __name__ == "__main__":
    main()
