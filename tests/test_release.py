"""Offline regression checks for the portable release and real Tk dashboard."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--app", type=Path, default=Path(__file__).resolve().parents[1])
args, test_args = parser.parse_known_args()
APP = args.app.resolve()
sys.path.insert(0, str(APP))
import startup
startup.prepare()
import eve_paths

TEST_ROOT = Path(__file__).resolve().parents[1] / "build" / "test-data"
TEST_ROOT.mkdir(parents=True, exist_ok=True)


class PathTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(dir=TEST_ROOT))

    def find(self, documents=None, **env):
        with patch.object(eve_paths.Path, "home", return_value=self.folder), \
             patch.object(eve_paths, "windows_documents", return_value=documents), \
             patch.dict(os.environ, env, clear=True):
            return Path(eve_paths.find_eve_log_path("Gamelogs"))

    def test_redirected_documents_preferred(self):
        redirected = self.folder / "Redirected Documents"
        log = redirected / "EVE/logs/Gamelogs"
        log.mkdir(parents=True)
        (self.folder / "Documents/EVE/logs/Gamelogs").mkdir(parents=True)
        self.assertEqual(self.find(redirected), log)

    def test_onedrive_fallback(self):
        onedrive = self.folder / "OneDrive - Test"
        log = onedrive / "Documents/EVE/logs/Gamelogs"
        log.mkdir(parents=True)
        self.assertEqual(self.find(OneDriveCommercial=str(onedrive)), log)

    def test_standard_documents(self):
        log = self.folder / "Documents/EVE/logs/Gamelogs"
        log.mkdir(parents=True)
        self.assertEqual(self.find(), log)

    def test_no_logs_uses_current_documents(self):
        documents = self.folder / "Redirected"
        self.assertEqual(self.find(documents), documents / "EVE/logs/Gamelogs")

    def test_linux_fallback_preserved(self):
        log = self.folder / ".eve/sharedcache/tq/logs/Gamelogs"
        log.mkdir(parents=True)
        self.assertEqual(self.find(), log)


class StartupTests(unittest.TestCase):
    def test_missing_script_error_is_logged(self):
        folder = Path(tempfile.mkdtemp(dir=TEST_ROOT))
        before = Path.cwd()
        try:
            with patch.object(startup, "ROOT", folder), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(startup.main(), 1)
            self.assertIn("Missing ratting.py", (folder / "startup.log").read_text())
        finally:
            os.chdir(before)

    def test_runs_ratting_as_main(self):
        with patch.object(sys, "argv", ["startup.py"]), patch.object(startup.runpy, "run_path") as run:
            self.assertEqual(startup.main(), 0)
            run.assert_called_once_with(str(APP / "ratting.py"), run_name="__main__")

    def test_real_dashboard_opens_and_closes(self):
        import ratting
        folder = Path(tempfile.mkdtemp(dir=TEST_ROOT))
        config = folder / "ratting_config.json"
        logs = folder / "Empty Gamelogs"
        logs.mkdir()
        config.write_text(json.dumps({"log_path": str(logs), "tax": 7.5}))
        # Use only fixture data: never inspect a player's logs or clipboard.
        with patch.object(ratting, "CONFIG_FILE", str(config)), \
             patch.object(ratting, "HISTORY_FILE", str(folder / "history.json")), \
             patch.object(ratting, "_TRAY_OK", False), \
             patch.object(ratting, "_CLIP_OK", False), \
             patch.object(ratting.tk.Tk, "mainloop", return_value=None):
            ui = ratting.MainUI()
            try:
                ui.root.update()
                self.assertTrue(ui.root.winfo_exists())
                self.assertIsNotNone(ui._tree)
                self.assertEqual(ui.cfg["log_path"], str(logs))
                self.assertEqual(ui.cfg["tax"], 7.5)
            finally:
                ui._quit()
        self.assertEqual(json.loads(config.read_text())["log_path"], str(logs))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)
