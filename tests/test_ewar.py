"""Incoming EWAR direction, offline audio queue and optional logo in real Tk."""
import sys
import io
import json
import hashlib
import math
import threading
import unittest
from unittest.mock import patch
import wave
from array import array
from pathlib import Path

# Reuse the isolated, synthetic fleet harness and its --app argument handling.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_panels as harness
from ewar_alerts import (AlertAudio, FILES, parse_incoming_ewar, amplify_wav, beep_wav,
                         VOICE_FOLDERS, VOLUME_GAINS, DEFAULT_VOICE, DEFAULT_VOLUME)
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
        def play(kind, mode, voice, volume):
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
        audio.pending.extend([(90, 'SCRAM', 'Voice', 'Robot', 'Low (100%)'), (99, 'WEB', 'Voice', 'Robot', 'Low (100%)')])
        audio._drain()
        self.assertEqual(played, [('WEB', 'Voice', 'Robot', 'Low (100%)')])

    def test_bundled_wavs_are_short_audible_pcm(self):
        for path in (harness.APP/'assets'/folder/name for folder in VOICE_FOLDERS.values() for name in FILES.values()):
            with wave.open(str(path), 'rb') as stream:
                self.assertEqual((stream.getnchannels(), stream.getsampwidth()), (1, 2))
                duration = stream.getnframes() / stream.getframerate()
                self.assertGreater(duration, .5)
                self.assertLess(duration, 3)
                samples = array('h', stream.readframes(stream.getnframes()))
                self.assertGreater(max(abs(x) for x in samples), 500)

    @staticmethod
    def wav_samples(data):
        with wave.open(io.BytesIO(data), 'rb') as stream:
            return stream.getparams(), array('h', stream.readframes(stream.getnframes()))

    @staticmethod
    def wav_bytes(samples):
        output=io.BytesIO()
        with wave.open(output, 'wb') as stream:
            stream.setparams((1, 2, 22050, len(samples), 'NONE', 'not compressed'))
            stream.writeframes(array('h', samples).tobytes())
        return output.getvalue()

    def test_gain_is_exact_below_the_limiter_and_low_is_unchanged(self):
        values=[0, 1000, -1000, 4000, -4000]
        original=self.wav_bytes(values)
        self.assertEqual(amplify_wav(original, 1), original)
        for gain in (2,3):
            params, samples=self.wav_samples(amplify_wav(original,gain))
            self.assertEqual(list(samples), [v*gain for v in values])
            self.assertEqual((params.nchannels,params.sampwidth,params.framerate,params.nframes), (1,2,22050,5))

    def test_limiter_never_wraps_and_invalid_gain_is_rejected(self):
        values=[15000, 25000, 32767, -15000, -25000, -32768]
        original=self.wav_bytes(values)
        _, output=self.wav_samples(amplify_wav(original,3))
        for old,new in zip(values,output):
            self.assertEqual(old>0,new>0)
            self.assertLessEqual(abs(new),32767)
        self.assertLess(output[0],output[1])
        for gain in (0,-1,4,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                amplify_wav(original,gain)

    def test_beep_obeys_the_same_volume_levels(self):
        _, low=self.wav_samples(beep_wav(1))
        _, high=self.wav_samples(beep_wav(3))
        self.assertEqual(list(high), [3*x for x in low])

    def test_styles_have_distinct_waveforms(self):
        for name in FILES.values():
            hashes={hashlib.sha256((harness.APP/'assets'/folder/name).read_bytes()).hexdigest()
                    for folder in VOICE_FOLDERS.values()}
            self.assertEqual(len(hashes),4)

    def test_playback_uses_selected_voice_and_gain_in_memory(self):
        audio=AlertAudio(harness.APP/'assets')
        with patch('ewar_alerts.winsound') as sound:
            for voice,folder in VOICE_FOLDERS.items():
                original=(harness.APP/'assets'/folder/FILES['SCRAM']).read_bytes()
                for volume,gain in VOLUME_GAINS.items():
                    audio._play('SCRAM','Voice',voice,volume)
                    self.assertEqual(sound.PlaySound.call_args.args[0],amplify_wav(original,gain))
            audio._play('POINT','Beep','Dramatic','High (300%)')
            self.assertEqual(sound.PlaySound.call_args.args[0],beep_wav(3))
            sound.Beep.assert_not_called()

    def test_queue_preserves_profile_and_normalizes_unknown_settings(self):
        played=[]
        audio=AlertAudio('.',player=lambda *args: played.append(args),clock=lambda:100)
        with patch('ewar_alerts.threading.Thread'):
            audio.notify('SCRAM',voice='Dramatic',volume='High (300%)')
            audio.notify('WEB',voice='unknown',volume='unknown')
        audio._drain()
        self.assertEqual(played,[('SCRAM','Voice','Dramatic','High (300%)'),
                                 ('WEB','Voice','Robot','Low (100%)')])

    def test_missing_style_falls_back_to_original_at_selected_gain(self):
        audio=AlertAudio(harness.APP/'assets')
        with patch('ewar_alerts.voice_wav',side_effect=[FileNotFoundError(),b'robot-wav']) as load, \
             patch('ewar_alerts.winsound') as sound, self.assertLogs(level='ERROR'):
            audio._play('WEB','Voice','Dramatic','High (300%)')
        self.assertEqual(Path(load.call_args.args[0]),harness.APP/'assets/webbed.wav')
        self.assertEqual(load.call_args.args[1],3)
        self.assertEqual(sound.PlaySound.call_args.args[0],b'robot-wav')


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
                notify.assert_called_with(kind, 'Voice', preview=True, voice='Robot', volume='Low (100%)')
        self.settings.audio_var.set('Off')
        self.assertTrue(self.settings._ap_dirty)
        self.settings._apply()
        self.assertEqual(self.ui.cfg['ewar_audio'], 'Off')
        self.assertTrue(self.settings._ap.winfo_viewable())
        self.assertLess(self.settings._ap.winfo_rooty()+self.settings._ap.winfo_height(),
                        self.settings.w.winfo_rooty()+self.settings.w.winfo_height())

    def test_profile_settings_persist_and_preview_before_applying(self):
        self.assertEqual(self.settings.voice_var.get(),DEFAULT_VOICE)
        self.assertEqual(self.settings.volume_var.get(),DEFAULT_VOLUME)
        self.settings.voice_var.set('News anchor')
        self.settings.volume_var.set('High (300%)')
        self.assertTrue(self.settings._ap_dirty)
        with patch.object(ratting._ALERT_AUDIO,'notify') as notify:
            self.settings._audio_test_buttons['POINT'].invoke()
            notify.assert_called_once_with('POINT','Voice',preview=True,voice='News anchor',volume='High (300%)')
        self.assertNotIn('ewar_voice',self.ui.cfg)
        self.settings._apply()
        stored=json.loads(Path(ratting.CONFIG_FILE).read_text(encoding='utf-8'))
        self.assertEqual((stored['ewar_voice'],stored['ewar_volume']),('News anchor','High (300%)'))
        self.settings.w.destroy()
        self.settings=ratting.MainUISettings(self.ui.root,self.ui)
        self.ui.root.update()
        self.assertEqual((self.settings.voice_var.get(),self.settings.volume_var.get()),('News anchor','High (300%)'))
        self.assertTrue(self.settings._ap.winfo_viewable())
        self.assertFalse(self.settings._ap_dirty)

    def test_hidden_log_events_route_only_incoming_audio(self):
        win = self.ui._windows['123']
        self.ui.cfg.update(ewar_voice='Commanding',ewar_volume='Medium (200%)')
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
            self.assertTrue(all(c.kwargs==dict(voice='Commanding',volume='Medium (200%)') for c in notify.call_args_list))
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
