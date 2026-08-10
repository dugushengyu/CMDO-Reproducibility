from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from reproduction.adapters import adapt_python
from reproduction.dag import ReproductionDAG
from reproduction.state import RunState
from scripts.compare_replay import compare_archive


ROOT = Path(__file__).resolve().parents[1]


class DAGTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dag = ReproductionDAG(ROOT / "provenance/reproduction_dag.json")

    def test_full_claim_has_training_and_no_u9(self) -> None:
        stages = self.dag.select("full-claim")
        ids = [stage.id for stage in stages]
        self.assertIn("u2_train_replay", ids)
        self.assertLess(ids.index("u2_train_replay"), ids.index("u8_nhanes_reconstruction"))
        self.assertFalse(any("u9" in stage_id.lower() for stage_id in ids))

    def test_every_declared_source_exists(self) -> None:
        missing = [
            stage.source
            for stage in self.dag.stages.values()
            if stage.source and not (ROOT / stage.source).is_file()
        ]
        self.assertEqual(missing, [])


class AdapterTests(unittest.TestCase):
    def test_adapter_does_not_mutate_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "source.py"
            source.write_text(
                "from pathlib import Path\n"
                "ROOT = Path('/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability')\n",
                encoding="utf-8",
            )
            before = source.read_bytes()
            destination = temp / "adapted.py"
            project = temp / "runtime" / "Cross-Modal_Diagnostic_Observability"
            record = adapt_python(source, destination, project)
            self.assertEqual(source.read_bytes(), before)
            self.assertIn(project.as_posix(), destination.read_text(encoding="utf-8"))
            self.assertFalse(record["source_mutated"])

    def test_adapter_uses_python311_compatible_isic_cli_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "source.py"
            source.write_text(
                "PIN = 'isic-cli==12.5.2'\n",
                encoding="utf-8",
            )
            before = source.read_bytes()
            destination = temp / "adapted.py"
            project = temp / "runtime" / "Cross-Modal_Diagnostic_Observability"
            record = adapt_python(source, destination, project)
            self.assertEqual(source.read_bytes(), before)
            self.assertIn("isic-cli==12.4.0", destination.read_text(encoding="utf-8"))
            self.assertEqual(
                record["runtime_dependency_adaptations"],
                ["isic-cli==12.5.2 -> isic-cli==12.4.0"],
            )


class StateTests(unittest.TestCase):
    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = RunState(path, profile="audit", run_id="x", root=ROOT)
            state.begin("one")
            state.complete("one", output="ok")
            loaded = RunState(path, profile="audit", run_id="x", root=ROOT)
            self.assertEqual(loaded.status("one"), "COMPLETE")


class ComparisonTests(unittest.TestCase):
    def _write_zip(self, path: Path, value: float) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("metrics.csv", f"target,value\na,{value}\n")
            archive.writestr(
                "complete.json",
                json.dumps({"decision": "PASS", "stage12_authorised": False}),
            )

    def test_archive_tolerance(self) -> None:
        rules = json.loads(
            (ROOT / "provenance/replay_acceptance_rules.json").read_text()
        )
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            frozen = temp / "frozen.zip"
            replay = temp / "replay.zip"
            self._write_zip(frozen, 0.5)
            self._write_zip(replay, 0.5000001)
            result = compare_archive(frozen, replay, rules)
            self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
