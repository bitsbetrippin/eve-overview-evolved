"""Incoming EWAR direction, offline audio queue and optional logo in real Tk."""
import sys
import threading
import unittest
from unittest.mock import patch
import wave
from array import array
from pathlib import Path

# Reuse the isolated, synthetic fleet harness and its --app argument handling.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_panels as harness
from ewar_alerts import AlertAudio, FILES, parse_incoming_ewar
ratting = harness.ratting


class ParserTests(unittest.TestCase):
    def test_scram_and_point_have_distinct_types(self):
        for action, expected in (("scramble", "SCRAM"), ("disruption", "POINT")):
            self.assertEqual(parse_incoming_ewar(f"(combat) Warp {action} attempt from Pilot [ABC](Loki) to you!"),
                             (expected, "Pilot [ABC](Loki)"))

    def test_rich_incoming_names_and_entities(self):
        line = '(combat) <color=0xffffffff><b>Warp scramble attempt</b> <font size=10>from</font> <b>Renée &amp; Co.[ABC]</b> <font size=10>to <b></font>you!'
        self.assertEqual(parse_incoming_ewar(line), ('SCRAM', 'Renée & Co.[ABC]'))

    def test_nearby_outgoing_and_drone_tackle_do_not_alert(self):
        for target in ('Target Pilot', "'Augmented' Warrior", 'younger Pilot'):
            for action in ('scramble', 'disruption'):
                self.assertIsNone(parse_incoming_ewar(f'(combat) <b>Warp {action} attempt</b> from <b>Guardian Agent</b> to <b>{target}</b>'))
        self.assertIsNone(parse_incoming_ewar('(combat) Warp scramble attempt from you to Pirate!'))

    def test_web_accepts_punctuation_and_tags(self):
        self.assertEqual(parse_incoming_ewar('(notify) <b>Jane D\'oe [ABC-1](Huginn)</b> has started webifying you.'),
                         ('WEB', "Jane D'oe [ABC-1](Huginn)"))

    def test_other_messages_do_not_trigger(self):
        for line in ('(notify) Pirate has stopped webifying you.', '(notify) You have started webifying Pirate',
                     '(combat) 500 from Pirate - Gun - Hits', '(notify) Warp scramble attempt failed',
                     'Pilot > Warp scramble attempt from Pirate to you!'):
            self.assertIsNone(parse_incoming_ewar(line))


class AudioTests(unittest.TestCase):
    def test_queue_serializes_all_three_and_limits_repeats(self):
        entered, release = threading.Event(), threading.Event()
        played = []
        def play(kind, mode):
            played.append((kind, mode))
            entered.set()
            release.wait(3)
        audio = AlertAudio('.', player=play, clock=lambda: 100)
        self.addCleanup(release.set)
        self.assertTrue(audio.notify('SCRAM'))
        self.assertTrue(entered.wait(2))
        worker = audio.worker
        self.assertFalse(audio.notify('SCRAM'))
        self.assertTrue(audio.notify('POINT'))
        self.assertTrue(audio.notify('WEB'))
        self.assertEqual(played, [('SCRAM', 'Voice')])
        release.set()
        worker.join(3)
        self.assertEqual(played, [('SCRAM', 'Voice'), ('POINT', 'Voice'), ('WEB', 'Voice')])
        self.assertFalse(worker.is_alive())

    def test_cooldown_off_and_invalid_modes(self):
        now = [100]
        audio = AlertAudio('.', player=lambda *_: None, clock=lambda: now[0])
        for mode in ('Off', 'invalid'):
            self.assertFalse(audio.notify('WEB', mode))
        self.assertFalse(audio.notify('UNKNOWN'))
        with patch('ewar_alerts.threading.Thread'):
            self.assertTrue(audio.notify('WEB'))
            audio.pending.clear()
            now[0] = 109
            self.assertFalse(audio.notify('WEB'))
            now[0] = 110
            self.assertTrue(audio.notify('WEB'))
            audio.clear()
            self.assertFalse(audio.pending)

    def test_stale_queue_is_discarded(self):
        played = []
        audio = AlertAudio('.', player=lambda *args: played.append(args), clock=lambda: 100)
        audio.pending.extend([(90, 'SCRAM', 'Voice'), (99, 'WEB', 'Voice')])
        audio._drain()
        self.assertEqual(played, [('WEB', 'Voice')])

    def test_bundled_wavs_are_short_audible_pcm(self):
        for name in FILES.values():
            with wave.open(str(harness.APP/'assets'/name), 'rb') as stream:
                self.assertEqual((stream.getnchannels(), stream.getsampwidth()), (1, 2))
                duration = stream.getnframes() / stream.getframerate()
                self.assertGreater(duration, .5)
                self.assertLess(duration, 3)
                samples = array('h', stream.readframes(stream.getnframes()))
                self.assertGreater(max(abs(x) for x in samples), 500)


class UISettingsTests(unittest.TestCase):
    def setUp(self):
        self.case = harness.FleetPanelTests()
        self.addCleanup(self.case.doCleanups)
        self.ui = self.case.open_fleet()
        self.settings = ratting.MainUISettings(self.ui.root, self.ui)
        self.ui.root.update()

    def test_logo_apply_and_hide_preserves_dps_and_fits(self):
        win = self.ui._windows['123']
        win.data.combat.add('to', 18750, 'Target')
        old_height = win.root.winfo_height()
        self.assertFalse(win._initiative_badge.winfo_manager())
        self.settings._logo_check.invoke()
        self.assertTrue(self.settings._ap_dirty)
        self.settings._apply()
        self.ui.root.update()
        win._update_combat_meters()
        self.ui.root.update()
        self.assertTrue(win._initiative_badge.winfo_viewable())
        self.assertTrue(self.ui._initiative_badge.winfo_viewable())
        self.assertEqual(win._target_dps_label.cget('text'), '1,250 DPS')
        self.assertLessEqual(win._meter_dps_font.measure('1,250 DPS'), win._target_dps_label.winfo_width())
        self.assertTrue(self.ui.cfg['initiative_logo'])
        self.assertGreater(win.root.winfo_height(), old_height)
        self.assertFalse(self.settings._ap_dirty)
        self.settings._logo_check.invoke()
        self.settings._apply()
        self.ui.root.update()
        self.assertFalse(win._initiative_badge.winfo_viewable())
        self.assertEqual(win.data.combat.snapshot()['target_dps'], 1250)

    def test_sound_setting_and_preview_buttons(self):
        with patch.object(ratting._ALERT_AUDIO, 'notify') as notify:
            for kind, button in self.settings._audio_test_buttons.items():
                button.invoke()
                notify.assert_called_with(kind, 'Voice', preview=True)
        self.settings.audio_var.set('Off')
        self.assertTrue(self.settings._ap_dirty)
        self.settings._apply()
        self.assertEqual(self.ui.cfg['ewar_audio'], 'Off')
        self.assertTrue(self.settings._ap.winfo_viewable())
        self.assertLess(self.settings._ap.winfo_rooty()+self.settings._ap.winfo_height(),
                        self.settings.w.winfo_rooty()+self.settings.w.winfo_height())

    def test_hidden_log_events_route_only_incoming_audio(self):
        win = self.ui._windows['123']
        win._go()
        self.ui._toggle_window('123')
        lines = ['(combat) Warp scramble attempt from Pirate to you!',
                 '(combat) Warp disruption attempt from Pirate to you!',
                 '(notify) Pirate has started webifying you',
                 '(combat) <b>Warp scramble attempt</b> from <b>Pirate</b> to <b>Someone Else</b>']
        with (self.case.folder/'20260922_120000_123.txt').open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(lines)+'\n')
        with patch.object(ratting._ALERT_AUDIO, 'notify') as notify, patch.object(win, '_flash_alert', wraps=win._flash_alert):
            win._read_logs_once()
            self.assertEqual([c.args for c in notify.call_args_list], [('SCRAM','Voice'),('POINT','Voice'),('WEB','Voice')])
            win._read_logs_once()
            self.assertEqual(notify.call_count, 3)
        self.assertEqual([a[1] for a in win.data.alerts], ['SCRAM','POINT','WEB'])
        self.ui.root.update()
        # Let the short visual pulses finish before destroying the window.
        for job in win.root.tk.call('after', 'info'):
            info = str(win.root.tk.call('after', 'info', job))
            if '<lambda>' in info:
                win.root.after_cancel(job)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + harness.test_args, verbosity=2)
