"""Monitor placement and complete fleet/dashboard recovery with synthetic logs."""
import argparse
import contextlib
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
import ratting
import window_placement as placement

AREAS = [(-1920, 0, 0, 1040), (0, 0, 1920, 1040)]


class PlacementTests(unittest.TestCase):
    def test_negative_monitor_coordinates_are_visible(self):
        self.assertTrue(placement.title_visible((-1600, 80, 290, 732), AREAS))

    def test_title_must_be_reachable_on_a_real_monitor(self):
        for rect in ((4000, 80, 290, 732), (100, -500, 290, 732), (1910, 80, 290, 732)):
            self.assertFalse(placement.title_visible(rect, AREAS))
        self.assertFalse(placement.title_visible((2000, 80, 290, 732),
                                                [(0, 0, 1920, 1040), (2560, 0, 4480, 1040)]))

    def test_placement_uses_the_overview_monitor(self):
        for anchor in ((50, 80, 410, 300), (-1800, 80, 410, 300)):
            x, y = placement.position_near(anchor, (290, 732), AREAS)
            self.assertEqual(x, anchor[0] + anchor[2] + 12)
            self.assertEqual(y, anchor[1])

    def test_oversized_panel_keeps_its_title_reachable(self):
        x, y = placement.position_near((1700, 900, 410, 300), (2200, 1400), AREAS)
        self.assertTrue(placement.title_visible((x, y, 2200, 1400), AREAS))


class FleetPanelTests(unittest.TestCase):
    def open_fleet(self, shown=True, geometry=None, collapsed=False, overview_geometry=None):
        base = Path(__file__).resolve().parents[1] / "build/test-data"
        base.mkdir(parents=True, exist_ok=True)
        self.folder = Path(tempfile.mkdtemp(dir=base))
        chars = {}
        for cid, name in (("123", "Test Pilot A"), ("456", "Test Pilot B")):
            (self.folder / f"20260922_120000_{cid}.txt").write_text(f"Listener: {name}\n", encoding="utf-8")
            chars[cid] = {"show": shown, "main_collapsed": collapsed, "main_full_height": 732}
            if geometry:
                chars[cid]["geometry"] = geometry
        cfg = {"log_path": str(self.folder), "chars": chars, "alpha": 1.0,
               "main_ui": {"geometry": overview_geometry or "410x300+50+80"}}
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        for name in ("CONFIG_FILE", "HISTORY_FILE", "PRICE_CACHE", "NAMEID_CACHE"):
            stack.enter_context(patch.object(ratting, name, str(self.folder / (name + ".json"))))
        stack.enter_context(patch.object(ratting, "load_config", return_value=cfg))
        stack.enter_context(patch.object(ratting, "_CLIP_OK", False))
        stack.enter_context(patch.object(ratting, "_TRAY_OK", False))
        stack.enter_context(patch.object(ratting.CharacterWindow, "_download_market_data", return_value=None))
        stack.enter_context(patch.object(ratting.tk.Tk, "mainloop", return_value=None))
        stack.enter_context(patch.object(placement, "work_areas", return_value=AREAS))
        stack.enter_context(patch.object(ratting, "work_areas", return_value=AREAS))
        self.ui = ratting.MainUI()
        self.addCleanup(self.ui._quit)
        self.callback_errors = []
        self.ui.root.report_callback_exception = lambda *error: self.callback_errors.append(error)
        self.addCleanup(lambda: self.assertEqual(self.callback_errors, []))
        self.ui.root.update()
        self.assertEqual(len(self.ui._windows), 2)
        return self.ui

    def assert_visible(self, window):
        self.assertTrue(window.winfo_viewable())
        self.assertTrue(placement.title_visible(placement.rectangle(window), AREAS), placement.rectangle(window))

    def test_new_panels_open_beside_overview_in_a_cascade(self):
        ui = self.open_fleet()
        positions = []
        for win in ui._windows.values():
            self.assert_visible(win.root)
            self.assertLess(abs(win.root.winfo_x() - ui.root.winfo_x()), 600)
            positions.append((win.root.winfo_x(), win.root.winfo_y()))
        self.assertEqual(len(set(positions)), 2)

    def test_saved_offscreen_positions_recover_at_startup(self):
        ui = self.open_fleet(geometry="290x732+30000+30000", overview_geometry="410x300+30000+30000")
        self.assert_visible(ui.root)
        for win in ui._windows.values():
            self.assert_visible(win.root)

    def test_visible_saved_negative_coordinates_are_preserved(self):
        ui = self.open_fleet(geometry="290x732+-1600+80")
        for win in ui._windows.values():
            self.assertEqual(win.root.winfo_x(), -1600)
            self.assertEqual(win.root.winfo_y(), 80)

    def test_show_panels_restores_hidden_collapsed_panels_without_resetting_session(self):
        ui = self.open_fleet(shown=False, geometry="290x32+30000+30000", collapsed=True)
        for win in ui._windows.values():
            self.assertFalse(win.root.winfo_viewable())
            win.data.add_dmg_out(None, 1500, "Test target")
        states = [win._st for win in ui._windows.values()]
        ui._show_panels_button.invoke()
        ui.root.update()
        for win in ui._windows.values():
            self.assert_visible(win.root)
            self.assertFalse(win._is_collapsed)
            self.assertFalse(win._suspended)
            self.assertTrue(win.char_cfg["show"])
            self.assertEqual(win.data.dd, 1500)
            self.assertEqual(win.char_cfg["geometry"], win.root.geometry())
        self.assertEqual(states, [win._st for win in ui._windows.values()])

    def test_row_click_recovers_offscreen_panel_instead_of_hiding_it(self):
        ui = self.open_fleet()
        win = ui._windows["123"]
        win.root.geometry("+30000+30000")
        ui.root.update()
        x, y, width, height = ui._tree.bbox("123", "char")
        ui._tree.event_generate("<ButtonRelease-1>", x=x + 20, y=y + height // 2)
        ui.root.update()
        self.assert_visible(win.root)
        self.assertTrue(win.char_cfg["show"])

    def test_show_panels_recovers_detached_windows(self):
        ui = self.open_fleet()
        win = ui._windows["123"]
        win._detach("isk")
        panel = win._isk_window
        panel.w.geometry("+30000+30000")
        ui._toggle_window("123")
        ui._show_panels_button.invoke()
        ui.root.update()
        self.assert_visible(panel.w)
        self.assertTrue(win._isk_detached)

    def test_fleet_dps_tracks_hidden_pilots_before_first_bounty(self):
        ui = self.open_fleet()
        self.assertGreaterEqual(ui.root.winfo_width(), ui.MAIN_W)
        for cid, damage in (("123", 1500), ("456", 3000)):
            win = ui._windows[cid]
            win._go()
            ui._toggle_window(cid)
            self.assertFalse(win._suspended)
            log = self.folder / f"20260922_120000_{cid}.txt"
            with log.open("a", encoding="utf-8") as stream:
                stream.write(f"[ 2026.09.22 12:00:01 ] (combat) {damage} to Target {cid} - Gun - Hits\n")
            win._read_logs_once()
        ui.root.after_cancel(ui._health_job)
        ui._health_check()
        self.assertEqual(ui._tree.set("123", "target_dps"), "100")
        self.assertEqual(ui._tree.set("456", "target_dps"), "200")
        self.assertFalse(ui._overlays)
        ui._windows["123"].data.combat.last_target_at -= 16
        ui.root.after_cancel(ui._health_job)
        ui._health_check()
        self.assertEqual(ui._tree.set("123", "target_dps"), "0")

    def test_fleet_dps_never_labels_inactive_data_live(self):
        ui = self.open_fleet()
        win = ui._windows["123"]
        for state, expected in (("paused", "PAUSED"), ("stopped", "STOPPED")):
            win._st = state
            ui.root.after_cancel(ui._health_job)
            ui._health_check()
            self.assertEqual(ui._tree.set("123", "target_dps"), expected)
        win._st = "running"
        ui.cfg["bg_monitor"] = False
        ui._toggle_window("123")
        ui.root.after_cancel(ui._health_job)
        ui._health_check()
        self.assertEqual(ui._tree.set("123", "target_dps"), "OFFLINE")
        ui._toggle_window("123")
        win._last_tick_wall = 0
        ui.root.after_cancel(ui._health_job)
        ui._health_check()
        self.assertEqual(ui._tree.set("123", "target_dps"), "NO TICK")

    def test_overlay_toggle_still_uses_its_own_column(self):
        ui = self.open_fleet()
        self.assertEqual(ui._tree.heading("dps", "text"), "OVL")
        x, y, width, height = ui._tree.bbox("123", "dps")
        with patch.object(ui, "_toggle_overlay") as toggle:
            ui._tree.event_generate("<ButtonRelease-1>", x=x + width // 2, y=y + height // 2)
            ui.root.update()
            toggle.assert_called_once_with("123")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)
