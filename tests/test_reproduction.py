from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from reproduction.adapters import adapt_notebook, adapt_python, canonical_json_hash
from reproduction.bootstrap import materialize_bootstrap_zip
from reproduction.errors import BlockedError
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

    def test_full_claim_orders_t3pf_before_t2g_and_after_t2f(self) -> None:
        ids = [stage.id for stage in self.dag.select("full-claim")]
        self.assertLess(ids.index("t2f_covariate_balance"), ids.index("t3pf_preflight"))
        self.assertLess(ids.index("t3pf_preflight"), ids.index("t2g_hierarchy"))
        self.assertEqual(len(ids), 55)

    def test_archival_continuation_is_separate_from_fresh_t2d_t2e(self) -> None:
        ids = [stage.id for stage in self.dag.select("archival-continuation")]
        self.assertNotIn("t2d_witness", ids)
        self.assertNotIn("t2e_baselines", ids)
        self.assertIn("archival_preflight", ids)
        self.assertNotIn("t2f_covariate_balance", ids)
        self.assertIn("t3pf_preflight", ids)
        self.assertIn("u8_nhanes_reconstruction", ids)
        self.assertLess(ids.index("archival_preflight"), ids.index("t3pf_preflight"))
        self.assertLess(ids.index("t3pf_preflight"), ids.index("t2g_hierarchy"))
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

    def test_later_tseries_file_and_record_hashes_rebind_from_runtime_parent(self) -> None:
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            project = temp / "P"
            t2h = project / (
                "06_Data_Records/Cross_Modal/"
                "StageT2-H_Development_Only_Single_Pilot_Deployability_And_Sequential_Forecast_Freeze_v0.1/"
                "04_Results/StageT2-H_Complete_v0.1.json"
            )
            t3pf = project / (
                "06_Data_Records/Cross_Modal/"
                "StageT3-PF_Outcome-Free_Preregistration_And_Asset_Preflight_v1.0/"
                "04_Results/StageT3-PF_Activation_Record_v1.0.json"
            )
            for path, field, stage in [
                (t2h, "final_record_sha256", "T2H"),
                (t3pf, "activation_record_sha256", "T3PF"),
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                core = {"stage": stage, "test_value": 1}
                payload = dict(core)
                payload[field] = canonical_json_hash(core)
                path.write_text(json.dumps(payload, indent=2) + "\n")
            source = ROOT / (
                "legacy/original_authoritative/t_series/"
                "CrossModal_StageT2-I_Independent_Target_Expansion_Registry_Acquisition_And_Harmonisation_v0.2.ipynb"
            )
            destination = temp / "adapted.ipynb"
            record = adapt_notebook(source, destination, project)
            text = destination.read_text(encoding="utf-8")
            for path, field in [(t2h, "final_record_sha256"), (t3pf, "activation_record_sha256")]:
                payload = json.loads(path.read_text())
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), text)
                self.assertIn(payload[field], text)
            bases = [row["basis"] for row in record["runtime_replay_parent_hash_adaptations"]]
            self.assertTrue(any("normalized file_sha256 t2h_file" in value for value in bases))

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
    def test_scientific_boundary_is_persistent_governance_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = RunState(path, profile="full-claim", run_id="x", root=ROOT)
            state.begin("t2d_witness")
            state.boundary(
                "t2d_witness",
                code="SCIENTIFIC_DIVERGENCE_BOUNDARY",
                message="non-reproduction",
                evidence={"gates_passed": 10, "gates_total": 11},
            )
            loaded = RunState(path, profile="full-claim", run_id="x", root=ROOT)
            self.assertEqual(loaded.status("t2d_witness"), "SCIENTIFIC_DIVERGENCE_BOUNDARY")
            self.assertFalse(loaded.payload["governance"]["fresh_accepted_chain_complete"])
            self.assertEqual(loaded.payload["governance"]["scientific_boundary_stage"], "t2d_witness")

    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = RunState(path, profile="audit", run_id="x", root=ROOT)
            state.begin("one")
            state.complete("one", output="ok")
            loaded = RunState(path, profile="audit", run_id="x", root=ROOT)
            self.assertEqual(loaded.status("one"), "COMPLETE")


class BootstrapTests(unittest.TestCase):
    def test_materialize_bootstrap_is_byte_verified_and_conflict_safe(self) -> None:
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            bundle = temp / "mini.zip"
            data = b"immutable-parent\n"
            digest = hashlib.sha256(data).hexdigest()
            manifest = {
                "classification": "TEST_BOOTSTRAP",
                "file_count": 1,
                "files": [{
                    "relative_path": "03_Theory/test.txt",
                    "size_bytes": len(data),
                    "sha256": digest,
                }],
            }
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("BOOTSTRAP_MANIFEST.json", json.dumps(manifest))
                archive.writestr("03_Theory/test.txt", data)
            project = temp / "project"
            first = materialize_bootstrap_zip(bundle, project)
            self.assertEqual(first["files"][0]["status"], "materialized")
            second = materialize_bootstrap_zip(bundle, project)
            self.assertEqual(second["files"][0]["status"], "reused")
            (project / "03_Theory/test.txt").write_bytes(b"changed")
            with self.assertRaises(BlockedError):
                materialize_bootstrap_zip(bundle, project)

    def test_stage7_historical_parent_manifest_is_complete(self) -> None:
        payload = json.loads((ROOT / "provenance/historical_parent_inputs.json").read_text())
        self.assertEqual(
            {row["id"] for row in payload["inputs"]},
            {"STAGE7_FINAL_RECORD", "STAGE7_EDGE_MATRIX", "STAGE7_DDO2_DISCOVERY_CANDIDATES"},
        )

    def test_archival_t2f_parent_bundle_is_declared(self) -> None:
        payload = json.loads((ROOT / "provenance/portable_bootstrap_manifest.json").read_text())
        rows = {row["file"]: row for row in payload["files"]}
        name = "CMDO-Archival-T2F-Accepted-Parent-v0.1.zip"
        self.assertIn(name, rows)
        path = ROOT / "bootstrap_inputs" / "portable" / name
        if path.is_file():
            self.assertEqual(path.stat().st_size, int(rows[name]["size_bytes"]))
            import hashlib
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[name]["sha256"])

    def test_archival_t2g_t2j_companion_bundle_is_declared(self) -> None:
        payload = json.loads((ROOT / "provenance/portable_bootstrap_manifest.json").read_text())
        rows = {row["file"]: row for row in payload["files"]}
        name = "CMDO-Archival-T2G-T2J-Immutable-Companions-v0.1.zip"
        self.assertIn(name, rows)
        path = ROOT / "bootstrap_inputs" / "portable" / name
        if path.is_file():
            self.assertEqual(path.stat().st_size, int(rows[name]["size_bytes"]))
            import hashlib
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[name]["sha256"])
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("BOOTSTRAP_MANIFEST.json"))
                self.assertEqual(manifest["file_count"], 13)
                self.assertEqual(
                    {row["required_by_stage"] for row in manifest["files"]},
                    {"T2-G", "T2-H", "T2-I", "T2-J"},
                )

    def test_historical_receipt_manifest_declares_six_unique_files(self) -> None:
        payload = json.loads((ROOT / "provenance/historical_receipts.json").read_text())
        rows = payload["files"]
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({row["id"] for row in rows}), 6)
        self.assertEqual(len({row["relative_path"] for row in rows}), 6)
        self.assertTrue(all(len(row["sha256"]) == 64 for row in rows))


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
