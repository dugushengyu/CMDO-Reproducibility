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
    def test_runner_uses_utf8_child_process_io(self) -> None:
        text = (ROOT / "reproduction/runner.py").read_text(encoding="utf-8")
        self.assertIn('"PYTHONIOENCODING": "utf-8"', text)
        self.assertIn('encoding="utf-8"', text)
        self.assertIn('errors="strict"', text)
        self.assertIn('reconfigure(errors="backslashreplace")', text)

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

    def test_t2kr_embedded_text_materialisation_is_lf_byte_stable(self) -> None:
        import ast
        import hashlib
        source = ROOT / "legacy/extracted_authoritative/t_series/StageT2KR_CPU_pipeline_v0.4.py"
        original_bytes = source.read_bytes()
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        assigned = {}
        for stmt in tree.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id in {"EMBEDDED_PREREG_TEXT", "EMBEDDED_METHOD_TEXT", "EMBEDDED_LEXICON_TEXT", "EXPECTED"}:
                assigned[target.id] = ast.literal_eval(stmt.value)
        expected = assigned["EXPECTED"]
        for text_name, hash_key in [
            ("EMBEDDED_PREREG_TEXT", "prereg_sha256"),
            ("EMBEDDED_METHOD_TEXT", "method_sha256"),
            ("EMBEDDED_LEXICON_TEXT", "lexicon_sha256"),
        ]:
            observed = hashlib.sha256(assigned[text_name].encode("utf-8")).hexdigest()
            self.assertEqual(observed, expected[hash_key])
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            destination = temp / source.name
            record = adapt_python(source, destination, temp / "P")
            adapted = destination.read_text(encoding="utf-8")
            self.assertIn('path.write_bytes(text.encode("utf-8"))', adapted)
            self.assertNotIn('path.write_text(text, encoding="utf-8")', adapted)
            rules = {
                item["rule"]
                for item in record["runtime_platform_adaptations"]
            }
            self.assertIn(
                "t2kr_embedded_text_lf_byte_stability",
                rules,
            )
            self.assertIn(
                "t2kr_windows_dataloader_single_process",
                rules,
            )
            self.assertIn(
                'shuffle=False, num_workers=0 if os.name == "nt" else 2, pin_memory=False',
                adapted,
            )
            self.assertIn(
                'shuffle=False, num_workers=2, pin_memory=False',
                source.read_text(encoding="utf-8-sig"),
            )
        self.assertEqual(source.read_bytes(), original_bytes)

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

    def test_t2l_windows_and_targeted_parent_adapters(self) -> None:
        import ast

        source = ROOT / (
            "legacy/extracted_authoritative/t_series/"
            "StageT2L_pipeline_v0.1.py"
        )
        source_before = source.read_bytes()

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            project = temp / "P"

            parents = {
                "t2kr": (
                    project
                    / "06_Data_Records/Cross_Modal/"
                    "StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4/"
                    "06_Results/StageT2-KR_Complete_v0.4.json",
                    "final_record_sha256",
                    "T2KR",
                ),
                "t2h": (
                    project
                    / "06_Data_Records/Cross_Modal/"
                    "StageT2-H_Development_Only_Single_Pilot_Deployability_And_Sequential_Forecast_Freeze_v0.1/"
                    "04_Results/StageT2-H_Complete_v0.1.json",
                    "final_record_sha256",
                    "T2H",
                ),
                "t3pf": (
                    project
                    / "06_Data_Records/Cross_Modal/"
                    "StageT3-PF_Outcome-Free_Preregistration_And_Asset_Preflight_v1.0/"
                    "04_Results/StageT3-PF_Activation_Record_v1.0.json",
                    "activation_record_sha256",
                    "T3PF",
                ),
            }

            expected_runtime = {}

            for key, (path, field, stage) in parents.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                core = {"stage": stage, "test_value": 1}
                payload = dict(core)
                payload[field] = canonical_json_hash(core)
                path.write_text(
                    json.dumps(payload, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                expected_runtime[key] = payload[field]

            destination = temp / "adapted_t2l.py"
            record = adapt_python(source, destination, project)

            def assigned(path):
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
                wanted = {
                    "EXPECTED_PARENT",
                    "EXPECTED_DOCS",
                    "EMBEDDED_THEORY",
                    "EMBEDDED_PREREG",
                    "EMBEDDED_REGISTRY",
                    "EMBEDDED_MANUAL",
                }
                out = {}
                for stmt in tree.body:
                    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                        continue
                    target = stmt.targets[0]
                    if isinstance(target, ast.Name) and target.id in wanted:
                        out[target.id] = ast.literal_eval(stmt.value)
                return out

            original = assigned(source)
            adapted = assigned(destination)
            adapted_text = destination.read_text(encoding="utf-8")

            for key in [
                "EXPECTED_DOCS",
                "EMBEDDED_THEORY",
                "EMBEDDED_PREREG",
                "EMBEDDED_REGISTRY",
                "EMBEDDED_MANUAL",
            ]:
                self.assertEqual(adapted[key], original[key])

            self.assertEqual(
                adapted["EXPECTED_PARENT"],
                expected_runtime,
            )

            self.assertIn(
                'path.write_bytes(text.encode("utf-8"))',
                adapted_text,
            )
            self.assertIn(
                'shuffle=False, num_workers=0 if os.name == "nt" else 2, pin_memory=False',
                adapted_text,
            )

            platform_rules = {
                item["rule"]
                for item in record["runtime_platform_adaptations"]
            }
            self.assertIn(
                "t2l_embedded_companion_lf_byte_stability",
                platform_rules,
            )
            self.assertIn(
                "t2l_windows_dataloader_single_process",
                platform_rules,
            )

            targeted = [
                item
                for item in record["runtime_replay_parent_hash_adaptations"]
                if item.get("basis")
                == "targeted_t2l_runtime_parent_self_hashes"
            ]
            self.assertEqual(
                {item["parent_key"] for item in targeted},
                {"t2kr", "t2h", "t3pf"},
            )
            self.assertTrue(
                all(
                    item["frozen_embedded_documents_mutated"] is False
                    for item in targeted
                )
            )

        self.assertEqual(source.read_bytes(), source_before)


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

    def test_archival_t2j_upstream_manifest_bundle_is_declared(self) -> None:
        payload = json.loads((ROOT / "provenance/portable_bootstrap_manifest.json").read_text())
        rows = {row["file"]: row for row in payload["files"]}
        name = "CMDO-Archival-T2J-Upstream-Manifests-v0.1.zip"
        self.assertIn(name, rows)
        path = ROOT / "bootstrap_inputs" / "portable" / name
        if path.is_file():
            self.assertEqual(path.stat().st_size, int(rows[name]["size_bytes"]))
            import hashlib
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[name]["sha256"])
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("BOOTSTRAP_MANIFEST.json"))
                self.assertEqual(manifest["file_count"], 4)
                self.assertEqual({row["required_by_stage"] for row in manifest["files"]}, {"T2-J"})

    def test_archival_t2j_reference_fingerprint_cache_bundle_is_declared(self) -> None:
        payload = json.loads((ROOT / "provenance/portable_bootstrap_manifest.json").read_text())
        rows = {row["file"]: row for row in payload["files"]}
        name = "CMDO-Archival-T2J-Dermoscopy-Reference-Fingerprints-v0.1.zip"
        self.assertIn(name, rows)
        path = ROOT / "bootstrap_inputs" / "portable" / name
        if path.is_file():
            self.assertEqual(path.stat().st_size, int(rows[name]["size_bytes"]))
            import hashlib
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[name]["sha256"])
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("BOOTSTRAP_MANIFEST.json"))
                self.assertEqual(manifest["file_count"], 1)
                row = manifest["files"][0]
                self.assertEqual(row["required_by_stage"], "T2-J")
                self.assertEqual(row["relative_path"], "06_Data_Records/Cross_Modal/StageT2-J_Expansion_Harmonisation_Dedup_And_Public_Route_Repair_v0.1/03_Fingerprints_And_Dedup/StageT2-J_Existing_Dermoscopy_Reference_Fingerprints_v0.1.csv")
                self.assertEqual(row["sha256"], "d0383dfce4db6b147c5f68aaf4a07bd44f62352dd5179ae6cd205b59b762e2bd")

    def test_archival_t2kr_prerequisite_bundle_is_declared(self) -> None:
        payload = json.loads((ROOT / "provenance/portable_bootstrap_manifest.json").read_text())
        rows = {row["file"]: row for row in payload["files"]}
        name = "CMDO-Archival-T2KR-Frozen-Prerequisites-v0.1.zip"
        self.assertIn(name, rows)
        path = ROOT / "bootstrap_inputs" / "portable" / name
        if path.is_file():
            self.assertEqual(path.stat().st_size, int(rows[name]["size_bytes"]))
            import hashlib
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[name]["sha256"])
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("BOOTSTRAP_MANIFEST.json"))
                self.assertEqual(manifest["file_count"], 7)
                self.assertEqual({row["required_by_stage"] for row in manifest["files"]}, {"T2-KR"})

    def test_hisbreast_registry_matches_authoritative_t2kr_mount(self) -> None:
        payload = json.loads((ROOT / "provenance/datasets.json").read_text())
        row = next(row for row in payload["datasets"] if row["id"] == "HISBREAST_V2")
        self.assertEqual(row["acquisition"], "manual_official")
        self.assertEqual(row["persistent_id"], "10.17632/5c723rpwz2.2")
        self.assertEqual(
            row["expected_mount"],
            "00_Data_Acquisition/Cross_Modal_Independent_Target_Expansion_v0.1/"
            "HISBREAST_V2/00_Raw_Inbox/HiSBreast_Version 2.zip",
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
