"""Atomic, resumable run ledger."""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class RunState:
    def __init__(self, path: Path, *, profile: str, run_id: str, root: Path):
        self.path = path
        if path.exists():
            self.payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.payload: dict[str, Any] = {
                "schema_version": 2,
                "run_id": run_id,
                "profile": profile,
                "created_utc": utc_now(),
                "updated_utc": utc_now(),
                "repository_root": str(root.resolve()),
                "environment": {
                    "python": sys.version,
                    "executable": sys.executable,
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "cpu_count": os.cpu_count(),
                },
                "governance": {
                    "classification": "RETROSPECTIVE_REPLAY",
                    "prospective_claim_created": False,
                    "u9_automatically_unsealed": False,
                },
                "stages": {},
            }
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.payload["updated_utc"] = utc_now()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def status(self, stage_id: str) -> str | None:
        row = self.payload["stages"].get(stage_id)
        return row.get("status") if row else None

    def begin(self, stage_id: str, *, command: list[str] | None = None) -> None:
        self.payload["stages"][stage_id] = {
            "status": "RUNNING",
            "started_utc": utc_now(),
            "command": command,
        }
        self.save()

    def complete(self, stage_id: str, **details: Any) -> None:
        row = self.payload["stages"].setdefault(stage_id, {})
        row.update({"status": "COMPLETE", "completed_utc": utc_now(), **details})
        self.save()

    def boundary(self, stage_id: str, *, code: str, message: str, evidence: dict[str, Any], details: list[str] | None = None) -> None:
        row = self.payload["stages"].setdefault(stage_id, {})
        row.update({
            "status": code,
            "stopped_utc": utc_now(),
            "message": message,
            "details": details or [],
            "evidence": evidence,
        })
        governance = self.payload.setdefault("governance", {})
        governance.update({
            "classification": "RETROSPECTIVE_REPLAY_WITH_SCIENTIFIC_BOUNDARY",
            "fresh_accepted_chain_complete": False,
            "scientific_boundary_stage": stage_id,
            "scientific_boundary_code": code,
            "prospective_claim_created": False,
            "u9_automatically_unsealed": False,
        })
        self.save()

    def fail(self, stage_id: str, *, status: str, message: str, **details: Any) -> None:
        row = self.payload["stages"].setdefault(stage_id, {})
        row.update(
            {
                "status": status,
                "stopped_utc": utc_now(),
                "message": message,
                **details,
            }
        )
        self.save()
