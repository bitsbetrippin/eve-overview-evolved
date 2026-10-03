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
from ewar_alerts import (AlertAudio, FILES, parse_incoming_ewar, parse_ewar, amplify_wav, beep_wav,
                         VOICE_FOLDERS, VOLUME_GAINS, DEFAULT_VOICE, DEFAULT_VOLUME, voice_files)
ratting = harness.ratting


class ParserTests(unittest.TestCase):
    def test_scram_and_point_have_distinct_types(self):
        for action, expected in (("scramble", "SCRAM"), ("disruption", "POINT")):
            self.assertEqual(parse_incoming_ewar(f"(combat) Warp {action} attempt from Pilot [ABC](Loki) to you!"),
                             (expected, "Pilot [ABC](Loki)"))

    def test_rich_incoming_names_and_entities(self):
        line = '(combat) <color=0xffffffff><b>Warp scramble attempt</b> <font size=10>from</font> <b>Renée &amp; Co.[ABC]</b> <font size=10>to <b></font>you!'
        self.assertEqual(parse_incoming_ewar(line), ('SCRAM', 'Renée & Co.[ABC]'))

    def test_nearby_outgoing_and_drone_tackle_are_not_personal(self):
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

    def test_explicit_recipients_include_other_pilots_drones_and_outgoing(self):
        for source in ('Pirate', 'you'):
            for target in ('Target Pilot', "\'Augmented\' Warrior", 'younger Pilot', 'Your ship'):
                for action, kind in (('scramble', 'SCRAM'), ('disruption', 'POINT')):
                    line = f'[ 2026.10.03 12:00:00 ] (combat) <b>Warp {action} attempt</b> from <b>{source}</b> to <b>{target}</b>!'
                    event = parse_ewar(line)
                    self.assertEqual((event.kind, event.source, event.target), (kind, source, target))
                    self.assertFalse(event.incoming)

    def test_web_recipients_and_html_are_preserved(self):
        for source, verb in (('Renée &amp; Co.', 'has'), ('You', 'have')):
            event = parse_ewar(f'(notify) <b>{source}</b> {verb} started webifying <b>Other Pilot</b>.')
            self.assertEqual((event.kind, event.target, event.incoming), ('WEB', 'Other Pilot', False))
        event = parse_ewar('(notify) Pirate has started webifying YOU!')
        self.assertTrue(event.incoming)
        self.assertEqual(event.target, 'YOU')

    def test_missing_recipients_and_unrelated_messages_are_ignored(self):
        for line in ('(combat) Warp scramble attempt from Pirate to ',
                     '(combat) Warp disruption attempt from Pirate to !',
                     '(notify) Pirate has started webifying ',
                     '(notify) Pirate has stopped webifying Other Pilot.',
                     'Pilot > (combat) Warp scramble attempt from Pirate to you!',
                     '(combat) 500 from Pirate - Gun - Hits',
                     '(notify) You are jammed!',
                     '(combat) Warp scramble attempt from you to you!'):
            self.assertIsNone(parse_ewar(line), line)


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
        audio.pending.extend([(90, 'SCRAM', 'Voice', 'Robot', 'Low (100%)', False), (99, 'WEB', 'Voice', 'Robot', 'Low (100%)', False)])
        audio._drain()
        self.assertEqual(played, [('WEB', 'Voice', 'Robot', 'Low (100%)')])

    def test_nearby_forces_beep_and_never_uses_or_blocks_personal_voice(self):
        played = []
        audio = AlertAudio('.', player=lambda *args: played.append(args), clock=lambda: 100)
        with patch('ewar_alerts.threading.Thread'):
            self.assertTrue(audio.notify('SCRAM', voice='SamL', volume='High (300%)', nearby=True))
            self.assertTrue(audio.notify('SCRAM', voice='SamL', volume='High (300%)'))
            self.assertFalse(audio.notify('SCRAM', nearby=True))
            self.assertFalse(audio.notify('SCRAM'))
        audio._drain()
        self.assertEqual(played, [('SCRAM', 'Voice', 'SamL', 'High (300%)'),
                                 ('SCRAM', 'Beep', 'SamL', 'High (300%)')])

    def test_personal_queue_takes_priority_during_nearby_playback(self):
        entered, release = threading.Event(), threading.Event()
        played = []
        def play(*args):
            played.append(args[:2])
            entered.set()
            release.wait(3)
        audio = AlertAudio('.', player=play, clock=lambda: 100)
        self.addCleanup(release.set)
        audio.notify('WEB', nearby=True)
        self.assertTrue(entered.wait(2))
        worker = audio.worker
        audio.notify('POINT', nearby=True)
        audio.notify('SCRAM', nearby=True)
        audio.notify('SCRAM', voice='SamL')
        audio.notify('POINT', voice='SamL')
        audio.notify('WEB', voice='SamL')
        release.set()
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(played, [('WEB','Beep'), ('SCRAM','Voice'), ('POINT','Voice'),
                                 ('WEB','Voice'), ('POINT','Beep'), ('SCRAM','Beep')])

    def test_nearby_off_beep_mode_and_jam_placeholder(self):
        played = []
        audio = AlertAudio('.', player=lambda *args: played.append(args), clock=lambda: 100)
        with patch('ewar_alerts.threading.Thread'):
            self.assertFalse(audio.notify('WEB', 'Off', nearby=True))
            self.assertFalse(audio.notify('JAM', voice='SamL', nearby=True, preview=True))
            self.assertTrue(audio.notify('WEB', 'Beep'))
            self.assertTrue(audio.notify('WEB', 'Beep', nearby=True))
        audio._drain()
        self.assertEqual([a[:2] for a in played], [('WEB','Beep'), ('WEB','Beep')])

    def test_nearby_expiry_and_clear(self):
        now = [100]
        played = []
        audio = AlertAudio('.', player=lambda *args: played.append(args), clock=lambda: now[0])
        with patch('ewar_alerts.threading.Thread'):
            audio.notify('WEB', nearby=True)
            now[0] = 109
            audio.notify('POINT')
        audio._drain()
        self.assertEqual([a[:2] for a in played], [('POINT', 'Voice')])
        with patch('ewar_alerts.threading.Thread'):
            audio.notify('SCRAM', nearby=True)
            audio.notify('SCRAM')
            audio.clear()
            self.assertFalse(audio.pending)
            self.assertFalse(audio.nearby_pending)
            self.assertFalse(audio.last)

    def test_nearby_and_personal_cooldowns_expire_independently(self):
        now = [100]
        audio = AlertAudio('.', player=lambda *_: None, clock=lambda: now[0])
        with patch('ewar_alerts.threading.Thread'):
            self.assertTrue(audio.notify('POINT', nearby=True))
            audio.nearby_pending.clear()
            now[0] = 105
            self.assertTrue(audio.notify('POINT'))
            audio.pending.clear()
            now[0] = 110
            self.assertTrue(audio.notify('POINT', nearby=True))
            self.assertFalse(audio.notify('POINT'))
            now[0] = 115
            self.assertTrue(audio.notify('POINT'))

    def test_bundled_wavs_are_short_audible_pcm(self):
        for path in (harness.APP/'assets'/folder/name for voice,folder in VOICE_FOLDERS.items() for name in voice_files(voice).values()):
            with wave.open(str(path), 'rb') as stream:
                self.assertEqual((stream.getnchannels(), stream.getsampwidth()), (1, 2))
                duration = stream.getnframes() / stream.getframerate()
                self.assertGreater(duration, .5)
                self.assertLess(duration, 5)
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
            self.assertEqual(len(hashes),len(VOICE_FOLDERS))

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

    def test_saml_jam_is_preview_only_and_other_styles_cannot_play_it(self):
        played=[]
        audio=AlertAudio('.',player=lambda *args: played.append(args),clock=lambda:100)
        with patch('ewar_alerts.threading.Thread'):
            self.assertFalse(audio.notify('JAM',voice='SamL'))
            self.assertFalse(audio.notify('JAM',voice='Robot',preview=True))
            self.assertTrue(audio.notify('JAM',voice='SamL',volume='High (300%)',preview=True))
        audio._drain()
        self.assertEqual(played,[('JAM','Voice','SamL','High (300%)')])
        self.assertIsNone(parse_incoming_ewar('(notify) You are jammed!'))

    def test_saml_preview_plays_full_clip_with_gain(self):
        original=(harness.APP/'assets/voices/saml/jammed.wav').read_bytes()
        audio=AlertAudio(harness.APP/'assets')
        with patch('ewar_alerts.winsound') as sound:
            audio._play('JAM','Voice','SamL','High (300%)')
        result=sound.PlaySound.call_args.args[0]
        self.assertEqual(result,amplify_wav(original,3))
        before,_=self.wav_samples(original)
        after,_=self.wav_samples(result)
        self.assertEqual(before.nframes,after.nframes)

    def test_all_four_saml_previews_survive_the_live_alert_expiry(self):
        played=[]
        audio=AlertAudio('.',player=lambda *args: played.append(args),clock=lambda:100)
        with patch('ewar_alerts.threading.Thread'):
            for kind in ('SCRAM','POINT','WEB','JAM'):
                self.assertTrue(audio.notify(kind,voice='SamL',preview=True))
        audio.clock=lambda:115
        audio._drain()
        self.assertEqual([p[0] for p in played],['SCRAM','POINT','WEB','JAM'])

    def test_imported_saml_files_match_the_conversion_manifest(self):
        folder=harness.APP/'assets/voices/saml'
        records=json.loads((folder/'import-manifest.json').read_text())
        self.assertEqual({r['output'] for r in records},set(voice_files('SamL').values()))
        for record in records:
            self.assertEqual(hashlib.sha256((folder/record['output']).read_bytes()).hexdigest(),record['output_sha256'])
            with wave.open(str(folder/record['output']),'rb') as stream:
                self.assertAlmostEqual(stream.getnframes()/stream.getframerate(),record['duration_seconds'],places=2)


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
                if kind == 'JAM':
                    self.assertEqual(str(button.cget('state')),'disabled')
                    continue
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

    def test_saml_selection_enables_placeholder_and_persists(self):
        self.settings.voice_var.set('SamL')
        self.settings.volume_var.set('Medium (200%)')
        self.assertEqual(str(self.settings._audio_test_buttons['JAM'].cget('state')),'normal')
        self.assertIn('preview only',self.settings._jam_preview_note.cget('text'))
        with patch.object(ratting._ALERT_AUDIO,'notify') as notify:
            self.settings._audio_test_buttons['JAM'].invoke()
            notify.assert_called_once_with('JAM','Voice',preview=True,voice='SamL',volume='Medium (200%)')
        self.settings._apply()
        saved=json.loads(Path(ratting.CONFIG_FILE).read_text(encoding='utf-8'))
        self.assertEqual(saved['ewar_voice'],'SamL')
        self.settings.w.destroy()
        self.settings=ratting.MainUISettings(self.ui.root,self.ui)
        self.ui.root.update()
        self.assertEqual(self.settings.voice_var.get(),'SamL')
        self.assertEqual(str(self.settings._audio_test_buttons['JAM'].cget('state')),'normal')
        self.settings.voice_var.set('Robot')
        self.assertEqual(str(self.settings._audio_test_buttons['JAM'].cget('state')),'disabled')

    def test_log_reader_plays_nearby_beep_and_selected_personal_voice(self):
        win = self.ui._windows['123']
        self.ui.cfg.update(ewar_audio='Voice', ewar_voice='SamL', ewar_volume='Medium (200%)')
        win._go()
        played = []
        audio = AlertAudio('.', player=lambda *args: played.append(args), clock=lambda: 100)
        with (self.case.folder/'20260922_120000_123.txt').open('a', encoding='utf-8') as stream:
            stream.write('(combat) Warp scramble attempt from Pirate to Drone!\n'
                         '(combat) Warp scramble attempt from Pirate to you!\n')
        with patch.object(ratting, '_ALERT_AUDIO', audio), patch('ewar_alerts.threading.Thread'), \
             patch.object(win, '_flash_alert', side_effect=win._ewar_sound):
            win._read_logs_once()
            win._read_logs_once()
        audio._drain()
        self.assertEqual(played, [('SCRAM', 'Voice', 'SamL', 'Medium (200%)'),
                                 ('SCRAM', 'Beep', 'SamL', 'Medium (200%)')])
        self.assertEqual([a[1] for a in win.data.alerts], ['SCRAM'])

    def test_log_routing_respects_beep_only_and_mute_settings(self):
        win = self.ui._windows['123']
        for mode, expected in (('Beep', [('WEB', 'Beep'), ('WEB', 'Beep')]), ('Off', [])):
            self.ui.cfg.update(ewar_audio=mode, ewar_voice='SamL')
            played = []
            audio = AlertAudio('.', player=lambda *args: played.append(args[:2]), clock=lambda: 100)
            with patch.object(ratting, '_ALERT_AUDIO', audio), patch('ewar_alerts.threading.Thread'), \
                 patch.object(win, '_flash_alert', side_effect=win._ewar_sound):
                win._parse('(notify) Pirate has started webifying Other Pilot.')
                win._parse('(notify) Pirate has started webifying you.')
            audio._drain()
            self.assertEqual(played, expected)

    def test_hidden_log_events_route_by_recipient_without_false_personal_alerts(self):
        win = self.ui._windows['123']
        self.ui.cfg.update(ewar_voice='SamL',ewar_volume='Medium (200%)')
        win._go()
        self.ui._toggle_window('123')
        lines = ['(combat) Warp scramble attempt from Pirate to you!',
                 '(combat) Warp disruption attempt from Pirate to you!',
                 '(notify) Pirate has started webifying you',
                 '(combat) <b>Warp scramble attempt</b> from <b>Pirate</b> to <b>Someone Else</b>',
                 '(combat) Warp disruption attempt from Pirate to Drone!',
                 '(notify) Pirate has started webifying Someone Else.',
                 '(combat) Warp scramble attempt from you to Pirate!']
        with (self.case.folder/'20260922_120000_123.txt').open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(lines)+'\n')
        with patch.object(ratting._ALERT_AUDIO, 'notify') as notify, patch.object(win, '_flash_alert', wraps=win._flash_alert) as flash:
            win._read_logs_once()
            self.assertEqual([c.args for c in notify.call_args_list],
                             [('SCRAM','Voice'),('POINT','Voice'),('WEB','Voice'),
                              ('SCRAM','Voice'),('POINT','Voice'),('WEB','Voice'),('SCRAM','Voice')])
            for i, call in enumerate(notify.call_args_list):
                expected = dict(voice='SamL', volume='Medium (200%)')
                if i >= 3:
                    expected['nearby'] = True
                self.assertEqual(call.kwargs, expected)
            self.assertEqual(flash.call_count, 3)
            win._read_logs_once()
            self.assertEqual(notify.call_count, 7)
        self.assertEqual([a[1] for a in win.data.alerts], ['SCRAM','POINT','WEB'])
        self.ui.root.update()
        # Let the short visual pulses finish before destroying the window.
        for job in win.root.tk.call('after', 'info'):
            info = str(win.root.tk.call('after', 'info', job))
            if '<lambda>' in info:
                win.root.after_cancel(job)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + harness.test_args, verbosity=2)
