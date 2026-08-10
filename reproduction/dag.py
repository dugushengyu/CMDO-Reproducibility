"""Load, validate, and select the declared CMDO reproduction DAG."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import IntegrityError


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    kind: str
    profiles: tuple[str, ...]
    depends_on: tuple[str, ...]
    source: str | None
    governance: str
    runtime: str
    estimated: str
    config: dict[str, Any]

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "Stage":
        known = {
            "id",
            "title",
            "kind",
            "profiles",
            "depends_on",
            "source",
            "governance",
            "runtime",
            "estimated",
        }
        return cls(
            id=row["id"],
            title=row["title"],
            kind=row["kind"],
            profiles=tuple(row.get("profiles", [])),
            depends_on=tuple(row.get("depends_on", [])),
            source=row.get("source"),
            governance=row.get("governance", "transparent"),
            runtime=row.get("runtime", "python"),
            estimated=row.get("estimated", "not benchmarked"),
            config={key: value for key, value in row.items() if key not in known},
        )


class ReproductionDAG:
    def __init__(self, path: Path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.schema_version = payload["schema_version"]
        self.profiles = payload["profiles"]
        stages = [Stage.from_mapping(row) for row in payload["stages"]]
        self.stages = {stage.id: stage for stage in stages}
        if len(stages) != len(self.stages):
            raise IntegrityError("duplicate stage id in reproduction DAG")
        self._validate()

    def _validate(self) -> None:
        for stage in self.stages.values():
            missing = [dep for dep in stage.depends_on if dep not in self.stages]
            if missing:
                raise IntegrityError(f"{stage.id}: unknown dependencies: {missing}")
            unknown_profiles = [p for p in stage.profiles if p not in self.profiles]
            if unknown_profiles:
                raise IntegrityError(
                    f"{stage.id}: unknown profiles: {unknown_profiles}"
                )
        self.topological_order(set(self.stages))

    def select(self, profile: str) -> list[Stage]:
        if profile not in self.profiles:
            raise IntegrityError(f"unknown profile: {profile}")
        selected = {sid for sid, stage in self.stages.items() if profile in stage.profiles}
        stack = list(selected)
        while stack:
            sid = stack.pop()
            for dependency in self.stages[sid].depends_on:
                if dependency not in selected:
                    selected.add(dependency)
                    stack.append(dependency)
        return [self.stages[sid] for sid in self.topological_order(selected)]

    def topological_order(self, selected: set[str]) -> list[str]:
        indegree = {sid: 0 for sid in selected}
        children = {sid: [] for sid in selected}
        for sid in selected:
            for dependency in self.stages[sid].depends_on:
                if dependency in selected:
                    indegree[sid] += 1
                    children[dependency].append(sid)
        ready = sorted(sid for sid, degree in indegree.items() if degree == 0)
        ordered: list[str] = []
        while ready:
            sid = ready.pop(0)
            ordered.append(sid)
            for child in sorted(children[sid]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()
        if len(ordered) != len(selected):
            cyclic = sorted(sid for sid, degree in indegree.items() if degree)
            raise IntegrityError(f"cycle in reproduction DAG: {cyclic}")
        return ordered
