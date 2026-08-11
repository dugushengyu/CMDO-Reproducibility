"""Non-destructive local adapters for immutable Drive-era source files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .hashing import sha256_file


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ISIC_CLI_RUNTIME_PIN = "12.4.0"  # newest release compatible with Python 3.11
STAGE8_NOTEBOOK_NAME = (
    "CrossModal_Stage8_CrossModality_EdgeLibrary_Expansion_And_Protocol_Seal_v0.1.ipynb"
)
REQUIRED_STAGE7_PARENT_IDS = {
    "STAGE7_FINAL_RECORD",
    "STAGE7_EDGE_MATRIX",
    "STAGE7_DDO2_DISCOVERY_CANDIDATES",
}


COLAB_MOUNT = re.compile(
    r"^\s*(?:from\s+google\.colab\s+import\s+drive|drive\.mount\s*\([^\n]*\))\s*$",
    re.MULTILINE,
)


def _materialize_historical_parent_inputs(project_root: Path) -> list[dict[str, object]]:
    """Restore byte-verified Stage 7 parent records required by Stage 8/Stage 9.

    Stage 7 is a frozen historical parent of the accepted Stage 8-to-U8 replay,
    not a stage re-executed by the full-claim profile. Existing runtime files are
    reused only when their byte identity matches the declared provenance.
    """

    manifest_path = REPOSITORY_ROOT / "provenance/historical_parent_inputs.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"historical parent manifest is missing: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    project_root = project_root.resolve()
    records: list[dict[str, object]] = []
    for row in payload.get("inputs", []):
        source = (REPOSITORY_ROOT / row["repository_path"]).resolve()
        if REPOSITORY_ROOT not in source.parents or not source.is_file():
            raise RuntimeError(f"historical parent source is missing or unsafe: {source}")
        expected_size = int(row["size_bytes"])
        expected_sha = str(row["sha256"]).lower()
        if source.stat().st_size != expected_size or sha256_file(source) != expected_sha:
            raise RuntimeError(f"historical parent source integrity mismatch: {source}")

        destination = (project_root / row["runtime_path"]).resolve()
        if project_root not in destination.parents:
            raise RuntimeError(f"historical parent runtime path escapes project root: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.stat().st_size != expected_size or sha256_file(destination) != expected_sha:
                raise RuntimeError(f"historical parent runtime conflict: {destination}")
        else:
            destination.write_bytes(source.read_bytes())
        if destination.stat().st_size != expected_size or sha256_file(destination) != expected_sha:
            raise RuntimeError(f"historical parent materialization failed: {destination}")
        records.append(
            {
                "id": row["id"],
                "runtime_path": str(destination),
                "size_bytes": expected_size,
                "sha256": expected_sha,
                "bytes_unchanged": True,
            }
        )

    actual_ids = {str(record["id"]) for record in records}
    if actual_ids != REQUIRED_STAGE7_PARENT_IDS:
        raise RuntimeError(
            "historical parent manifest must contain the complete Stage 7 parent set; "
            f"expected={sorted(REQUIRED_STAGE7_PARENT_IDS)} actual={sorted(actual_ids)}"
        )
    return records


def _adapt_text(text: str, project_root: Path) -> tuple[str, int]:
    root = project_root.resolve().as_posix()
    parent = project_root.resolve().parent.as_posix()
    replacements = [
        ("/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability", root),
        ("/tmp/Cross-Modal_Diagnostic_Observability", root),
        ("/mnt/data/Cross-Modal_Diagnostic_Observability", root),
        ("/tmp/cmdo_fake_drive", parent),
        ("/content/drive/Shareddrives", parent),
        ("/content/drive/MyDrive", parent),
        # The immutable Drive-era sources pin isic-cli 12.5.2, which now
        # requires Python >=3.12. The replay baseline is Python 3.11, so the
        # non-destructive runtime copy uses the last compatible CLI release.
        ("isic-cli==12.5.2", f"isic-cli=={ISIC_CLI_RUNTIME_PIN}"),
    ]
    count = 0
    adapted = text
    for old, new in replacements:
        occurrences = adapted.count(old)
        adapted = adapted.replace(old, new)
        count += occurrences
    adapted, mount_count = COLAB_MOUNT.subn(
        "# CMDO local adapter: Colab Drive mount omitted", adapted
    )
    return adapted, count + mount_count


def adapt_python(source: Path, destination: Path, project_root: Path) -> dict[str, object]:
    original = source.read_text(encoding="utf-8-sig")
    adapted, replacement_count = _adapt_text(original, project_root)
    compile(adapted, str(destination), "exec")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(adapted, encoding="utf-8")
    return {
        "source": source.as_posix(),
        "destination": destination.as_posix(),
        "source_sha256": sha256_file(source),
        "adapted_sha256": sha256_file(destination),
        "replacement_count": replacement_count,
        "runtime_dependency_adaptations": (
            [f"isic-cli==12.5.2 -> isic-cli=={ISIC_CLI_RUNTIME_PIN}"]
            if "isic-cli==12.5.2" in original
            else []
        ),
        "source_mutated": False,
    }


def _compile_notebook_cells(payload: dict[str, object], label: str) -> None:
    for index, cell in enumerate(payload.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        filtered = "\n".join(
            line
            for line in source.splitlines()
            if not line.lstrip().startswith(("%", "!"))
        )
        if not filtered.strip():
            continue
        try:
            compile(filtered, f"{label}:cell-{index}", "exec")
        except SyntaxError as exc:
            # IPython help syntax and multiline shell blocks remain valid in a notebook
            # but are not valid in CPython's compile(). They are checked by nbformat later.
            if "?" not in filtered and "get_ipython" not in filtered:
                raise exc


def adapt_notebook(
    source: Path, destination: Path, project_root: Path
) -> dict[str, object]:
    historical_parent_inputs: list[dict[str, object]] = []
    if source.name == STAGE8_NOTEBOOK_NAME:
        historical_parent_inputs = _materialize_historical_parent_inputs(project_root)

    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    original_has_isic_1252 = any(
        "isic-cli==12.5.2" in "".join(cell.get("source", []))
        for cell in payload.get("cells", [])
        if cell.get("cell_type") == "code"
    )
    replacement_count = 0
    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        original = "".join(cell.get("source", []))
        adapted, count = _adapt_text(original, project_root)
        replacement_count += count
        cell["source"] = adapted.splitlines(keepends=True)
        cell["execution_count"] = None
        cell["outputs"] = []
    _compile_notebook_cells(payload, destination.as_posix())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return {
        "source": source.as_posix(),
        "destination": destination.as_posix(),
        "source_sha256": sha256_file(source),
        "adapted_sha256": sha256_file(destination),
        "replacement_count": replacement_count,
        "runtime_dependency_adaptations": (
            [f"isic-cli==12.5.2 -> isic-cli=={ISIC_CLI_RUNTIME_PIN}"]
            if original_has_isic_1252
            else []
        ),
        "historical_parent_inputs": historical_parent_inputs,
        "source_mutated": False,
    }


def adapt_source(source: Path, destination: Path, project_root: Path) -> dict[str, object]:
    if source.suffix.lower() == ".py":
        return adapt_python(source, destination, project_root)
    if source.suffix.lower() == ".ipynb":
        return adapt_notebook(source, destination, project_root)
    raise ValueError(f"unsupported adaptable source: {source}")
