"""Byte-verified portable bootstrap and prerequisite gates for CMDO replay."""
from __future__ import annotations

import json
import os
import sys
import zipfile
import importlib.metadata
from pathlib import Path
from typing import Any

from .errors import BlockedError, IntegrityError
from .hashing import sha256_file


REPLAY_EXACT_VERSIONS = {
    "numpy": "1.26.4",
    "pandas": "2.2.3",
    "scipy": "1.13.1",
    "scikit-learn": "1.5.2",
    "matplotlib": "3.9.2",
    "pydicom": "3.0.1",
    "isic-cli": "12.4.0",
    "pylibjpeg": "2.0.1",
    "pylibjpeg-libjpeg": "2.0.1",
}
REPLAY_BASE_VERSIONS = {
    "torch": "2.6.0",
    "torchvision": "0.21.0",
}


def verify_replay_python_environment() -> dict[str, Any]:
    problems: list[str] = []
    if sys.version_info[:2] != (3, 11):
        problems.append(f"Python {sys.version_info.major}.{sys.version_info.minor} detected; published replay baseline requires Python 3.11.x")
    observed: dict[str, str] = {}
    for distribution, expected in REPLAY_EXACT_VERSIONS.items():
        try:
            value = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            problems.append(f"{distribution}: missing (expected {expected})")
            continue
        observed[distribution] = value
        if value != expected:
            problems.append(f"{distribution}: {value} (expected exactly {expected})")
    for distribution, expected_base in REPLAY_BASE_VERSIONS.items():
        try:
            value = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            problems.append(f"{distribution}: missing (expected {expected_base}, local CUDA suffix allowed)")
            continue
        observed[distribution] = value
        if value.split("+")[0] != expected_base:
            problems.append(f"{distribution}: {value} (expected base version {expected_base})")
    if problems:
        raise BlockedError(
            "BLOCKED_REPLAY_ENVIRONMENT",
            "Python replay environment does not match the published baseline",
            details=problems + ["Create/reinstall the environment from environment/requirements-replay.txt before running scientific stages."],
        )
    return {"python": sys.version.split()[0], "packages": observed}

PORTABLE_ROOT = Path(__file__).resolve().parents[1] / "bootstrap_inputs" / "portable"
FRESH_BUNDLES = (
    "CMDO-T1R-Historical-Bootstrap-v0.1.zip",
    "CMDO-T2D-Historical-Bootstrap-v0.1.zip",
    "CMDO-T2E-Historical-Bootstrap-v0.1.zip",
)
ARCHIVAL_BUNDLES = (
    "CMDO-Archival-Accepted-Parents-v0.1.zip",
    "CMDO-Archival-T2F-Accepted-Parent-v0.1.zip",
    "CMDO-Archival-T2G-T2J-Immutable-Companions-v0.1.zip",
    "CMDO-Archival-T2J-Upstream-Manifests-v0.1.zip",
)
ABORTED_PROTOCOL_NAME = "Stage11E-R_Protocol_Seal_v0.1_ABORTED_PREEXECUTION_MIXED_ENDPOINT_ASSUMPTION.json"
ABORTED_PROTOCOL_SHA256 = "7f5a6450c3341fb1ef067dff5b89f186ce0142fdc8d38648607cd74843fa1a77"
ABORTED_PROTOCOL_SIZE = 2370
ABORTED_PROTOCOL_RUNTIME = Path(
    "06_Data_Records/Cross_Modal/"
    "Stage11E-R_Development_Only_Source_Recoverability_And_Axis_Freeze_v0.1/00_Protocol/"
    + ABORTED_PROTOCOL_NAME
)


def _safe_destination(project_root: Path, relative: str) -> Path:
    root = project_root.resolve()
    destination = (root / relative).resolve()
    if destination != root and root not in destination.parents:
        raise IntegrityError(f"bootstrap path escapes project root: {relative}")
    return destination


def _write_verified(data: bytes, destination: Path, *, size: int, digest: str) -> str:
    if len(data) != size:
        raise IntegrityError(f"bootstrap member size mismatch: {destination}")
    import hashlib
    observed = hashlib.sha256(data).hexdigest()
    if observed != digest:
        raise IntegrityError(f"bootstrap member hash mismatch: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size != size or sha256_file(destination) != digest:
            raise BlockedError(
                "BLOCKED_BOOTSTRAP_CONFLICT",
                f"existing runtime file conflicts with byte-verified bootstrap: {destination}",
                details=["Use a clean project root or preserve/move the conflicting file; it will not be overwritten."],
            )
        return "reused"
    destination.write_bytes(data)
    if destination.stat().st_size != size or sha256_file(destination) != digest:
        raise IntegrityError(f"bootstrap write verification failed: {destination}")
    return "materialized"


def materialize_bootstrap_zip(bundle: Path, project_root: Path) -> dict[str, Any]:
    if not bundle.is_file():
        raise BlockedError(
            "BLOCKED_PORTABLE_BOOTSTRAP_MISSING",
            f"portable bootstrap is missing: {bundle.name}",
            details=["Use the reviewer portable bundle; large historical bootstrap bytes are intentionally not stored on GitHub."],
        )
    records = []
    with zipfile.ZipFile(bundle) as archive:
        if "BOOTSTRAP_MANIFEST.json" not in archive.namelist():
            raise IntegrityError(f"bootstrap manifest missing: {bundle}")
        manifest = json.loads(archive.read("BOOTSTRAP_MANIFEST.json").decode("utf-8"))
        files = manifest.get("files", [])
        if int(manifest.get("file_count", len(files))) != len(files):
            raise IntegrityError(f"bootstrap file_count mismatch: {bundle}")
        for row in files:
            rel = str(row["relative_path"])
            if rel not in archive.namelist():
                raise IntegrityError(f"bootstrap member absent: {rel}")
            destination = _safe_destination(project_root, rel)
            status = _write_verified(
                archive.read(rel), destination,
                size=int(row["size_bytes"]), digest=str(row["sha256"]).lower(),
            )
            records.append({"relative_path": rel, "status": status, "sha256": row["sha256"]})
    return {
        "bundle": bundle.name,
        "bundle_sha256": sha256_file(bundle),
        "classification": manifest.get("classification", "BYTE_VERIFIED_HISTORICAL_BOOTSTRAP"),
        "files": records,
    }


def _materialize_aborted_protocol(project_root: Path) -> dict[str, Any]:
    source = PORTABLE_ROOT / ABORTED_PROTOCOL_NAME
    if not source.is_file() or source.stat().st_size != ABORTED_PROTOCOL_SIZE or sha256_file(source) != ABORTED_PROTOCOL_SHA256:
        raise BlockedError(
            "BLOCKED_PORTABLE_BOOTSTRAP_MISSING",
            "Stage11E-R historical aborted pre-execution protocol record is missing or corrupt",
        )
    destination = _safe_destination(project_root, ABORTED_PROTOCOL_RUNTIME.as_posix())
    status = _write_verified(source.read_bytes(), destination, size=ABORTED_PROTOCOL_SIZE, digest=ABORTED_PROTOCOL_SHA256)
    return {"relative_path": ABORTED_PROTOCOL_RUNTIME.as_posix(), "status": status, "sha256": ABORTED_PROTOCOL_SHA256}


def prepare_fresh_bootstraps(project_root: Path) -> list[dict[str, Any]]:
    records = [materialize_bootstrap_zip(PORTABLE_ROOT / name, project_root) for name in FRESH_BUNDLES]
    records.append({"bundle": ABORTED_PROTOCOL_NAME, "files": [_materialize_aborted_protocol(project_root)]})
    return records


def prepare_archival_parents(project_root: Path) -> list[dict[str, Any]]:
    """Materialize the declared byte-verified archival accepted-parent frontier.

    T2-D/T2-E were already historical parents of the archival profile. A current
    Windows/Python 3.11 archival attempt subsequently failed T2-F's immutable
    AMW-U exact-parent reproduction assertion. The accepted historical T2-F
    records are therefore a separate, explicitly classified archival parent
    bundle. Historical T2-G/T2-H/T2-I/T2-J companion documents and registries are
    materialized from a separate byte-verified bundle because the Drive-era
    implementations require them before execution. This repairs packaging only
    and does not represent T2-F or any fresh upstream stage as reproduced.
    """
    return [
        materialize_bootstrap_zip(PORTABLE_ROOT / name, project_root)
        for name in ARCHIVAL_BUNDLES
    ]


def verify_historical_receipts(repository_root: Path, project_root: Path) -> list[dict[str, Any]]:
    manifest = json.loads((repository_root / "provenance/historical_receipts.json").read_text(encoding="utf-8"))
    receipt_root = project_root / manifest["root"]
    problems = []
    records = []
    for row in manifest["files"]:
        path = receipt_root / row["relative_path"]
        if not path.is_file():
            problems.append(f"{row['id']}: missing {path}")
            continue
        if path.stat().st_size != int(row["size_bytes"]):
            problems.append(f"{row['id']}: size mismatch at {path}")
            continue
        observed = sha256_file(path)
        if observed != row["sha256"]:
            problems.append(f"{row['id']}: SHA-256 mismatch at {path}")
            continue
        records.append({"id": row["id"], "path": str(path), "sha256": observed})
    if problems:
        raise BlockedError(
            "BLOCKED_HISTORICAL_RECEIPTS",
            "Stage11C-R requires six byte-exact historical official receipt files",
            details=problems + ["These are historical prerequisites, not fresh provider downloads."],
        )
    return records


def check_windows_path_budget(project_root: Path, run_dir: Path) -> dict[str, Any]:
    # The T1-R adapted notebook applies Win32 extended-length addressing to the
    # project tree. We still reject obviously hazardous root choices early.
    project_len = len(str(project_root.resolve()))
    run_len = len(str(run_dir.resolve()))
    if os.name == "nt" and (project_len > 120 or run_len > 160):
        raise BlockedError(
            "BLOCKED_WINDOWS_PATH_BUDGET",
            "selected Windows roots are too long for the historical replay tree",
            details=[
                f"project root length={project_len}; use a short root such as C:\\Users\\<you>\\P",
                f"run root length={run_len}; use a short output root such as C:\\Users\\<you>\\R",
            ],
        )
    return {"project_root_length": project_len, "run_root_length": run_len, "t1r_extended_length_adapter": True}
