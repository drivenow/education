from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from models.workflow import AssetConfig, StepConfig, WorkflowConfig
from progress_store import ProgressStore
from workflow_runner import run_workflow


class ProgressStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config_dir = self.base / "config"
        self.config_dir.mkdir()
        self.config_path = self.config_dir / "sample.json"
        initial_config = {
            "id": "wf1",
            "title": "Test Workflow",
            "services": [],
            "steps": [],
            "assets": [
                {
                    "id": "asset_a",
                    "source_uri": "X:/path/to",
                    "file_name": "file.mp3",
                    "lang": "zh",
                    "is_valid": True,
                    "completed": False,
                    "play_count": 0,
                    "steps": {"play": {"repeats": 1}},
                },
                {
                    "id": "asset_b",
                    "source_uri": "X:/path/to",
                    "file_name": "file2.mp3",
                    "lang": "en",
                    "is_valid": True,
                    "completed": False,
                    "play_count": 0,
                    "steps": {"play": {"repeats": 1}},
                },
            ],
        }
        self.config_path.write_text(json.dumps(initial_config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_progress_json(self, store: ProgressStore) -> dict:
        path = store.path
        return json.loads(path.read_text(encoding="utf-8"))

    def test_mark_started_and_completed_persist(self) -> None:
        asset = AssetConfig(
            id="asset_a",
            source_uri="X:/path/to",
            file_name="file.mp3",
            lang="zh",
            steps={"play": {"repeats": 1}},
        )

        store = ProgressStore(self.config_path, workflow_id="wf1", assets=[asset])

        store.mark_started(asset)
        store.update_checkpoint(
            asset,
            progress_played=3,
            progress_total=3,
        )
        store.flush()
        data = self._load_progress_json(store)
        asset_entry = next(item for item in data["assets"] if item["id"] == asset.id)
        self.assertEqual(asset_entry["status"], "in_progress")
        self.assertFalse(asset_entry["completed"])
        self.assertEqual(asset_entry["file_name"], asset.file_name)
        self.assertEqual(asset_entry["progress_played"], 3)

        store.mark_completed(asset)
        store.flush()
        data = self._load_progress_json(store)
        entry = next(item for item in data["assets"] if item["id"] == asset.id)
        self.assertTrue(entry["completed"])
        self.assertEqual(entry["status"], "completed")
        self.assertEqual(entry["play_count"], 1)
        self.assertIn("update_time", entry)
        self.assertGreaterEqual(entry["progress_total"], entry["progress_played"])
        self.assertEqual(entry["progress_total"], 3)

        reloaded = ProgressStore.from_config_path(self.config_path, workflow_id="wf1")
        self.assertTrue(reloaded.is_completed(asset.id))

    def test_update_checkpoint_records_progress(self) -> None:
        asset = AssetConfig(
            id="asset_b",
            source_uri="X:/path/to",
            file_name="file2.mp3",
            lang="en",
            steps={"play": {"repeats": 1}},
        )

        store = ProgressStore(self.config_path, workflow_id="wf1", assets=[asset])

        store.mark_started(asset)
        store.update_checkpoint(
            asset,
            last_item="chunk1.wav",
            progress_played=1,
            progress_total=4,
        )
        store.flush()

        data = self._load_progress_json(store)
        entry = next(item for item in data["assets"] if item["id"] == asset.id)
        self.assertEqual(entry["last_item"], "chunk1.wav")
        self.assertEqual(entry["progress_played"], 1)
        self.assertEqual(entry["progress_total"], 4)
        self.assertEqual(entry["status"], "in_progress")

        store.update_checkpoint(
            asset,
            last_item="chunk4.wav",
            progress_played=4,
            progress_total=4,
        )
        store.mark_completed(asset)
        store.flush()
        data = self._load_progress_json(store)
        entry = next(item for item in data["assets"] if item["id"] == asset.id)
        self.assertEqual(entry["progress_played"], 4)
        self.assertEqual(entry["progress_total"], 4)
        self.assertTrue(entry["completed"])
        self.assertEqual(entry["play_count"], 1)

    def test_mark_completed_without_full_playback(self) -> None:
        asset = AssetConfig(
            id="asset_c",
            source_uri="X:/path/to",
            file_name="file3.mp3",
            lang="en",
            steps={"play": {"repeats": 1}},
        )

        store = ProgressStore(self.config_path, workflow_id="wf1", assets=[asset])
        store.mark_started(asset)
        store.update_checkpoint(
            asset,
            last_item="chunk1.wav",
            progress_played=1,
            progress_total=4,
        )
        store.mark_completed(asset)
        store.flush()

        data = self._load_progress_json(store)
        entry = next(item for item in data["assets"] if item["id"] == asset.id)
        self.assertEqual(entry["progress_played"], 1)
        self.assertEqual(entry["progress_total"], 4)
        self.assertEqual(entry["play_count"], 0)
        self.assertFalse(entry["completed"])
        self.assertEqual(entry["status"], "in_progress")

    def test_run_workflow_skips_completed_assets(self) -> None:
        services: list = []
        steps: list[StepConfig] = []
        assets = [
            AssetConfig(id="asset_done", source_uri="X:/done", file_name="done.mp3", lang="zh"),
            AssetConfig(id="asset_new", source_uri="X:/new", file_name="new.mp3", lang="en"),
        ]
        cfg = WorkflowConfig(
            id="wf_skip",
            title="Skip Test",
            services=services,
            steps=steps,
            assets=assets,
        )

        store = ProgressStore(self.config_path, workflow_id=cfg.id)
        store.attach_assets(cfg.assets)
        store.update_checkpoint(
            cfg.assets[0],
            progress_played=1,
            progress_total=1,
        )
        store.mark_completed(cfg.assets[0])
        store.flush()

        with mock.patch("workflow_runner.Orchestrator") as MockOrchestrator:
            mock_orchestrator = MockOrchestrator.return_value
            mock_orchestrator.run_asset.return_value = {"artifacts": {}}
            run_workflow(cfg, progress_path=self.config_path)

        # Only the second asset should be processed.
        self.assertEqual(MockOrchestrator.return_value.run_asset.call_count, 1)
        args, _ = MockOrchestrator.return_value.run_asset.call_args
        processed_asset = args[0]
        self.assertEqual(processed_asset.id, "asset_new")

        refreshed = ProgressStore.from_config_path(self.config_path, workflow_id=cfg.id)
        # Previously completed record should still be marked done.
        self.assertTrue(refreshed.is_completed("asset_done"))
        self.assertFalse(refreshed.is_completed("asset_new"))


if __name__ == "__main__":
    unittest.main()
