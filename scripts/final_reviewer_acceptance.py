#!/usr/bin/env python3
"""One-command engineering acceptance for the CMDO reviewer package.

This check never turns a scientific non-reproduction into a pass. It validates the
package/runner/bootstrap surface and, when a project root is supplied, reports the
sealed T2-D boundary separately from engineering acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reproduction.bootstrap import verify_historical_receipts, verify_replay_python_environment
from reproduction.dag import ReproductionDAG


def _child_environment() -> dict[str, str]:
    """Return a byte-neutral child environment with canonical Windows temp paths.

    Hosted Windows runners may expose TEMP/TMP through an 8.3 short alias while
    ``Path.resolve()`` expands the same directory to its long form. Canonicalising
    these environment values prevents path-spelling-only unit-test failures without
    altering any scientific input, threshold or replay rule.
    """
    env = os.environ.copy()
    if os.name == "nt":
        for key in ("TEMP", "TMP", "TMPDIR"):
            value = env.get(key)
            if value:
                env[key] = str(Path(value).expanduser().resolve())
    return env


def run(command: list[str], *, label: str) -> dict:
    print(f"\n[{label}] {' '.join(command)}")
    p = subprocess.run(command, cwd=ROOT, text=True, env=_child_environment())
    if p.returncode:
        raise RuntimeError(f"{label} failed with exit status {p.returncode}")
    return {"label": label, "command": command, "returncode": p.returncode}


def t2d_boundary(project_root: Path) -> dict | None:
    path = project_root / (
        "06_Data_Records/Cross_Modal/"
        "StageT2-D_Development_Only_AMW-DDET_Active_Minimal_Witness_Certificate_v0.1/"
        "04_Results/StageT2-D_Complete_v0.1.json"
    )
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    metrics = payload.get("metrics", {})
    return {
        "path": str(path),
        "gates_passed": payload.get("frozen_gates_passed"),
        "gates_total": payload.get("frozen_gates_total"),
        "decision": payload.get("decision"),
        "g4_target_signflip": metrics.get(
            "target_cluster_exact_signflip_p", metrics.get("target_signflip_p")
        ),
        "stage12_authorised": payload.get("stage12_authorised"),
        "locked_blind_assets_touched": payload.get("locked_blind_assets_touched"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path)
    ap.add_argument("--skip-runtime", action="store_true", help="static package acceptance only")
    ap.add_argument(
        "--require-canonical", action="store_true",
        help="require all seven canonical scientific archives (Portable bundle acceptance)",
    )
    ap.add_argument("--output", type=Path, default=ROOT / "outputs/reviewer_acceptance.json")
    args = ap.parse_args()

    report: dict = {
        "classification": "CMDO_REVIEWER_ENGINEERING_ACCEPTANCE",
        "scientific_acceptance_inferred": False,
        "checks": [],
    }

    verify_command = [sys.executable, "scripts/verify_repository.py"]
    if args.require_canonical:
        verify_command.append("--require-canonical")
    report["checks"].append(run(verify_command, label="repository"))
    report["checks"].append(run([sys.executable, "scripts/extract_embedded_sources.py", "--check"], label="embedded-sources"))
    report["checks"].append(run([sys.executable, "scripts/build_provenance_manifests.py", "--check"], label="provenance"))
    report["checks"].append(run([sys.executable, "scripts/build_cleanup_manifest.py", "--check"], label="cleanup-manifest"))
    report["checks"].append(run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], label="unit-tests"))

    dag = ReproductionDAG(ROOT / "provenance/reproduction_dag.json")
    full = [s.id for s in dag.select("full-claim")]
    archival = [s.id for s in dag.select("archival-continuation")]
    assert len(full) == 55
    assert full.index("t2f_covariate_balance") < full.index("t3pf_preflight") < full.index("t2g_hierarchy")
    assert "t2d_witness" not in archival and "t2e_baselines" not in archival
    assert "t2f_covariate_balance" not in archival
    assert archival.index("archival_preflight") < archival.index("t3pf_preflight") < archival.index("t2g_hierarchy")
    assert not any("u9" in x.lower() for x in full + archival)
    report["dag"] = {"full_claim_nodes": len(full), "archival_nodes": len(archival), "u9_excluded": True}

    if not args.skip_runtime:
        report["python_replay_environment"] = verify_replay_python_environment()
        matlab = shutil.which("matlab")
        if not matlab:
            raise RuntimeError("MATLAB is not on PATH; full/archival reviewer paths require MATLAB")
        report["matlab_on_path"] = matlab

    if args.project_root:
        project = args.project_root.expanduser().resolve()
        report["historical_receipts"] = verify_historical_receipts(ROOT, project)
        boundary = t2d_boundary(project)
        report["project_root"] = str(project)
        report["t2d_observed"] = boundary
        if boundary:
            historical_authorised = (
                boundary.get("gates_passed") == 11
                and boundary.get("gates_total") == 11
                and boundary.get("decision")
                == "AUTHORISE_AMW_DDET_METHOD_FREEZE_AND_BLIND_PREREGISTRATION_ONLY"
            )
            report["fresh_scientific_chain_complete"] = bool(historical_authorised)
            report["scientific_boundary_code"] = None if historical_authorised else "SCIENTIFIC_DIVERGENCE_BOUNDARY"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n=== CMDO REVIEWER ENGINEERING ACCEPTANCE PASS ===")
    print("Static integrity, provenance, bootstrap identities, DAG and unit tests passed.")
    print("This PASS does not overwrite or reinterpret any scientific divergence.")
    if report.get("scientific_boundary_code"):
        print(f"Observed scientific status: {report['scientific_boundary_code']}")
    print("Report:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
