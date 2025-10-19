from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_config.py"


class GenerateConfigTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.base = Path(self.tmpdir.name)
        (self.base / "audio").mkdir()

    def _run_script(self, directory: Path, lang: str, output: Path, extra_args: list[str] | None = None) -> None:
        cmd = [sys.executable, str(SCRIPT_PATH), "--directory", str(directory), "--lang", lang, "--output", str(output)]
        if extra_args:
            cmd.extend(extra_args)
        subprocess.check_call(cmd, cwd=SCRIPT_PATH.parent)

    def test_generate_config_for_english(self) -> None:
        audio_dir = self.base / "audio_en"
        audio_dir.mkdir()
        (audio_dir / "lesson1.mp3").write_bytes(b"")
        (audio_dir / "lesson2.m4a").write_bytes(b"")
        output_path = self.base / "en_config.json"

        self._run_script(audio_dir, "en", output_path, extra_args=["--config-id", "en_plan", "--title", "English Lessons"])

        data = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "en_plan")
        self.assertEqual(len(data["assets"]), 2)
        for asset in data["assets"]:
            self.assertEqual(asset["lang"], "en")
            self.assertTrue(asset["steps"]["split"].get("enabled", False))
            self.assertTrue(asset["steps"]["play"].get("translate"))
            self.assertEqual(asset["progress_played"], 0)
            self.assertEqual(asset["progress_total"], 0)

    def test_generate_config_for_chinese(self) -> None:
        audio_dir = self.base / "audio_zh"
        audio_dir.mkdir()
        (audio_dir / "01.mp3").write_bytes(b"")
        output_path = self.base / "zh_config.json"

        self._run_script(audio_dir, "zh", output_path)

        data = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(data["assets"][0]["lang"], "zh")
        split_cfg = data["assets"][0]["steps"]["split"]
        play_cfg = data["assets"][0]["steps"]["play"]
        self.assertTrue(split_cfg.get("enabled", False))
        self.assertFalse(play_cfg.get("translate", True))
        self.assertEqual(play_cfg.get("skip_first"), False)
        self.assertEqual(data["assets"][0]["progress_played"], 0)
        self.assertEqual(data["assets"][0]["progress_total"], 0)


if __name__ == "__main__":
    unittest.main()
