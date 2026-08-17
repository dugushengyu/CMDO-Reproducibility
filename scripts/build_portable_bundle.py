#!/usr/bin/env python3
"""Build and byte-verify the reviewer portable ZIP without restricted raw data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "CMDO-Reproducibility"
DEFAULT_NAME = "CMDO-Reproducibility-Reviewer-Portable-v1.0.zip"
FIXED_TIME = (2026, 8, 17, 0, 0, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_files() -> list[Path]:
    forced_roots = [
        ROOT / "data/canonical_records",
        ROOT / "data/frozen_assets",
        ROOT / "bootstrap_inputs/portable",
    ]
    relative: list[Path] = []
    if (ROOT / ".git").exists():
        process = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        )
        relative.extend(
            Path(value.decode("utf-8"))
            for value in process.stdout.split(b"\0")
            if value
        )
    else:
        relative.extend(
            path.relative_to(ROOT)
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )
    for directory in forced_roots:
        if directory.is_dir():
            relative.extend(path.relative_to(ROOT) for path in directory.rglob("*") if path.is_file())
    excluded_prefixes = ("outputs/", "dist/", ".git/", ".venv/", ".venv-cleanroom/", "__pycache__/")
    excluded_exact = {
        "config/local_paths.json",
        "PORTABLE_MANIFEST_SHA256.csv",
        "PORTABLE_PACKAGE_INFO.json",
    }
    files = []
    for rel in sorted(set(relative), key=lambda item: item.as_posix()):
        value = rel.as_posix()
        path = ROOT / rel
        if value in excluded_exact or value.startswith(excluded_prefixes):
            continue
        if "__pycache__" in rel.parts:
            continue
        if not path.is_file() or path.is_symlink():
            continue
        files.append(path)
    return files


def git_metadata() -> dict[str, object]:
    declared = os.environ.get("CMDO_SOURCE_COMMIT", "").strip()
    if (ROOT / ".git").exists():
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True,
        ).stdout
        return {"git_commit": declared or revision, "git_worktree_dirty": bool(status.strip())}
    return {
        "git_commit": declared or "UNPUBLISHED_RECONSTRUCTED_WORKTREE",
        "git_worktree_dirty": None,
    }


def manifest_text(records: list[dict[str, object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=["relative_path", "size_bytes", "sha256", "distribution"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue()


def write_member(archive: zipfile.ZipFile, name: str, data: bytes, *, compression: int) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
    info.compress_type = compression
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    archive.writestr(info, data, compresslevel=9 if compression == zipfile.ZIP_DEFLATED else None)


def build(output: Path, *, require_reviewer_assets: bool) -> dict[str, object]:
    files = repository_files()
    revision = git_metadata()
    records = []
    payloads: list[tuple[str, bytes, int]] = []
    stored_suffixes = {".zip", ".npz", ".pt", ".xlsx", ".png", ".jpg", ".jpeg"}
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        distribution = (
            "PORTABLE_ONLY_GITIGNORED"
            if relative.startswith(("data/canonical_records/", "data/frozen_assets/", "bootstrap_inputs/portable/"))
            else "GIT_PUBLICATION_CANDIDATE"
        )
        records.append(
            {
                "relative_path": relative,
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
                "distribution": distribution,
            }
        )
        compression = zipfile.ZIP_STORED if path.suffix.lower() in stored_suffixes else zipfile.ZIP_DEFLATED
        payloads.append((f"{PREFIX}/{relative}", data, compression))

    canonical_count = sum(
        row["relative_path"].startswith("data/canonical_records/")
        and row["relative_path"].endswith(".zip")
        for row in records
    )
    u2_asset_count = sum(row["relative_path"].startswith("data/frozen_assets/u2/") for row in records)
    bootstrap_count = sum(row["relative_path"].startswith("bootstrap_inputs/portable/") for row in records)
    if require_reviewer_assets and canonical_count != 7:
        raise RuntimeError(f"submission portable bundle requires 7 canonical archives, found {canonical_count}")

    manifest = manifest_text(records).encode("utf-8")
    package_info = json.dumps(
        {
            "schema_version": 1,
            "package": output.name,
            "classification": "REVIEWER_PORTABLE_REPRODUCTION_PACKAGE",
            "raw_restricted_data_included": False,
            "u9_eicu_data_included": False,
            "canonical_figure_archives_included": canonical_count,
            "u2_authoritative_asset_files_included": u2_asset_count,
            "u2_authoritative_checkpoint_and_prediction_caches_included": u2_asset_count > 0,
            "scientific_full_replay_executed_during_packaging": False,
            "fresh_full_claim_may_terminate_at_declared_scientific_boundary": True,
            "fresh_boundary_stage": "t2d_witness",
            "fresh_boundary_exit_code": 4,
            "archival_continuation_is_not_fresh_reproduction": True,
            "historical_bootstrap_files_included": bootstrap_count,
            "historical_bootstrap_archives_included": bootstrap_count > 0,
            "entrypoint": "python RUN_REVIEWER.py all --allow-network",
            **revision,
            "manifest_sha256": sha256_bytes(manifest),
            "file_count": len(records),
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        for name, data, compression in payloads:
            write_member(archive, name, data, compression=compression)
        write_member(
            archive,
            f"{PREFIX}/PORTABLE_MANIFEST_SHA256.csv",
            manifest,
            compression=zipfile.ZIP_DEFLATED,
        )
        write_member(
            archive,
            f"{PREFIX}/PORTABLE_PACKAGE_INFO.json",
            package_info,
            compression=zipfile.ZIP_DEFLATED,
        )
    return {
        "output": str(output),
        "size_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "file_count": len(records),
        "manifest_sha256": sha256_bytes(manifest),
        "canonical_archive_count": canonical_count,
    }


def verify(output: Path, *, require_reviewer_assets: bool) -> dict[str, object]:
    with zipfile.ZipFile(output) as archive:
        broken = archive.testzip()
        if broken:
            raise RuntimeError(f"corrupt ZIP member: {broken}")
        manifest_name = f"{PREFIX}/PORTABLE_MANIFEST_SHA256.csv"
        rows = list(
            csv.DictReader(io.StringIO(archive.read(manifest_name).decode("utf-8")))
        )
        for row in rows:
            member = f"{PREFIX}/{row['relative_path']}"
            data = archive.read(member)
            if len(data) != int(row["size_bytes"]):
                raise RuntimeError(f"portable size mismatch: {member}")
            if sha256_bytes(data) != row["sha256"]:
                raise RuntimeError(f"portable hash mismatch: {member}")
        info = json.loads(archive.read(f"{PREFIX}/PORTABLE_PACKAGE_INFO.json"))
        if info["raw_restricted_data_included"] is not False or info["u9_eicu_data_included"] is not False:
            raise RuntimeError("portable package incorrectly claims restricted/deferred data")
        if len(rows) != info["file_count"]:
            raise RuntimeError("portable manifest file count mismatch")
        if require_reviewer_assets and info["canonical_figure_archives_included"] != 7:
            raise RuntimeError("portable package does not contain all seven canonical reviewer archives")
    return {
        "output": str(output),
        "size_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "verified_members": len(rows),
        "canonical_archive_count": info["canonical_figure_archives_included"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / DEFAULT_NAME)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--require-reviewer-assets", action="store_true")
    args = parser.parse_args()
    if not args.verify_only:
        result = build(args.output, require_reviewer_assets=args.require_reviewer_assets)
        print("CMDO portable bundle WRITTEN", json.dumps(result, sort_keys=True))
    verified = verify(args.output, require_reviewer_assets=args.require_reviewer_assets)
    sidecar = args.output.with_suffix(args.output.suffix + ".sha256")
    sidecar.write_text(f"{verified['sha256']}  {args.output.name}\n", encoding="utf-8", newline="\n")
    print("CMDO portable bundle PASS", json.dumps(verified, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
