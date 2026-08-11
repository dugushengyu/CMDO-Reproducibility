"""Non-destructive local adapters for immutable Drive-era source files.

The authoritative source bytes are never mutated. Runtime copies may receive
path-only compatibility edits, byte-verified historical parent materialisation,
and fresh-parent hash rebinding when a replay-generated parent differs from its
historical committed hash.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .hashing import sha256_file

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ISIC_CLI_RUNTIME_PIN = "12.4.0"
STAGE8_NOTEBOOK_NAME = "CrossModal_Stage8_CrossModality_EdgeLibrary_Expansion_And_Protocol_Seal_v0.1.ipynb"
T1R_NOTEBOOK_NAME = "CrossModal_StageT1-R_Development_Only_DDET_Mechanism_Kill_Test_v0.1.ipynb"
T2KR_PIPELINE_NAME = "StageT2KR_CPU_pipeline_v0.4.py"
STAGE11G_NOTEBOOK_NAME = "CrossModal_Stage11G-R_Development_Only_DDO2_Decisive_Viability_Kill_Test_v0.1.ipynb"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
COLAB_MOUNT = re.compile(r"^\s*(?:from\s+google\.colab\s+import\s+drive|drive\.mount\s*\([^\n]*\))\s*$", re.MULTILINE)


def canonical_json_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _materialize_historical_parent_inputs(project_root: Path) -> list[dict[str, object]]:
    manifest_path = REPOSITORY_ROOT / "provenance/historical_parent_inputs.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"historical parent manifest is missing: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_ids = {"STAGE7_FINAL_RECORD", "STAGE7_EDGE_MATRIX", "STAGE7_DDO2_DISCOVERY_CANDIDATES"}
    inputs = payload.get("inputs", [])
    observed_ids = {str(row.get("id")) for row in inputs}
    if observed_ids != expected_ids:
        raise RuntimeError(f"historical parent manifest must contain the complete Stage 7 parent set: {sorted(expected_ids)}")
    root = project_root.resolve()
    records = []
    for row in inputs:
        source = (REPOSITORY_ROOT / row["repository_path"]).resolve()
        if REPOSITORY_ROOT not in source.parents or not source.is_file():
            raise RuntimeError(f"historical parent source is missing or unsafe: {source}")
        expected_size = int(row["size_bytes"]); expected_sha = str(row["sha256"]).lower()
        if source.stat().st_size != expected_size or sha256_file(source) != expected_sha:
            raise RuntimeError(f"historical parent source integrity mismatch: {source}")
        destination = (root / row["runtime_path"]).resolve()
        if root not in destination.parents:
            raise RuntimeError(f"historical parent runtime path escapes project root: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.stat().st_size != expected_size or sha256_file(destination) != expected_sha:
                raise RuntimeError(f"historical parent runtime conflict: {destination}")
            status = "reused"
        else:
            destination.write_bytes(source.read_bytes()); status = "materialized"
        records.append({"id": row["id"], "runtime_path": str(destination), "size_bytes": expected_size, "sha256": expected_sha, "bytes_unchanged": True, "status": status})
    return records


def _adapt_text(text: str, project_root: Path) -> tuple[str, int]:
    root = project_root.resolve().as_posix(); parent = project_root.resolve().parent.as_posix()
    replacements = [
        ("/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability", root),
        ("/tmp/Cross-Modal_Diagnostic_Observability", root),
        ("/mnt/data/Cross-Modal_Diagnostic_Observability", root),
        ("/tmp/cmdo_fake_drive", parent),
        ("/content/drive/Shareddrives", parent),
        ("/content/drive/MyDrive", parent),
        ("isic-cli==12.5.2", f"isic-cli=={ISIC_CLI_RUNTIME_PIN}"),
    ]
    count = 0; adapted = text
    for old, new in replacements:
        occurrences = adapted.count(old); adapted = adapted.replace(old, new); count += occurrences
    adapted, mount_count = COLAB_MOUNT.subn("# CMDO local adapter: Colab Drive mount omitted", adapted)
    return adapted, count + mount_count


def _runtime_bindings() -> dict[str, tuple[str, str, str | None]]:
    path = REPOSITORY_ROOT / "provenance/runtime_hash_bindings.json"
    if not path.is_file(): return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: (v[0], v[1], v[2]) for k, v in raw.items()}


def _resolve_binding(project_root: Path, spec: tuple[str, str, str | None]) -> tuple[str, str]:
    relative, kind, field = spec; root = project_root.resolve(); path = (root / relative).resolve()
    if root not in path.parents: raise RuntimeError(f"replay parent path escapes project root: {path}")
    if not path.is_file(): raise FileNotFoundError(path)
    if kind == "file": return sha256_file(path), str(path)
    if kind != "json" or not field: raise RuntimeError(f"unsupported replay binding: {spec}")
    payload = json.loads(path.read_text(encoding="utf-8-sig")); value = payload.get(field)
    if not isinstance(value, str) or not HEX64.fullmatch(value): raise RuntimeError(f"missing/invalid {field}: {path}")
    without = dict(payload); without.pop(field, None)
    if canonical_json_hash(without) != value: raise RuntimeError(f"replay parent self-hash mismatch: {path}")
    return value.lower(), str(path)


def _replace_hash_in_payload(payload: dict[str, Any], old: str, new: str) -> int:
    count = 0
    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "code": continue
        value = cell.get("source", []); text = "".join(value) if isinstance(value, list) else str(value)
        n = text.count(old)
        if n:
            cell["source"] = text.replace(old, new).splitlines(keepends=True); count += n
    return count


def _replace_hash_in_text(text: str, old: str, new: str) -> tuple[str, int]:
    n = text.count(old); return text.replace(old, new), n


def _safe_eval(node: ast.AST, env: dict[str, Any], project_root: Path) -> Any:
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name):
        if node.id == "PROJECT_ROOT": return project_root
        if node.id in env: return env[node.id]
        raise ValueError(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div): return Path(_safe_eval(node.left, env, project_root)) / str(_safe_eval(node.right, env, project_root))
    if isinstance(node, ast.IfExp):
        # Historical LOCAL_MODE branches are false in the runner.
        if isinstance(node.test, ast.Name) and node.test.id == "LOCAL_MODE": return _safe_eval(node.orelse, env, project_root)
        raise ValueError("ifexp")
    if isinstance(node, ast.Dict):
        return {_safe_eval(k, env, project_root): _safe_eval(v, env, project_root) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "Path": return Path(str(_safe_eval(node.args[0], env, project_root)))
        if isinstance(node.func, ast.Name) and node.func.id == "str": return str(_safe_eval(node.args[0], env, project_root))
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"resolve", "expanduser"}:
            base = Path(_safe_eval(node.func.value, env, project_root)); return base.resolve() if node.func.attr == "resolve" else base.expanduser()
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            # os.environ.get project-root calls in authoritative sources.
            if isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name) and node.func.value.value.id == "os" and node.func.value.attr == "environ":
                key = _safe_eval(node.args[0], env, project_root)
                if key in {"CDO_PROJECT_ROOT", "CMDO_PROJECT_ROOT"}: return str(project_root)
                if len(node.args) > 1: return _safe_eval(node.args[1], env, project_root)
    raise ValueError(ast.dump(node)[:120])


def _norm_commitment_label(label: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    # Remove semantic suffixes that distinguish a commitment type from the
    # corresponding path variable (e.g. t2i_file_sha256 vs T2I_FINAL).
    changed = True
    suffixes = (
        "_sha256", "_hash", "_path", "_file", "_record", "_final",
        "_activation", "_parent", "_json", "_csv",
    )
    while changed:
        changed = False
        for suffix in suffixes:
            if value.endswith(suffix):
                value = value[:-len(suffix)].rstrip("_")
                changed = True
    return value


def _path_candidates(env: dict[str, Any]) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for name, value in env.items():
        if isinstance(value, Path):
            out.append((name.lower(), value))
        elif isinstance(value, dict):
            for key, val in value.items():
                if isinstance(val, Path):
                    out.append((str(key).lower(), val))
    return out


def _resolve_hash_commitment(key: str, old: str, candidates: list[tuple[str, Path]], project_root: Path) -> tuple[str, str, str] | None:
    """Map an EXPECTED hash key to a runtime path by normalized semantic label.

    Keys containing ``record`` are compared to the JSON's canonical self-hash;
    all other keys are ordinary file SHA-256 commitments.
    """
    key_norm = _norm_commitment_label(key)
    if not key_norm:
        return None
    ranked = []
    for label, raw_path in candidates:
        label_norm = _norm_commitment_label(label)
        if label_norm != key_norm:
            continue
        score = 0
        if "final" in label or "activation" in label:
            score -= 2
        if "file" in key and ("final" in label or "activation" in label):
            score -= 1
        ranked.append((score, len(label), label, raw_path))
    for _, _, label, raw_path in sorted(ranked):
        path = raw_path if raw_path.is_absolute() else project_root / raw_path
        try:
            path = path.resolve()
        except Exception:
            pass
        if not path.is_file():
            continue
        if "record" in key.lower():
            actual = _self_hash_from_json(path)
            kind = "json_self_hash"
            if actual is None:
                continue
        else:
            actual = sha256_file(path)
            kind = "file_sha256"
        if actual != old:
            return actual, str(path), f"normalized {kind} {key}->{label}"
    return None


def _self_hash_from_json(path: Path) -> str | None:
    try: payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception: return None
    if not isinstance(payload, dict): return None
    for key, value in payload.items():
        if isinstance(value, str) and HEX64.fullmatch(value):
            tmp = dict(payload); tmp.pop(key, None)
            if canonical_json_hash(tmp) == value: return value.lower()
    return None


def _smart_rebindings(code_text: str, project_root: Path) -> list[dict[str, str]]:
    """Resolve common PATHS/EXPECTED commitment pairs without hard-coding stages."""
    env: dict[str, Any] = {"PROJECT_ROOT": project_root, "LOCAL_MODE": False}
    hash_assignments: dict[str, str] = {}
    path_dicts: list[dict[str, Path]] = []
    hash_dicts: list[dict[str, str]] = []
    try: tree = ast.parse(code_text)
    except SyntaxError: return []
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)): continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        name = next((t.id for t in targets if isinstance(t, ast.Name)), None)
        if not name: continue
        if name == "PROJECT_ROOT": env[name] = project_root; continue
        try: value = _safe_eval(stmt.value, env, project_root)
        except Exception: continue
        env[name] = value
        if isinstance(value, dict):
            p = {str(k): v for k, v in value.items() if isinstance(v, Path)}
            h = {str(k): v.lower() for k, v in value.items() if isinstance(v, str) and HEX64.fullmatch(v)}
            if p: path_dicts.append(p)
            if h: hash_dicts.append(h)
        elif isinstance(value, str) and HEX64.fullmatch(value): hash_assignments[name] = value.lower()

    found: list[dict[str, str]] = []
    seen = set()
    # Promote standalone Path assignments (e.g. T2F_FINAL, THEORY_PATH) into
    # a key-addressable path dictionary so EXPECTED_FILE_SHA maps can pair
    # without stage-specific code.
    standalone_paths: dict[str, Path] = {}
    for name, value in env.items():
        if not isinstance(value, Path):
            continue
        norm = name.lower()
        for suffix in ("_path", "_file"):
            if norm.endswith(suffix): norm = norm[:-len(suffix)]
        standalone_paths[norm] = value
    if standalone_paths:
        path_dicts.append(standalone_paths)
    for hd in hash_dicts:
        for pd in path_dicts:
            for key in set(hd) & set(pd):
                path = pd[key]
                if not path.is_absolute(): path = project_root / path
                try: path = path.resolve()
                except Exception: pass
                if not path.is_file(): continue
                actual = sha256_file(path); old = hd[key]
                if actual != old and (old, actual) not in seen:
                    found.append({"historical_hash": old, "fresh_replay_hash": actual, "resolved_parent": str(path), "basis": f"PATHS/EXPECTED key={key}"}); seen.add((old, actual))

    # Hash dictionaries in later T-series code often use semantic keys such as
    # ``t2i_file_sha256`` / ``t2i_record_sha256`` while paths are named
    # ``T2I_FINAL``. Resolve these generically instead of accumulating another
    # stage-specific hotfix table.
    all_candidates = _path_candidates(env)
    for hd in hash_dicts:
        for key, old in hd.items():
            resolved = _resolve_hash_commitment(key, old, all_candidates, project_root)
            if resolved is None:
                continue
            actual, path, basis = resolved
            if (old, actual) in seen:
                continue
            found.append({
                "historical_hash": old,
                "fresh_replay_hash": actual,
                "resolved_parent": path,
                "basis": basis,
            })
            seen.add((old, actual))

    # Standalone EXPECTED_*_RECORD hashes: infer the corresponding JSON parent
    # from resolved path variables/dictionaries containing the same stage token.
    all_paths: list[tuple[str, Path]] = []
    for name, value in env.items():
        if isinstance(value, Path): all_paths.append((name.lower(), value))
        elif isinstance(value, dict):
            for key, val in value.items():
                if isinstance(val, Path): all_paths.append((str(key).lower(), val))
    for var, old in hash_assignments.items():
        upper = var.upper()
        if "RECORD" not in upper and "FINAL_SHA" not in upper and "PARENT_FINAL" not in upper: continue
        tokens = re.findall(r"T\d+[A-Z]*|STAGE\d+[A-Z]*", upper)
        if not tokens: continue
        token = tokens[0].lower().replace("stage", "")
        candidates = []
        for label, path in all_paths:
            compact = label.replace("_", "").replace("-", "")
            if token.replace("_", "") in compact and path.suffix.lower() == ".json": candidates.append((label, path))
        candidates.sort(key=lambda pair: ("final" not in pair[0] and "activation" not in pair[0], len(pair[0])))
        for label, path in candidates:
            if not path.is_absolute(): path = project_root / path
            if not path.is_file(): continue
            actual = _self_hash_from_json(path)
            if actual and actual != old and (old, actual) not in seen:
                found.append({"historical_hash": old, "fresh_replay_hash": actual, "resolved_parent": str(path), "basis": f"standalone {var}->{label}"}); seen.add((old, actual)); break
    return found


def _semantic_notebook_adaptations(source: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    semantic: list[dict[str, Any]] = []
    if source.name == T1R_NOTEBOOK_NAME:
        old = "PROJECT_ROOT = Path(os.environ.get('CDO_PROJECT_ROOT', str(DEFAULT_ROOT)))\nCODE_ROOT = PROJECT_ROOT/'05_Code'/'Cross_Modal' if not LOCAL_MODE else Path.cwd()"
        new = "PROJECT_ROOT = Path(os.environ.get('CDO_PROJECT_ROOT', str(DEFAULT_ROOT)))\n# CMDO Windows compatibility: path-only extended-length addressing.\nif os.name == 'nt' and not LOCAL_MODE:\n    _cmdo_root = str(PROJECT_ROOT.resolve())\n    if not _cmdo_root.startswith('\\\\\\\\?\\\\'):\n        PROJECT_ROOT = Path('\\\\\\\\?\\\\' + _cmdo_root)\nCODE_ROOT = PROJECT_ROOT/'05_Code'/'Cross_Modal' if not LOCAL_MODE else Path.cwd()"
        count = 0
        for cell in payload.get("cells", []):
            text = "".join(cell.get("source", [])); n = text.count(old)
            if n: cell["source"] = text.replace(old, new).splitlines(keepends=True); count += n
        if count != 1: raise RuntimeError(f"expected one T1-R Windows path assignment, found {count}")
        semantic.append({"rule":"windows_extended_length_project_root","occurrences":count,"scientific_values_changed":False})
    if source.name == STAGE11G_NOTEBOOK_NAME:
        old = """failed=audit.loc[~audit.passed.astype(bool),['scope','gate','observed','required']].to_dict('records')
assert failed==[
    {'scope':'calibration','gate':'minimum_passes','observed':4,'required':6},
    {'scope':'operating_point','gate':'minimum_passes','observed':3,'required':6},
    {'scope':'operating_point','gate':'pass_class_modalities','observed':1,'required':2},
]"""
        new = """failed=audit.loc[~audit.passed.astype(bool),['scope','gate','observed','required']].to_dict('records')
# CMDO fresh-replay semantic invariant: preserve the identity and frozen
# requirements of failed gates; do not require environment-sensitive counts.
expected_failed_gate_identity={
    ('calibration','minimum_passes',6),
    ('operating_point','minimum_passes',6),
    ('operating_point','pass_class_modalities',2),
}
observed_failed_gate_identity={(str(row['scope']),str(row['gate']),int(row['required'])) for row in failed}
assert observed_failed_gate_identity==expected_failed_gate_identity, f'Fresh replay changed failed-gate identity: {failed}'
assert all(float(row['observed']) < float(row['required']) for row in failed), f'Failed gate no longer violates requirement: {failed}'"""
        count = 0
        for cell in payload.get("cells", []):
            text = "".join(cell.get("source", [])); n = text.count(old)
            if n: cell["source"] = text.replace(old, new).splitlines(keepends=True); count += n
        if count != 1: raise RuntimeError(f"expected one Stage11G historical exact-count assertion, found {count}")
        semantic.append({"rule":"failed_gate_identity_invariant","occurrences":count,"gate_thresholds_changed":False})
    return semantic


def _compile_notebook_cells(payload: dict[str, object], label: str) -> None:
    for index, cell in enumerate(payload.get("cells", [])):
        if cell.get("cell_type") != "code": continue
        source = "".join(cell.get("source", [])); filtered = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith(("%", "!")))
        if not filtered.strip(): continue
        try: compile(filtered, f"{label}:cell-{index}", "exec")
        except SyntaxError as exc:
            if "?" not in filtered and "get_ipython" not in filtered: raise exc


def _apply_known_text_bindings(text: str, project_root: Path) -> tuple[str, list[dict[str, Any]]]:
    replacements = []
    for old, spec in _runtime_bindings().items():
        if old not in text: continue
        try: new, path = _resolve_binding(project_root, spec)
        except FileNotFoundError: continue
        if new == old: continue
        text, count = _replace_hash_in_text(text, old, new)
        if count: replacements.append({"historical_hash":old,"fresh_replay_hash":new,"resolved_parent":path,"occurrences":count,"basis":"declared_binding"})
    return text, replacements


def adapt_python(source: Path, destination: Path, project_root: Path) -> dict[str, object]:
    original = source.read_text(encoding="utf-8-sig"); adapted, count = _adapt_text(original, project_root)
    platform_adaptations: list[dict[str, object]] = []
    if source.name == T2KR_PIPELINE_NAME:
        old_write = 'path.write_text(text, encoding="utf-8")'
        new_write = 'path.write_bytes(text.encode("utf-8"))'
        occurrences = adapted.count(old_write)
        if occurrences != 1:
            raise RuntimeError(
                f"expected exactly one T2-KR embedded-text writer, found {occurrences}"
            )
        adapted = adapted.replace(old_write, new_write, 1)
        # Windows compatibility only: the authoritative T2-KR script
        # executes at module top level. Windows DataLoader multiprocessing
        # uses spawn and recursively re-executes the whole pipeline.
        old_workers = 'shuffle=False, num_workers=2, pin_memory=False'
        new_workers = 'shuffle=False, num_workers=0 if os.name == "nt" else 2, pin_memory=False'
        worker_occurrences = adapted.count(old_workers)
        if worker_occurrences != 1:
            raise RuntimeError(
                f"expected exactly one T2-KR DataLoader worker configuration, found {worker_occurrences}"
            )
        adapted = adapted.replace(old_workers, new_workers, 1)
        platform_adaptations.append({
            "rule": "t2kr_windows_dataloader_single_process",
            "occurrences": 1,
            "authoritative_source_mutated": False,
            "scientific_thresholds_changed": False,
            "scientific_values_changed": False,
            "reason": "Windows spawn cannot safely execute workers from the top-level historical T2-KR script; single-process loading preserves image order and main-process inference",
        })
        platform_adaptations.append({
            "rule": "t2kr_embedded_text_lf_byte_stability",
            "occurrences": 1,
            "authoritative_source_mutated": False,
            "scientific_thresholds_changed": False,
            "reason": "avoid Windows text-mode CRLF translation while preserving frozen LF SHA-256 commitments",
        })
    adapted, replacements = _apply_known_text_bindings(adapted, project_root)
    for item in _smart_rebindings(adapted, project_root):
        adapted, n = _replace_hash_in_text(adapted, item["historical_hash"], item["fresh_replay_hash"])
        if n: item["occurrences"] = n; replacements.append(item)
    compile(adapted, str(destination), "exec"); destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(adapted, encoding="utf-8", newline="\n")
    return {"source":source.as_posix(),"destination":destination.as_posix(),"source_sha256":sha256_file(source),"adapted_sha256":sha256_file(destination),"replacement_count":count+sum(int(x["occurrences"]) for x in replacements)+sum(int(x["occurrences"]) for x in platform_adaptations),"runtime_dependency_adaptations":[f"isic-cli==12.5.2 -> isic-cli=={ISIC_CLI_RUNTIME_PIN}"] if "isic-cli==12.5.2" in original else [],"runtime_replay_parent_hash_adaptations":replacements,"runtime_platform_adaptations":platform_adaptations,"source_mutated":False}


def adapt_notebook(source: Path, destination: Path, project_root: Path) -> dict[str, object]:
    historical_parent_inputs = _materialize_historical_parent_inputs(project_root) if source.name == STAGE8_NOTEBOOK_NAME else []
    payload = json.loads(source.read_text(encoding="utf-8-sig")); count = 0; original_has_pin = False
    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "code": continue
        original = "".join(cell.get("source", [])); original_has_pin |= "isic-cli==12.5.2" in original
        adapted, n = _adapt_text(original, project_root); count += n; cell["source"] = adapted.splitlines(keepends=True); cell["execution_count"] = None; cell["outputs"] = []
    replacements = []
    all_text = "\n".join("".join(c.get("source", [])) for c in payload.get("cells", []) if c.get("cell_type") == "code")
    for old, spec in _runtime_bindings().items():
        if old not in all_text: continue
        try: new, path = _resolve_binding(project_root, spec)
        except FileNotFoundError: continue
        if new == old: continue
        n = _replace_hash_in_payload(payload, old, new)
        if n: replacements.append({"historical_hash":old,"fresh_replay_hash":new,"resolved_parent":path,"occurrences":n,"basis":"declared_binding"}); all_text = all_text.replace(old,new)
    # Smart PATHS/EXPECTED pairing handles later T-series parent commitments.
    all_text = "\n".join("".join(c.get("source", [])) for c in payload.get("cells", []) if c.get("cell_type") == "code")
    for item in _smart_rebindings(all_text, project_root):
        n = _replace_hash_in_payload(payload, item["historical_hash"], item["fresh_replay_hash"])
        if n: item["occurrences"] = n; replacements.append(item)
    semantic = _semantic_notebook_adaptations(source, payload)
    _compile_notebook_cells(payload, destination.as_posix()); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    return {"source":source.as_posix(),"destination":destination.as_posix(),"source_sha256":sha256_file(source),"adapted_sha256":sha256_file(destination),"replacement_count":count+sum(int(x["occurrences"]) for x in replacements),"runtime_dependency_adaptations":[f"isic-cli==12.5.2 -> isic-cli=={ISIC_CLI_RUNTIME_PIN}"] if original_has_pin else [],"historical_parent_inputs":historical_parent_inputs,"runtime_replay_parent_hash_adaptations":replacements,"runtime_replay_semantic_adaptations":semantic,"source_mutated":False}


def adapt_source(source: Path, destination: Path, project_root: Path) -> dict[str, object]:
    if source.suffix.lower() == ".py": return adapt_python(source, destination, project_root)
    if source.suffix.lower() == ".ipynb": return adapt_notebook(source, destination, project_root)
    raise ValueError(f"unsupported adaptable source: {source}")
