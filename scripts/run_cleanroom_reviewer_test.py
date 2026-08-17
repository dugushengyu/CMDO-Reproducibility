#!/usr/bin/env python3
"""Run a clean-room reviewer acceptance from a fresh clone or portable bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = Path.home() / "Downloads" / "CMDO-Reviewer-Cleanroom"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    process = subprocess.run(
        ["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if check and process.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({process.returncode}):\n{process.stderr}"
        )
    return process.stdout.strip()


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run_logged(command: list[str], *, cwd: Path, log_path: Path) -> dict[str, object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    print("\n$", " ".join(command), flush=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="backslashreplace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        rc = process.wait()
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": rc,
        "duration_seconds": round(time.time() - started, 3),
        "log": str(log_path),
    }


def extract_portable(bundle: Path, destination: Path) -> tuple[Path, dict[str, object]]:
    with zipfile.ZipFile(bundle) as archive:
        broken = archive.testzip()
        if broken:
            raise RuntimeError(f"portable bundle has corrupt member: {broken}")
        info_name = "CMDO-Reproducibility/PORTABLE_PACKAGE_INFO.json"
        info = json.loads(archive.read(info_name))
        archive.extractall(destination)
    repo = destination / "CMDO-Reproducibility"
    if not (repo / "RUN_REVIEWER.py").is_file():
        raise RuntimeError("portable bundle did not materialize RUN_REVIEWER.py")
    return repo, info


def source_preflight() -> dict[str, object]:
    required = [
        ROOT / "RUN_REVIEWER.py",
        ROOT / "environment/requirements-replay.txt",
        ROOT / "environment/replay-constraints.txt",
        ROOT / "scripts/install_reviewer_asset_bundle.py",
        ROOT / "scripts/build_reviewer_asset_bundle.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"clean-room source preflight missing files: {missing}")
    result: dict[str, object] = {"required_files": len(required)}
    if (ROOT / ".git").exists():
        result["source_head"] = git("rev-parse", "HEAD")
        result["source_status_clean"] = not bool(git("status", "--porcelain"))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CMDO clean-room reviewer acceptance")
    delivery = parser.add_mutually_exclusive_group()
    delivery.add_argument("--repository-url", help="fresh-clone delivery route")
    delivery.add_argument("--portable-bundle", type=Path, help="offline portable ZIP delivery route")
    parser.add_argument("--ref", help="exact Git ref/commit for clone mode")
    parser.add_argument("--asset-bundle", type=Path, help="CMDO-Reviewer-Assets-v1.0.zip")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--python", dest="python_exe", default=sys.executable)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--skip-environment-install", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--skip-matlab", action="store_true")
    parser.add_argument("--skip-frozen", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    preflight = source_preflight()
    if args.selftest:
        print(json.dumps({
            "classification": "CMDO_CLEANROOM_REVIEWER_TOOL_SELFTEST",
            "source_preflight": preflight,
            "default_workspace": str(DEFAULT_WORKSPACE),
            "required_python_major_minor": "3.11",
            "standard_sequence": [
                "fresh delivery materialization",
                "new Python 3.11 venv + pinned dependencies",
                "RUN_REVIEWER.py check",
                "install exact seven-archive reviewer asset bundle",
                "RUN_REVIEWER.py deep-plan",
                "RUN_REVIEWER.py figures56",
                "RUN_REVIEWER.py smoke --allow-network",
                "RUN_REVIEWER.py frozen",
                "post-run clean delivery check",
            ],
        }, indent=2, sort_keys=True))
        print("=== CMDO CLEANROOM TOOL SELFTEST PASS ===")
        return 0

    if not args.repository_url and not args.portable_bundle:
        if not (ROOT / ".git").exists():
            parser.error("provide --repository-url or --portable-bundle")
        args.repository_url = git("remote", "get-url", "origin")
    if args.repository_url and not args.ref:
        args.ref = git("rev-parse", "HEAD") if (ROOT / ".git").exists() else "main"

    workspace = args.workspace.expanduser().resolve()
    if workspace.exists():
        if not args.force:
            raise SystemExit(f"workspace already exists; use --force to replace it: {workspace}")
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    logs = workspace / "logs"
    report_path = workspace / "CMDO_CLEANROOM_REVIEWER_REPORT.json"
    commands: list[dict[str, object]] = []
    report: dict[str, object] = {
        "schema_version": 1,
        "classification": "CMDO_CLEANROOM_REVIEWER_ACCEPTANCE",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "source_preflight": preflight,
        "delivery": {},
        "commands": commands,
    }

    try:
        if args.portable_bundle:
            bundle = args.portable_bundle.expanduser().resolve()
            if not bundle.is_file():
                raise RuntimeError(f"portable bundle not found: {bundle}")
            repo, info = extract_portable(bundle, workspace)
            report["delivery"] = {
                "mode": "portable_bundle",
                "bundle": str(bundle),
                "bundle_sha256": sha256(bundle),
                "package_info": info,
            }
        else:
            repo = workspace / "CMDO-Reproducibility"
            clone = run_logged(
                ["git", "clone", "--no-local", str(args.repository_url), str(repo)],
                cwd=workspace,
                log_path=logs / "01_clone.log",
            )
            commands.append(clone)
            if clone["returncode"]:
                raise RuntimeError("fresh git clone failed")
            checkout = run_logged(
                ["git", "checkout", "--detach", str(args.ref)],
                cwd=repo,
                log_path=logs / "02_checkout.log",
            )
            commands.append(checkout)
            if checkout["returncode"]:
                raise RuntimeError(f"could not checkout requested ref {args.ref}")
            cloned_head = git("rev-parse", "HEAD", cwd=repo)
            expected_head = git("rev-parse", f"{args.ref}^{{commit}}", cwd=repo)
            if cloned_head != expected_head:
                raise RuntimeError(f"clean-room HEAD mismatch: requested {args.ref} -> {expected_head}, got {cloned_head}")
            if git("status", "--porcelain", cwd=repo):
                raise RuntimeError("fresh clone is unexpectedly dirty before reviewer execution")
            report["delivery"] = {
                "mode": "fresh_clone",
                "repository_url": args.repository_url,
                "requested_ref": args.ref,
                "cloned_head": cloned_head,
            }

        base_python = Path(args.python_exe).expanduser().resolve()
        version = subprocess.run(
            [str(base_python), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
            text=True, stdout=subprocess.PIPE, check=True,
        ).stdout.strip()
        if tuple(map(int, version.split(".")[:2])) != (3, 11):
            raise RuntimeError(f"clean-room requires Python 3.11; selected interpreter is {version}")
        report["python_base"] = {"path": str(base_python), "version": version}

        venv = repo / ".venv-cleanroom"
        py = venv_python(venv)
        if args.skip_environment_install:
            py = base_python
            report["environment_install"] = "SKIPPED_BY_REQUEST"
        else:
            create = run_logged(
                [str(base_python), "-m", "venv", str(venv)], cwd=repo,
                log_path=logs / "03_create_venv.log",
            )
            commands.append(create)
            if create["returncode"]:
                raise RuntimeError("clean-room venv creation failed")
            install = run_logged(
                [str(py), "-m", "pip", "install", "-c", "environment/replay-constraints.txt", "-r", "environment/requirements-replay.txt"],
                cwd=repo, log_path=logs / "04_install_environment.log",
            )
            commands.append(install)
            if install["returncode"]:
                raise RuntimeError("clean-room dependency installation failed")
            report["environment_install"] = "PINNED_REQUIREMENTS_INSTALLED"

        def reviewer(label: str, *reviewer_args: str) -> None:
            record = run_logged(
                [str(py), "RUN_REVIEWER.py", *reviewer_args],
                cwd=repo, log_path=logs / f"{label}.log",
            )
            commands.append(record)
            if record["returncode"]:
                raise RuntimeError(f"reviewer step failed: {label}")

        reviewer("05_check", "check")

        if args.asset_bundle:
            asset = args.asset_bundle.expanduser().resolve()
            if not asset.is_file():
                raise RuntimeError(f"reviewer asset bundle not found: {asset}")
            report["asset_bundle"] = {
                "path": str(asset),
                "size_bytes": asset.stat().st_size,
                "sha256": sha256(asset),
            }
            reviewer("06_install_assets", "install-assets", "--bundle", str(asset))
        else:
            canonical = repo / "data" / "canonical_records"
            if not canonical.is_dir():
                raise RuntimeError("no --asset-bundle supplied and portable delivery lacks canonical records")

        reviewer("07_deep_plan", "deep-plan")

        matlab = shutil.which("matlab")
        report["matlab"] = matlab
        if args.skip_matlab:
            report["figures56"] = "SKIPPED_BY_REQUEST"
        else:
            if not matlab:
                raise RuntimeError("MATLAB is required for standard clean-room acceptance but is not on PATH")
            reviewer("08_figures56", "figures56", "--output-root", str(repo / "outputs" / "cleanroom-reviewer"))

        if args.skip_smoke:
            report["smoke"] = "SKIPPED_BY_REQUEST"
        else:
            if not args.allow_network:
                raise RuntimeError("public smoke requires --allow-network (or use --skip-smoke)")
            reviewer(
                "09_smoke", "smoke", "--allow-network", "--run-prefix", "CLEANROOM",
                "--output-root", str(repo / "outputs" / "cleanroom-reviewer"),
            )

        if args.skip_frozen:
            report["frozen"] = "SKIPPED_BY_REQUEST"
        else:
            if not matlab:
                raise RuntimeError("frozen figure regeneration requires MATLAB on PATH")
            reviewer(
                "10_frozen", "frozen", "--run-prefix", "CLEANROOM",
                "--output-root", str(repo / "outputs" / "cleanroom-reviewer"),
            )

        if (repo / ".git").exists():
            post_status = git("status", "--porcelain", cwd=repo)
            if post_status:
                raise RuntimeError(f"clean-room clone became dirty after reviewer execution:\n{post_status}")
            report["post_run_git_status"] = "CLEAN"

        report["status"] = "PASS"
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print("\n=== CMDO CLEANROOM REVIEWER ACCEPTANCE PASS ===")
        print("Report:", report_path)
        return 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"\nCMDO clean-room reviewer acceptance FAILED: {exc}", file=sys.stderr)
        print("Report:", report_path, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
