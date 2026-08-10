"""Command-line interface for the CMDO reproduction runner."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from .runner import RunOptions, Runner


ROOT = Path(__file__).resolve().parents[1]


def default_run_id(profile: str) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{profile}-{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CMDO reviewer reproduction: audit, smoke, frozen or full replay"
    )
    parser.add_argument(
        "profile",
        choices=["audit", "smoke", "frozen", "full-claim", "historical-replay"],
    )
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/reproduction")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--acknowledge-retrospective-replay", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--from-stage")
    parser.add_argument("--to-stage")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = RunOptions(
        profile=args.profile,
        run_id=args.run_id or default_run_id(args.profile),
        output_root=args.output_root,
        project_root=args.project_root,
        config_path=args.config,
        allow_network=args.allow_network,
        acknowledge_retrospective_replay=args.acknowledge_retrospective_replay,
        resume=args.resume,
        plan_only=args.plan,
        from_stage=args.from_stage,
        to_stage=args.to_stage,
        extra_env={
            key: value
            for key, value in os.environ.items()
            if key.startswith("CMDO_REPLAY_")
        },
    )
    return Runner(ROOT, options).run()
