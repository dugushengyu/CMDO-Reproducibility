"""Non-destructive local adapters for immutable Drive-era source files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .hashing import sha256_file


COLAB_MOUNT = re.compile(
    r"^\s*(?:from\s+google\.colab\s+import\s+drive|drive\.mount\s*\([^\n]*\))\s*$",
    re.MULTILINE,
)


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
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
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
        "source_mutated": False,
    }


def adapt_source(source: Path, destination: Path, project_root: Path) -> dict[str, object]:
    if source.suffix.lower() == ".py":
        return adapt_python(source, destination, project_root)
    if source.suffix.lower() == ".ipynb":
        return adapt_notebook(source, destination, project_root)
    raise ValueError(f"unsupported adaptable source: {source}")
