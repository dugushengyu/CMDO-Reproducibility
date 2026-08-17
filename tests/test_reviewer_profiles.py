from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reproduction.runner import RunOptions, Runner


ROOT = Path(__file__).resolve().parents[1]


class ReviewerProfileIsolationTests(unittest.TestCase):
    def test_smoke_adapter_audit_skips_historical_code_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = Runner(
                ROOT,
                RunOptions(
                    profile="smoke",
                    run_id="smoke-isolation",
                    output_root=Path(directory),
                ),
            )

            def forbidden_mirror() -> dict[str, object]:
                raise AssertionError("smoke profile must not materialize historical code mirror")

            runner._prepare_authoritative_code_mirror = forbidden_mirror  # type: ignore[method-assign]
            result = runner._adapt_selected_sources()

            self.assertEqual(result["adapted_count"], 0)
            self.assertEqual(result["authoritative_mirror_count"], 0)
            mirror_manifest = Path(str(result["authoritative_mirror_manifest"]))
            self.assertTrue(mirror_manifest.is_file())
            self.assertEqual(json.loads(mirror_manifest.read_text(encoding="utf-8")), [])

    def test_frozen_adapter_audit_skips_historical_code_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = Runner(
                ROOT,
                RunOptions(
                    profile="frozen",
                    run_id="frozen-isolation",
                    output_root=Path(directory),
                ),
            )

            def forbidden_mirror() -> dict[str, object]:
                raise AssertionError("frozen profile must not materialize historical code mirror")

            runner._prepare_authoritative_code_mirror = forbidden_mirror  # type: ignore[method-assign]
            result = runner._adapt_selected_sources()

            self.assertEqual(result["adapted_count"], 0)
            self.assertEqual(result["authoritative_mirror_count"], 0)


if __name__ == "__main__":
    unittest.main()
