"""Synthetic combat logs exercise damage attribution and the real pilot window."""
import argparse
import contextlib
from datetime import datetime, timezone
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
import combat_meter
from combat_meter import CombatMeter, parse_damage
import ratting


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(combat_meter.time, "monotonic", return_value=100)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.meter = CombatMeter()

    def test_plain_names_and_ship_tags(self):
        self.assertEqual(parse_damage("[ 2026.09.22 12:00:00 ] (combat) 1,500 from Jane D'oe[ABC-1](Vedmak) - Gun - Hits"),
                         ("from", 1500, "Jane D'oe[ABC-1](Vedmak)"))

    def test_rich_combat_line(self):
        self.assertEqual(parse_damage("(combat) <color=0xff00ffff><b>787</b> <color=0x77ffffff><font size=10>to</font> <b><color=0xffffffff>Caldari Navy Wasp</b><font size=10><color=0x77ffffff> - Caldari Navy Wasp - Penetrates"),
                         ("to", 787, "Caldari Navy Wasp"))

    def test_nested_html_entities_and_unicode(self):
        self.assertEqual(parse_damage("(combat) <b>42</b> from <b><color=x>Renée &amp; Co. (Vexor)</color></b> - Drones - Hits"),
                         ("from", 42, "Renée & Co. (Vexor)"))

    def test_misses_and_ewar_are_not_damage(self):
        for line in ("(combat) Your Ogre II misses Pirate completely",
                     "(combat) Warp scramble attempt from Pirate to you!",
                     "(bounty) 500 ISK added to next bounty payout"):
            self.assertIsNone(parse_damage(line))

    def test_target_switch_does_not_mix_damage(self):
        self.meter.add("to", 1500, "Target A")
        self.meter.add("to", 300, "Target B")
        self.assertEqual(self.meter.snapshot()["target"], "Target B")
        self.assertEqual(self.meter.snapshot()["target_dps"], 20)
        self.meter.add("to", 150, "Target A")
        self.assertEqual(self.meter.snapshot()["target_dps"], 110)

    def test_top_three_aggregate_and_rank(self):
        for name, damage in (("A", 300), ("B", 100), ("C", 400), ("B", 600), ("D", 50)):
            self.meter.add("from", damage, name)
        top = self.meter.snapshot()["attackers"]
        self.assertEqual([(name, total) for name, total, _ in top], [("B", 700), ("C", 400), ("A", 300)])

    def test_idle_expires_and_target_clears(self):
        self.meter.add("to", 1500, "Old target")
        self.meter.add("from", 1500, "Old attacker")
        self.now.return_value = 115
        self.assertEqual(self.meter.snapshot(), {"target": None, "target_dps": 0, "attackers": []})
        self.assertEqual(self.meter.outgoing, {})
        self.assertEqual(self.meter.incoming, {})

    def test_rank_changes_as_old_hits_expire(self):
        self.meter.add("from", 1500, "A")
        self.now.return_value = 105
        self.meter.add("from", 300, "B")
        self.now.return_value = 115
        self.assertEqual(self.meter.snapshot()["attackers"], [("B", 300, 20)])

    def test_capacity_eviction_keeps_totals_correct(self):
        meter = CombatMeter(max_events=2)
        meter.add("from", 100, "A")
        meter.add("from", 200, "A")
        meter.add("from", 600, "B")
        self.assertEqual(meter.snapshot()["attackers"], [("B", 600, 40), ("A", 200, 200 / 15)])

    def test_data_reset_clears_both_meters(self):
        data = ratting.Data()
        data.add_dmg_out(None, 1500, "Target")
        data.add_dmg_in(None, 300, "Attacker")
        self.assertEqual(data.dd, 1500)
        self.assertEqual(data.dr, 300)
        self.assertEqual(data.dps(True), 100)
        data.reset()
        self.assertEqual(data.combat.snapshot(), {"target": None, "target_dps": 0, "attackers": []})


class PilotWindowTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / "build/test-data"
        test_root.mkdir(parents=True, exist_ok=True)
        self.folder = Path(tempfile.mkdtemp(dir=test_root))
        self.log = self.folder / "20260922_120000_123.txt"
        self.log.write_text("Listener: Test Pilot\n", encoding="utf-8")
        self.patches = contextlib.ExitStack()
        self.addCleanup(self.patches.close)
        for name in ("CONFIG_FILE", "HISTORY_FILE", "PRICE_CACHE", "NAMEID_CACHE"):
            self.patches.enter_context(patch.object(ratting, name, str(self.folder / (name + ".json"))))
        self.patches.enter_context(patch.object(ratting, "_CLIP_OK", False))
        self.patches.enter_context(patch.object(ratting, "_TRAY_OK", False))
        self.patches.enter_context(patch.object(ratting.CharacterWindow, "_download_market_data", return_value=None))
        self.clock = self.patches.enter_context(patch.object(combat_meter.time, "monotonic", return_value=100))
        self.root = ratting.tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        cfg = {"log_path": str(self.folder), "tax": 7.5, "alpha": 1.0}
        self.win = ratting.CharacterWindow(self.root, None, "123", "Test Pilot", str(self.log), cfg)
        self.addCleanup(self.win._quit)
        self.win.root.deiconify()
        self.root.update()

    def hit(self, direction, amount, name):
        self.win._parse(f"[ 2026.09.22 12:00:00 ] (combat) {amount} {direction} {name} - Gun - Hits")

    def test_log_reader_updates_visible_meters(self):
        self.win._go()
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write("[ 2026.09.22 12:00:00 ] (combat) 1500 to Core Admiral - Railgun - Hits\n")
            stream.write("[ 2026.09.22 12:00:00 ] (combat) 450 from Core Admiral - Railgun - Hits\n")
        self.win._read_logs_once()
        self.win._update_combat_meters()
        self.assertEqual(self.win._target_dps_label.cget("text"), "100 DPS")
        self.assertEqual(self.win._target_name_label.cget("text"), "Core Admiral")
        self.assertEqual(self.win._incoming_rows[0][1].cget("text"), "30 DPS")
        self.assertEqual(self.win._meter_status.cget("text"), "LIVE")

    def test_stop_freezes_and_reset_clears(self):
        self.win._go()
        self.hit("to", 1500, "Target")
        self.hit("from", 450, "Attacker")
        self.win._stop()
        self.clock.return_value = 200
        self.win._update_combat_meters()
        self.assertEqual(self.win._target_dps_label.cget("text"), "100 DPS")
        self.assertEqual(self.win._incoming_rows[0][1].cget("text"), "30 DPS")
        self.assertEqual(self.win._meter_status.cget("text"), "STOPPED")
        self.win._reset()
        self.win._update_combat_meters()
        self.assertEqual(self.win._target_dps_label.cget("text"), "0 DPS")
        self.assertEqual(self.win._incoming_rows[0][0].cget("text"), "No incoming damage")

    def test_theme_preserves_bold_aqua_and_red(self):
        self.win._current_theme = next(name for name in ratting.THEMES if name != ratting.THEME_DEFAULT)
        self.win._apply_theme_live()
        for widget, color in self.win._combat_fixed_colors:
            self.assertEqual(widget.cget("fg"), color)
            font = ratting.tkfont.Font(font=widget.cget("font"))
            self.assertEqual(font.actual("weight"), "bold")

    def test_layout_and_long_names(self):
        name = "Extremely Long Pirate Name [VERY-LONG-CORPORATION](Vindicator)"
        self.hit("to", 15000, name)
        self.hit("from", 15000, name)
        self.win._update_combat_meters()
        self.root.update()
        self.assertIn("…", self.win._target_name_label.cget("text"))
        self.assertIn(name, self.win._incoming_tooltip(0))
        self.assertLess(self.win._combat_container.winfo_y(), self.win._incoming_container.winfo_y())
        self.assertLess(self.win._incoming_container.winfo_y(), self.win._ctrl_frame.winfo_y())
        self.assertEqual(self.win.root.winfo_width(), ratting.WIN_W)
        for label in (self.win._target_name_label, self.win._incoming_rows[0][0]):
            font = ratting.tkfont.Font(font=label.cget("font"))
            self.assertLessEqual(font.measure(label.cget("text")), label.winfo_width())


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)
