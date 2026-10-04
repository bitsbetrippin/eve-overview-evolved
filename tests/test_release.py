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
APP = args.app.resolve() / "app"
sys.path.insert(0, str(APP))
import startup
startup.prepare()
import eve_paths
import app_paths

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
            self.assertIn("Missing app/app_info.py", (folder / "data/logs/startup.log").read_text())
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
                self.assertEqual(ui.root.title(), ratting.APP_TITLE)
                self.assertIsNotNone(ui._tree)
                self.assertEqual(ui.cfg["log_path"], str(logs))
                self.assertEqual(ui.cfg["tax"], 7.5)
            finally:
                ui._quit()
        self.assertEqual(json.loads(config.read_text())["log_path"], str(logs))


class LayoutTests(unittest.TestCase):
    def test_release_root_has_only_launcher_readme_and_source_metadata(self):
        root = APP.parent
        files = {p.name for p in root.iterdir() if p.is_file()}
        self.assertIn('START.bat', files)
        self.assertIn('README.md', files)
        self.assertLessEqual(files, {'START.bat', 'README.md', '.gitignore'})
        for path in ('app/startup.py', 'app/app_paths.py', 'app/assets/PVE.ico',
                     'docs/USER-GUIDE.md', 'docs/ATTRIBUTION.md', 'runtime/python.exe'):
            self.assertTrue((root/path).is_file(), path)

    def test_state_paths_are_separate_from_application_and_resources(self):
        import ratting
        root = APP.parent
        expected = {'CONFIG_FILE': 'data/ratting_config.json',
                    'HISTORY_FILE': 'data/ratting_history.json',
                    'PRICE_CACHE': 'data/cache/ratting_prices.json',
                    'NAMEID_CACHE': 'data/cache/ratting_nameids.json',
                    'DEBUG_LOG_FILE': 'data/logs/ratting_debug.log'}
        for name, relative in expected.items():
            self.assertEqual(Path(getattr(ratting, name)), root/relative)
        self.assertEqual(ratting._ALERT_AUDIO.assets, APP/'assets')

    def test_resource_paths_are_independent_of_launch_directory(self):
        import ratting
        before = Path.cwd()
        unrelated = Path(tempfile.mkdtemp(dir=TEST_ROOT))
        try:
            os.chdir(unrelated)
            for name in ('assets/PVE.ico', 'assets/initiative.png', 'assets/voices/saml/jammed.wav'):
                self.assertEqual(Path(ratting._get_resource_path(name)), APP/name)
                self.assertTrue(Path(ratting._get_resource_path(name)).is_file())
        finally:
            os.chdir(before)

    def test_legacy_import_preserves_all_bytes_and_originals(self):
        root = Path(tempfile.mkdtemp(dir=TEST_ROOT))/'Upgrade & paths (test)! Ω'
        root.mkdir()
        for i, name in enumerate(app_paths.LEGACY_FILES):
            (root/name).write_bytes(('legacy-Ω-'+str(i)).encode('utf-8'))
        app_paths.prepare_data(root)
        for name, relative in app_paths.LEGACY_FILES.items():
            self.assertEqual((root/relative).read_bytes(), (root/name).read_bytes())

    def test_new_data_takes_precedence_and_second_launch_does_not_reset_it(self):
        root = Path(tempfile.mkdtemp(dir=TEST_ROOT))
        (root/'data').mkdir()
        (root/'ratting_config.json').write_text('{"ewar_voice":"Robot"}')
        config = root/'data/ratting_config.json'
        config.write_text('{"ewar_voice":"SamL"}')
        app_paths.prepare_data(root)
        self.assertEqual(json.loads(config.read_text())['ewar_voice'], 'SamL')
        config.write_text('{"ewar_voice":"Dramatic"}')
        app_paths.prepare_data(root)
        self.assertEqual(json.loads(config.read_text())['ewar_voice'], 'Dramatic')


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)
