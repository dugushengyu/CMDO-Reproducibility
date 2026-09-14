#!/usr/bin/env python3
"""Run the lean submission-v2 reviewer acceptance in a clean room."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
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
PREFIX = "CMDO-Reproducibility"
if os.name == "nt":
    _system_drive = os.environ.get("SystemDrive", "C:")
    DEFAULT_WORKSPACE = Path(_system_drive + "\\") / "CMDO-CR"
else:
    DEFAULT_WORKSPACE = Path.home() / "CMDO-Reviewer-Cleanroom"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_command(*args: str) -> list[str]:
    if os.name == "nt":
        return ["git", "-c", "core.longpaths=true", *args]
    return ["git", *args]


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    process = subprocess.run(
        git_command(*args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and process.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({process.returncode}):\n{process.stderr}"
        )
    return process.stdout.strip()


def run_logged(
    command: list[str], *, cwd: Path, log_path: Path
) -> dict[str, object]:
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


def verify_portable_archive(bundle: Path) -> dict[str, object]:
    with zipfile.ZipFile(bundle) as archive:
        broken = archive.testzip()
        if broken:
            raise RuntimeError(f"portable bundle has corrupt member: {broken}")
        manifest_name = f"{PREFIX}/PORTABLE_MANIFEST_SHA256.csv"
        info_name = f"{PREFIX}/PORTABLE_PACKAGE_INFO.json"
        rows = list(
            csv.DictReader(
                io.StringIO(archive.read(manifest_name).decode("utf-8"))
            )
        )
        for row in rows:
            member = f"{PREFIX}/{row['relative_path']}"
            data = archive.read(member)
            if len(data) != int(row["size_bytes"]):
                raise RuntimeError(f"portable size mismatch: {member}")
            if sha256_bytes(data) != row["sha256"]:
                raise RuntimeError(f"portable SHA mismatch: {member}")
        info = json.loads(archive.read(info_name))
        if info.get("historical_deep_replay_required") is not False:
            raise RuntimeError("portable package incorrectly requires deep replay")
        if info.get("submission_v2_displays") != 8:
            raise RuntimeError("portable package does not declare 8 displays")
        if info.get("raw_restricted_data_included") is not False:
            raise RuntimeError("portable package incorrectly contains restricted raw data")
    return {
        "bundle_sha256": sha256(bundle),
        "verified_members": len(rows),
        "package_info": info,
    }


def extract_portable(
    bundle: Path, destination: Path
) -> tuple[Path, dict[str, object]]:
    verified = verify_portable_archive(bundle)
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(destination)
    repo = destination / PREFIX
    if not (repo / "RUN_REVIEWER.py").is_file():
        raise RuntimeError("portable bundle did not materialize RUN_REVIEWER.py")
    return repo, verified


def source_preflight() -> dict[str, object]:
    required = [
        ROOT / "RUN_REVIEWER.py",
        ROOT / "RUN_SUBMISSION_V2_FIGURES.m",
        ROOT / "scripts/verify_submission_v2_science.py",
        ROOT / "scripts/build_portable_bundle.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"clean-room source preflight missing files: {missing}")
    result: dict[str, object] = {
        "required_files": len(required),
        "reviewer_path": "submission-v2 static science + eight graphical displays",
        "historical_deep_replay_required": False,
        "windows_longpaths_enabled_for_git": os.name == "nt",
    }
    if (ROOT / ".git").exists():
        result["source_head"] = git("rev-parse", "HEAD")
        result["source_status_clean"] = not bool(
            git("status", "--porcelain", "--untracked-files=all")
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CMDO submission-v2 clean-room reviewer acceptance"
    )
    delivery = parser.add_mutually_exclusive_group()
    delivery.add_argument("--repository-url", help="fresh-clone delivery route")
    delivery.add_argument(
        "--portable-bundle", type=Path, help="offline portable ZIP delivery route"
    )
    parser.add_argument("--ref", help="exact Git ref/commit for clone mode")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--python", dest="python_exe", default=sys.executable)
    parser.add_argument("--matlab", help="optional MATLAB executable path")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    preflight = source_preflight()
    if args.selftest:
        print(
            json.dumps(
                {
                    "classification": "CMDO_SUBMISSION_V2_CLEANROOM_TOOL_SELFTEST",
                    "source_preflight": preflight,
                    "default_workspace": str(DEFAULT_WORKSPACE),
                    "standard_sequence": [
                        "fresh clone or byte-verified portable delivery",
                        "python RUN_REVIEWER.py all",
                        "verify 8 PNG + 8 PDF",
                        "verify clean Git worktree when Git metadata is present",
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        print("=== CMDO SUBMISSION-V2 CLEANROOM TOOL SELFTEST PASS ===")
        return 0

    if not args.repository_url and not args.portable_bundle:
        if not (ROOT / ".git").exists():
            parser.error("provide --repository-url or --portable-bundle")
        args.repository_url = git("remote", "get-url", "origin")
    if args.repository_url and not args.ref:
        args.ref = (
            git("rev-parse", "HEAD") if (ROOT / ".git").exists() else "main"
        )

    workspace = args.workspace.expanduser().resolve()
    if workspace.exists():
        if not args.force:
            raise SystemExit(
                f"workspace already exists; use --force to replace it: {workspace}"
            )
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    logs = workspace / "logs"
    report_path = workspace / "CMDO_CLEANROOM_REVIEWER_REPORT.json"
    commands: list[dict[str, object]] = []
    report: dict[str, object] = {
        "schema_version": 2,
        "classification": "CMDO_SUBMISSION_V2_CLEANROOM_REVIEWER_ACCEPTANCE",
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
            repo, verified = extract_portable(bundle, workspace)
            report["delivery"] = {
                "mode": "portable_bundle",
                "bundle": str(bundle),
                **verified,
            }
        else:
            repo = workspace / PREFIX
            clone = run_logged(
                git_command(
                    "clone", "--no-local", str(args.repository_url), str(repo)
                ),
                cwd=workspace,
                log_path=logs / "01_clone.log",
            )
            commands.append(clone)
            if clone["returncode"]:
                raise RuntimeError("fresh git clone failed")

            if os.name == "nt":
                git("config", "core.longpaths", "true", cwd=repo)
            checkout = run_logged(
                git_command("checkout", "--detach", str(args.ref)),
                cwd=repo,
                log_path=logs / "02_checkout.log",
            )
            commands.append(checkout)
            if checkout["returncode"]:
                raise RuntimeError(
                    f"could not checkout requested ref {args.ref}"
                )

            cloned_head = git("rev-parse", "HEAD", cwd=repo)
            expected_head = git(
                "rev-parse", f"{args.ref}^{{commit}}", cwd=repo
            )
            if cloned_head != expected_head:
                raise RuntimeError(
                    "clean-room HEAD mismatch: "
                    f"requested {args.ref} -> {expected_head}, got {cloned_head}"
                )
            if git(
                "status", "--porcelain", "--untracked-files=all", cwd=repo
            ):
                raise RuntimeError(
                    "fresh clone is unexpectedly dirty before reviewer execution"
                )
            report["delivery"] = {
                "mode": "fresh_clone",
                "repository_url": args.repository_url,
                "requested_ref": args.ref,
                "cloned_head": cloned_head,
            }

        python_exe = str(Path(args.python_exe).expanduser().resolve())
        rendered = workspace / "rendered"
        reviewer_command = [
            python_exe,
            "RUN_REVIEWER.py",
            "all",
            "--output-dir",
            str(rendered),
        ]
        if args.matlab:
            reviewer_command.extend(["--matlab", args.matlab])

        acceptance = run_logged(
            reviewer_command,
            cwd=repo,
            log_path=logs / "03_submission_v2_acceptance.log",
        )
        commands.append(acceptance)
        if acceptance["returncode"]:
            raise RuntimeError("submission-v2 reviewer acceptance failed")

        png_count = len(list(rendered.glob("*.png")))
        pdf_count = len(list(rendered.glob("*.pdf")))
        if png_count != 8 or pdf_count != 8:
            raise RuntimeError(
                f"render inventory mismatch: {png_count} PNG, {pdf_count} PDF"
            )
        report["render_inventory"] = {
            "png": png_count,
            "pdf": pdf_count,
            "directory": str(rendered),
        }

        if (repo / ".git").exists():
            post_status = git(
                "status", "--porcelain", "--untracked-files=all", cwd=repo
            )
            if post_status:
                raise RuntimeError(
                    "clean-room clone became dirty after reviewer execution:\n"
                    + post_status
                )
            report["post_run_git_status"] = "CLEAN"

        report["status"] = "PASS"
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("\n=== CMDO SUBMISSION-V2 CLEANROOM REVIEWER PASS ===")
        print("Report:", report_path)
        return 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(
            f"\nCMDO submission-v2 clean-room reviewer FAILED: {exc}",
            file=sys.stderr,
        )
        print("Report:", report_path, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
