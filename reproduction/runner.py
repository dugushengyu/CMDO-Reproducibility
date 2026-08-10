"""Execution engine for audit, smoke, frozen, and full replay profiles."""

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback is documented
    tomllib = None  # type: ignore[assignment]

from .adapters import adapt_source
from .dag import ReproductionDAG, Stage
from .errors import BlockedError, IntegrityError
from .hashing import file_record, sha256_file
from .state import RunState


@dataclass
class RunOptions:
    profile: str
    run_id: str
    output_root: Path
    project_root: Path | None = None
    config_path: Path | None = None
    allow_network: bool = False
    acknowledge_retrospective_replay: bool = False
    resume: bool = False
    plan_only: bool = False
    from_stage: str | None = None
    to_stage: str | None = None
    extra_env: dict[str, str] = field(default_factory=dict)


class Runner:
    def __init__(self, repository_root: Path, options: RunOptions):
        self.root = repository_root.resolve()
        self.options = options
        self.dag = ReproductionDAG(self.root / "provenance/reproduction_dag.json")
        self.profile_stages = self.dag.select(options.profile)
        self.stages = self._slice(self.profile_stages)
        self.run_dir = (options.output_root / options.run_id).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state = RunState(
            self.run_dir / "run_state.json",
            profile=options.profile,
            run_id=options.run_id,
            root=self.root,
        )
        self.config = self._load_config(options.config_path)
        configured_project = self.config.get("run", {}).get("project_root")
        self.project_root = (
            options.project_root
            or (Path(configured_project).expanduser() if configured_project else None)
            or self.run_dir / "runtime" / "Cross-Modal_Diagnostic_Observability"
        ).resolve()
        self.adapted_sources: dict[str, Path] = {}

    def _slice(self, stages: list[Stage]) -> list[Stage]:
        ids = [stage.id for stage in stages]
        start = ids.index(self.options.from_stage) if self.options.from_stage else 0
        end = ids.index(self.options.to_stage) + 1 if self.options.to_stage else len(ids)
        if start >= end:
            raise IntegrityError("--from-stage occurs after --to-stage")
        return stages[start:end]

    @staticmethod
    def _load_config(path: Path | None) -> dict[str, Any]:
        if not path:
            return {}
        if not path.is_file():
            raise IntegrityError(f"configuration file does not exist: {path}")
        if tomllib is None:
            raise IntegrityError("TOML configuration requires Python 3.11+")
        with path.open("rb") as stream:
            return tomllib.load(stream)

    def print_plan(self) -> None:
        profile = self.dag.profiles[self.options.profile]
        print(f"Profile: {self.options.profile} — {profile['description']}")
        print(f"Run directory: {self.run_dir}")
        print(f"Scientific project root: {self.project_root}")
        for index, stage in enumerate(self.stages, 1):
            dependencies = ",".join(stage.depends_on) or "-"
            print(
                f"{index:02d}. {stage.id:28s} [{stage.kind:15s}] "
                f"deps={dependencies} | {stage.estimated} | {stage.governance}"
            )
            print(f"    {stage.title}")

    def run(self) -> int:
        self.print_plan()
        if self.options.plan_only:
            return 0
        for stage in self.stages:
            if self.options.resume and self.state.status(stage.id) == "COMPLETE":
                print(f"[RESUME] {stage.id}: already complete")
                continue
            print(f"\n[START] {stage.id}: {stage.title}")
            self.state.begin(stage.id)
            started = time.monotonic()
            try:
                details = self._execute(stage)
            except BlockedError as exc:
                self.state.fail(
                    stage.id,
                    status=exc.code,
                    message=str(exc),
                    details=exc.details,
                )
                print(f"[{exc.code}] {exc}")
                for detail in exc.details:
                    print(f"- {detail}")
                return 3
            except Exception as exc:
                self.state.fail(
                    stage.id,
                    status="FAILED",
                    message=f"{type(exc).__name__}: {exc}",
                )
                print(f"[FAILED] {stage.id}: {type(exc).__name__}: {exc}")
                return 1
            elapsed = time.monotonic() - started
            self.state.complete(stage.id, elapsed_seconds=elapsed, **details)
            print(f"[PASS] {stage.id} ({elapsed:.1f}s)")
        print(f"\nCMDO profile {self.options.profile} COMPLETE")
        print(f"Run ledger: {self.state.path}")
        return 0

    def _execute(self, stage: Stage) -> dict[str, Any]:
        if stage.kind == "internal":
            return self._execute_internal(stage)
        if stage.governance in {"sealed_replay", "post_unseal_replay"}:
            if not self.options.acknowledge_retrospective_replay:
                raise BlockedError(
                    "BLOCKED_GOVERNANCE_ACK",
                    "sealed stages require --acknowledge-retrospective-replay",
                    details=[
                        "This run is a disclosed retrospective replay, not a new prospective validation.",
                        "U9 is excluded and will not be unsealed by this runner.",
                    ],
                )
        if stage.kind in {"python", "notebook"}:
            return self._execute_legacy(stage)
        if stage.kind == "matlab_package":
            return self._execute_matlab_package(stage)
        raise IntegrityError(f"unsupported stage kind: {stage.kind}")

    def _execute_internal(self, stage: Stage) -> dict[str, Any]:
        action = stage.config.get("action")
        if action == "repository_integrity":
            return self._run_command(
                stage, [sys.executable, "scripts/verify_repository.py"], cwd=self.root
            )
        if action == "extracted_source_integrity":
            return self._run_command(
                stage,
                [sys.executable, "scripts/extract_embedded_sources.py", "--check"],
                cwd=self.root,
            )
        if action == "provenance_integrity":
            return self._run_command(
                stage,
                [sys.executable, "scripts/build_provenance_manifests.py", "--check"],
                cwd=self.root,
            )
        if action == "adapted_source_static_check":
            return self._adapt_selected_sources()
        if action == "smoke_loop":
            command = [
                sys.executable,
                "-m",
                "reproduction.smoke",
                "--output-dir",
                str(self.run_dir / "smoke"),
            ]
            if self.options.allow_network:
                command.append("--allow-network")
            return self._run_command(stage, command, cwd=self.root)
        if action == "canonical_integrity":
            return self._run_command(
                stage,
                [sys.executable, "scripts/verify_repository.py", "--require-canonical"],
                cwd=self.root,
            )
        if action == "full_preflight":
            return self._full_preflight()
        if action == "collect_replay_records":
            return self._collect_replay_records()
        if action == "frozen_figures":
            return self._run_matlab_figures(stage, canonical_dir=self.root / "data/canonical_records")
        if action == "replay_figures":
            return self._run_matlab_figures(stage, canonical_dir=self.run_dir / "replay_canonical_records")
        if action == "compare_replay":
            command = [
                sys.executable,
                "scripts/compare_replay.py",
                "--run-dir",
                str(self.run_dir),
                "--canonical-dir",
                str(self.run_dir / "replay_canonical_records"),
            ]
            return self._run_command(stage, command, cwd=self.root)
        raise IntegrityError(f"unsupported internal action: {action}")

    def _base_environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "CMDO_PROJECT_ROOT": str(self.project_root),
                "CDO_PROJECT_ROOT": str(self.project_root),
                "CMDO_REPRODUCTION_MODE": "RETROSPECTIVE_REPLAY",
                "CMDO_ALLOW_PROSPECTIVE_CLAIM": "0",
                "PYTHONHASHSEED": "0",
                "MPLBACKEND": "Agg",
            }
        )
        environment.update(self.options.extra_env)
        return environment

    def _run_command(
        self,
        stage: Stage,
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        log_path = self.run_dir / "logs" / f"{stage.id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        environment = self._base_environment()
        if env:
            environment.update(env)
        print("Command:", " ".join(command))
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                log.write(line)
            return_code = process.wait()
        if return_code:
            raise RuntimeError(f"command exited with status {return_code}; see {log_path}")
        return {
            "command": command,
            "log": str(log_path),
            "log_sha256": sha256_file(log_path),
        }

    def _adapt_selected_sources(self) -> dict[str, Any]:
        destination_root = self.run_dir / "adapted_source"
        records = []
        mirror = self._prepare_authoritative_code_mirror()
        for stage in self.profile_stages:
            if not stage.source:
                continue
            source = (self.root / stage.source).resolve()
            if not source.is_file():
                raise IntegrityError(f"declared source is missing: {stage.source}")
            destination = destination_root / stage.source
            record = adapt_source(source, destination, self.project_root)
            record["source"] = stage.source
            record["destination"] = str(destination.relative_to(self.run_dir))
            records.append(record)
            self.adapted_sources[stage.id] = destination
        manifest_path = self.run_dir / "adapted_source_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "classification": "NON_DESTRUCTIVE_RUNTIME_ADAPTERS",
                    "authoritative_sources_mutated": False,
                    "project_root": str(self.project_root),
                    "files": records,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "adapted_count": len(records),
            "authoritative_mirror_count": mirror["file_count"],
            "authoritative_mirror_manifest": mirror["manifest"],
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
        }

    def _prepare_authoritative_code_mirror(self) -> dict[str, Any]:
        """Populate the Drive-era code location with unchanged authoritative bytes.

        Adapted copies execute elsewhere. Scripts that hash NOTEBOOK_PATH therefore see
        the original container, preserving the historical source commitment.
        """

        code_root = self.project_root / "05_Code" / "Cross_Modal"
        code_root.mkdir(parents=True, exist_ok=True)
        source_roots = [
            self.root / "legacy/original_authoritative",
            self.root / "legacy/extracted_authoritative",
        ]
        records: list[dict[str, object]] = []
        by_name: dict[str, str] = {}
        for source_root in source_roots:
            for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
                digest = sha256_file(source)
                if source.name in by_name and by_name[source.name] != digest:
                    # Preserve both without making a potentially wrong file authoritative.
                    destination = code_root / "_name_collisions" / source.relative_to(source_root)
                else:
                    destination = code_root / source.name
                    by_name[source.name] = digest
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists() and sha256_file(destination) != digest:
                    raise IntegrityError(f"runtime code-mirror conflict: {destination}")
                if not destination.exists():
                    shutil.copy2(source, destination)
                records.append(
                    {
                        "source": source.relative_to(self.root).as_posix(),
                        "runtime_path": destination.relative_to(self.project_root).as_posix(),
                        "sha256": digest,
                        "bytes_unchanged": True,
                    }
                )
        manifest = self.run_dir / "authoritative_code_mirror_manifest.json"
        manifest.write_text(
            json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return {"file_count": len(records), "manifest": str(manifest)}

    def _adapted_source(self, stage: Stage) -> Path:
        if stage.id in self.adapted_sources:
            return self.adapted_sources[stage.id]
        assert stage.source
        source = self.root / stage.source
        destination = self.run_dir / "adapted_source" / stage.source
        adapt_source(source, destination, self.project_root)
        self.adapted_sources[stage.id] = destination
        return destination

    def _execute_legacy(self, stage: Stage) -> dict[str, Any]:
        self.project_root.mkdir(parents=True, exist_ok=True)
        if not (self.run_dir / "authoritative_code_mirror_manifest.json").exists():
            self._prepare_authoritative_code_mirror()
        source = self._adapted_source(stage)
        environment = {key: str(value) for key, value in stage.config.get("env", {}).items()}
        if stage.kind == "python":
            entrypoint = stage.config.get("entrypoint")
            if entrypoint:
                snippet = (
                    "import runpy; ns=runpy.run_path(r'"
                    + str(source)
                    + "'); ns['"
                    + entrypoint
                    + "']()"
                )
                command = [sys.executable, "-c", snippet]
            else:
                command = [sys.executable, str(source)]
            return self._run_command(stage, command, cwd=self.project_root, env=environment)

        try:
            import nbformat  # noqa: F401
            import nbclient  # noqa: F401
        except ImportError as exc:
            raise BlockedError(
                "BLOCKED_RUNTIME",
                "notebook execution requires nbformat and nbclient",
                details=["Install environment/requirements-replay.txt"],
            ) from exc
        executed_dir = self.run_dir / "executed_notebooks"
        executed_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            str(source),
            "--output",
            source.name,
            "--output-dir",
            str(executed_dir),
            "--ExecutePreprocessor.timeout=-1",
        ]
        return self._run_command(stage, command, cwd=self.project_root, env=environment)

    def _full_preflight(self) -> dict[str, Any]:
        if not self.options.acknowledge_retrospective_replay:
            raise BlockedError(
                "BLOCKED_GOVERNANCE_ACK",
                "full-claim requires --acknowledge-retrospective-replay",
            )
        manifest = json.loads(
            (self.root / "provenance/datasets.json").read_text(encoding="utf-8")
        )
        configured = self.config.get("datasets", {})
        required_modules = [
            "numpy",
            "pandas",
            "scipy",
            "sklearn",
            "matplotlib",
            "torch",
            "torchvision",
            "nbformat",
            "nbclient",
        ]
        missing_modules = [
            module for module in required_modules if importlib.util.find_spec(module) is None
        ]
        missing_runtimes = []
        if missing_modules:
            missing_runtimes.append("Python modules: " + ", ".join(missing_modules))
        if not shutil.which("matlab"):
            missing_runtimes.append(
                "MATLAB with Statistics and Machine Learning Toolbox is not on PATH"
            )
        if missing_runtimes:
            raise BlockedError(
                "BLOCKED_RUNTIME",
                "full replay runtimes are incomplete; no scientific stage was run",
                details=missing_runtimes,
            )
        missing_manual: list[str] = []
        missing_network: list[str] = []
        mounted: list[dict[str, str]] = []
        self.project_root.mkdir(parents=True, exist_ok=True)
        for row in manifest["datasets"]:
            if self.options.profile not in row.get("required_for", []):
                continue
            dataset_id = row["id"]
            mode = row["acquisition"]
            configured_path = configured.get(dataset_id) or os.environ.get(
                "CMDO_DATA_" + dataset_id.replace("-", "_").upper()
            )
            expected = row.get("expected_mount")
            expected_path = self.project_root / expected if expected else None
            if configured_path:
                source = Path(configured_path).expanduser().resolve()
                if not source.exists():
                    missing_manual.append(f"{dataset_id}: configured path absent: {source}")
                    continue
                if expected_path and not expected_path.exists():
                    expected_path.parent.mkdir(parents=True, exist_ok=True)
                    expected_path.symlink_to(source, target_is_directory=source.is_dir())
                mounted.append({"dataset": dataset_id, "source": str(source), "mount": str(expected_path or source)})
                continue
            if expected_path and expected_path.exists():
                continue
            if mode in {"manual_acceptance", "manual_official", "account_gated"}:
                missing_manual.append(
                    f"{dataset_id}: {mode}; expected {expected or 'configured path'}"
                )
            elif mode == "automatic" and not self.options.allow_network:
                missing_network.append(f"{dataset_id}: automatic official download")
            elif mode == "credentialed_excluded":
                continue
        if missing_manual:
            raise BlockedError(
                "BLOCKED_LICENSE_GATE",
                "manual/account-gated datasets are not available; no stage was run",
                details=missing_manual,
            )
        if missing_network:
            raise BlockedError(
                "BLOCKED_NETWORK_ACK",
                "automatic public downloads require --allow-network",
                details=missing_network,
            )
        return {
            "project_root": str(self.project_root),
            "configured_mounts": mounted,
            "network_allowed": self.options.allow_network,
            "prospective_claim_created": False,
            "u9_excluded": True,
        }

    def _collect_replay_records(self) -> dict[str, Any]:
        names = []
        with (self.root / "provenance/canonical_archives_manifest.csv").open(
            encoding="utf-8-sig"
        ) as stream:
            import csv

            names = [row["archive"] for row in csv.DictReader(stream)]
        destination = self.run_dir / "replay_canonical_records"
        destination.mkdir(parents=True, exist_ok=True)
        records = []
        for name in names:
            candidates = list(self.project_root.rglob(name))
            if len(candidates) != 1:
                raise IntegrityError(
                    f"expected one replay archive {name}, found {len(candidates)}"
                )
            target = destination / name
            shutil.copy2(candidates[0], target)
            records.append(file_record(target, root=destination))
        manifest = destination / "replay_records_manifest.json"
        manifest.write_text(
            json.dumps(records, indent=2, sort_keys=True), encoding="utf-8"
        )
        return {"archives": records, "manifest": str(manifest)}

    def _matlab_executable(self) -> str:
        executable = shutil.which("matlab")
        if not executable:
            raise BlockedError(
                "BLOCKED_RUNTIME",
                "MATLAB is required for U8 and the publication figures",
                details=["Required toolbox: Statistics and Machine Learning Toolbox"],
            )
        return executable

    @staticmethod
    def _matlab_quote(path: Path) -> str:
        return str(path.resolve()).replace("'", "''")

    def _run_matlab_figures(self, stage: Stage, *, canonical_dir: Path) -> dict[str, Any]:
        output = self.run_dir / "publication_figures"
        environment = {
            "CMDO_CANONICAL_RECORD_DIR": str(canonical_dir.resolve()),
            "CMDO_OUTPUT_ROOT": str(output.resolve()),
            "CMDO_BATCH_MODE": "1",
        }
        expression = (
            f"cd('{self._matlab_quote(self.root)}'); "
            "SETUP_CMDO; RUN_ALL_FIGURES('Batch',true,'Strict',true);"
        )
        return self._run_command(
            stage,
            [self._matlab_executable(), "-batch", expression],
            cwd=self.root,
            env=environment,
        )

    def _execute_matlab_package(self, stage: Stage) -> dict[str, Any]:
        source_directory = self.root / stage.config["package"]
        package_copy = self.run_dir / "matlab_packages" / stage.id
        if package_copy.exists() and not self.options.resume:
            raise IntegrityError(f"MATLAB work directory already exists: {package_copy}")
        if not package_copy.exists():
            shutil.copytree(source_directory, package_copy)
        script = stage.config["script"]
        expression = f"cd('{self._matlab_quote(package_copy)}'); run('{script}');"
        return self._run_command(
            stage,
            [self._matlab_executable(), "-batch", expression],
            cwd=package_copy,
        )
