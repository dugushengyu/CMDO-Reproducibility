"""Load, validate, and select the declared CMDO reproduction DAG."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .errors import IntegrityError

@dataclass(frozen=True)
class Stage:
    id: str; title: str; kind: str; profiles: tuple[str,...]; depends_on: tuple[str,...]
    source: str|None; governance: str; runtime: str; estimated: str; config: dict[str,Any]
    @classmethod
    def from_mapping(cls,row:dict[str,Any])->"Stage":
        known={"id","title","kind","profiles","depends_on","source","governance","runtime","estimated"}
        return cls(row["id"],row["title"],row["kind"],tuple(row.get("profiles",[])),tuple(row.get("depends_on",[])),row.get("source"),row.get("governance","transparent"),row.get("runtime","python"),row.get("estimated","not benchmarked"),{k:v for k,v in row.items() if k not in known})

class ReproductionDAG:
    def __init__(self,path:Path):
        payload=json.loads(path.read_text(encoding="utf-8")); self.schema_version=payload["schema_version"]; self.profiles=payload["profiles"]
        stages=[Stage.from_mapping(r) for r in payload["stages"]]; self.stages={s.id:s for s in stages}
        if len(stages)!=len(self.stages): raise IntegrityError("duplicate stage id in reproduction DAG")
        self._validate()
    def dependencies(self,stage:Stage,profile:str|None=None)->tuple[str,...]:
        overrides=stage.config.get("depends_on_by_profile",{})
        if profile and profile in overrides: return tuple(overrides[profile])
        return stage.depends_on
    def _validate(self)->None:
        for s in self.stages.values():
            dep_sets=[s.depends_on]+[tuple(v) for v in s.config.get("depends_on_by_profile",{}).values()]
            for deps in dep_sets:
                missing=[d for d in deps if d not in self.stages]
                if missing: raise IntegrityError(f"{s.id}: unknown dependencies: {missing}")
            unknown=[p for p in s.profiles if p not in self.profiles]
            if unknown: raise IntegrityError(f"{s.id}: unknown profiles: {unknown}")
            for p in s.config.get("depends_on_by_profile",{}):
                if p not in self.profiles: raise IntegrityError(f"{s.id}: unknown dependency override profile: {p}")
        self.topological_order(set(self.stages),None)
        for profile in self.profiles: self.select(profile)
    def select(self,profile:str)->list[Stage]:
        if profile not in self.profiles: raise IntegrityError(f"unknown profile: {profile}")
        selected={sid for sid,s in self.stages.items() if profile in s.profiles}; stack=list(selected)
        while stack:
            sid=stack.pop()
            for dep in self.dependencies(self.stages[sid],profile):
                if dep not in selected: selected.add(dep); stack.append(dep)
        return [self.stages[sid] for sid in self.topological_order(selected,profile)]
    def topological_order(self,selected:set[str],profile:str|None=None)->list[str]:
        indegree={sid:0 for sid in selected}; children={sid:[] for sid in selected}
        for sid in selected:
            for dep in self.dependencies(self.stages[sid],profile):
                if dep in selected: indegree[sid]+=1; children[dep].append(sid)
        ready=sorted(sid for sid,n in indegree.items() if n==0); ordered=[]
        while ready:
            sid=ready.pop(0); ordered.append(sid)
            for child in sorted(children[sid]):
                indegree[child]-=1
                if indegree[child]==0: ready.append(child); ready.sort()
        if len(ordered)!=len(selected): raise IntegrityError(f"cycle in reproduction DAG: {sorted(s for s,n in indegree.items() if n)}")
        return ordered
