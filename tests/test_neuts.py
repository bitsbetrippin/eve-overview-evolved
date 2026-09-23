"""Anonymized real log format, incoming-only accounting and visible Tk panel."""
from datetime import datetime
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_combat as harness
from neut_meter import CapDrainEvent, CapDrainMeter, parse_incoming_cap_drain, source_label

ratting = harness.ratting
LINES = (Path(__file__).parent / 'fixtures/incoming_neuts.txt').read_text(encoding='utf-8').splitlines()
CAP_LINES = (Path(__file__).parent / 'fixtures/incoming_cap_drain.txt').read_text(encoding='utf-8').splitlines()
NOS_LINES = [line for line in CAP_LINES if 'energy drained to' in line]


class NeutTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(harness.combat_meter.time, 'monotonic', return_value=100)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.meter = CapDrainMeter()

    def test_real_format_totals_and_timed_rate(self):
        first = datetime.strptime(LINES[0][2:21], '%Y.%m.%d %H:%M:%S')
        for line in LINES:
            timestamp = datetime.strptime(line[2:21], '%Y.%m.%d %H:%M:%S')
            self.now.return_value = 100 + (timestamp - first).total_seconds()
            self.meter.add(parse_incoming_cap_drain(line))
        state = self.meter.snapshot()
        self.assertEqual(state['total_gj'], 1126)
        self.assertEqual(state['hits'], 20)
        self.assertAlmostEqual(state['gj_per_second'], 281 / 15)
        self.assertEqual([(source_label(s['source']), s['total_gj']) for s in state['sources']],
                         [('Pilot Alpha', 846), ('Pilot Beta', 280)])
        self.assertEqual(state['sources'][0]['module'], 'Small Energy Neutralizer II')

    def test_zero_damage_idle_keeps_session_totals(self):
        self.meter.add(parse_incoming_cap_drain(LINES[0]))
        self.now.return_value = 115
        state = self.meter.snapshot()
        self.assertEqual(state['gj_per_second'], 0)
        self.assertEqual(state['total_gj'], 47)
        self.assertEqual(state['sources'][0]['total_gj'], 47)

    def test_other_colors_and_directionless_plain_text_are_ignored(self):
        for color in ('0xff7fffff', '0xff00ffff', '0xffffffff'):
            self.assertIsNone(parse_incoming_cap_drain(LINES[0].replace('0xffe57f7f', color)))
        self.assertIsNone(parse_incoming_cap_drain('(combat) 47 GJ energy neutralized Pilot - Neut'))

    def test_marker_in_source_cannot_turn_outgoing_into_incoming(self):
        line = LINES[0].replace('0xffe57f7f', '0xff00ffff').replace('Pilot Alpha', '<color=0xffe57f7f>Pilot Alpha')
        self.assertIsNone(parse_incoming_cap_drain(line))

    def test_directionless_drain_and_capacitor_transfer_are_ignored(self):
        for action in ('energy drained', 'energy transferred', 'energy received'):
            self.assertIsNone(parse_incoming_cap_drain(LINES[0].replace('energy neutralized', action)))

    def test_decimals_separators_entities_and_hyphenated_sources(self):
        line = '(combat) <color=0xffe57f7f><b>1,234.5 GJ</b> energy neutralized Jane - D\'oe &amp; Co. - Heavy Neutralizer'
        event = parse_incoming_cap_drain(line)
        self.assertEqual(event, CapDrainEvent(1234.5, "Jane - D'oe & Co.", 'Heavy Neutralizer'))

    def test_blank_source_keeps_amount(self):
        event = parse_incoming_cap_drain('(combat) <color=0xffe57f7f>47 GJ energy neutralized <b></b> - Small Energy Neutralizer II')
        self.assertEqual(event.source, 'Unknown source')
        self.assertEqual(event.amount, 47)

    def test_neuts_are_never_hull_damage(self):
        for line in LINES:
            self.assertIsNone(harness.parse_damage(line))

    def test_bounded_recent_events_do_not_drop_session_totals(self):
        meter = CapDrainMeter(max_events=2)
        for amount, name in ((100, 'A'), (200, 'B'), (300, 'C')):
            meter.add(CapDrainEvent(amount, name, 'Neutralizer'))
        state = meter.snapshot()
        self.assertEqual(state['total_gj'], 600)
        self.assertAlmostEqual(state['gj_per_second'], 500 / 15)
        self.assertEqual([s['source'] for s in state['sources']], ['C', 'B', 'A'])


class NeutWindowTests(unittest.TestCase):
    setUp = harness.PilotWindowTests.setUp

    def read_sample(self):
        self.win._go()
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(LINES) + '\n')
        self.win._read_logs_once()
        self.win._update_combat_meters()

    def test_log_to_panel_and_repeated_poll_does_not_duplicate(self):
        self.read_sample()
        self.win._read_logs_once()
        self.assertEqual(self.win.data.cap_drain.total, 1126)
        self.assertEqual(self.win.data.cap_drain.hits, 20)
        self.assertEqual(self.win._neut_total_label.cget('text'), 'SESSION 1,126 GJ')
        self.assertEqual(self.win._neut_rows[0][0].cget('text'), '1. Pilot Alpha')
        self.assertEqual(self.win._neut_rows[0][1].cget('text'), '846 GJ')
        self.assertIn('Small Energy Neutralizer II', self.win._neut_tooltip(0))
        self.assertEqual(self.win.data.dr, 0)
        self.assertEqual(self.win.data.dd, 0)

    def test_stop_freezes_and_reset_clears_neuts(self):
        self.read_sample()
        before = self.win._neut_rate_label.cget('text')
        self.win._stop()
        self.clock.return_value = 1000
        self.win._update_combat_meters()
        self.assertEqual(self.win._neut_rate_label.cget('text'), before)
        self.win._reset()
        self.win._update_combat_meters()
        self.assertEqual(self.win._neut_total_label.cget('text'), 'SESSION 0 GJ')
        self.assertEqual(self.win._neut_rate_label.cget('text'), '0.0 GJ/s')
        self.assertEqual(self.win._neut_rows[0][0].cget('text'), 'No incoming cap drain')

    def test_pause_expires_rate_but_preserves_total(self):
        self.read_sample()
        self.win._pause()
        self.clock.return_value = 1000
        self.win._update_combat_meters()
        self.assertEqual(self.win._neut_rate_label.cget('text'), '0.0 GJ/s')
        self.assertEqual(self.win._neut_total_label.cget('text'), 'SESSION 1,126 GJ')

    def test_neut_only_session_is_saved(self):
        self.read_sample()
        with patch.object(ratting, 'load_history', return_value=[]), patch.object(ratting, 'save_history') as save:
            ratting.save_session(self.win.data, 'Test Pilot', 7.5)
        entry = save.call_args.args[0][0]
        self.assertEqual(entry['neut_received_gj'], 1126)
        self.assertEqual(entry['neut_hits'], 20)
        self.assertEqual(sum(entry['neut_sources_gj'].values()), 1126)

    def test_quitting_saves_neut_only_session_to_history(self):
        self.read_sample()
        self.doCleanups()
        history = json.loads((self.folder / 'HISTORY_FILE.json').read_text(encoding='utf-8'))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['neut_received_gj'], 1126)

    def test_initial_play_does_not_import_old_neuts(self):
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(LINES) + '\n')
        self.win._go()
        self.win._read_logs_once()
        self.assertEqual(self.win.data.cap_drain.total, 0)

    def test_panel_order_and_long_names_fit(self):
        source = 'An extremely long neutralizer pilot name with spaces and punctuation'
        self.win.data.cap_drain.add(CapDrainEvent(1234.5, source, 'Small Energy Neutralizer II'))
        self.win._update_combat_meters()
        self.root.update()
        self.assertLess(self.win._incoming_container.winfo_y(), self.win._neut_container.winfo_y())
        self.assertLess(self.win._neut_container.winfo_y(), self.win._ctrl_frame.winfo_y())
        label = self.win._neut_rows[0][0]
        self.assertIn('…', label.cget('text'))
        self.assertLessEqual(self.win._neut_font.measure(label.cget('text')), label.winfo_width())
        self.assertIn(source, self.win._neut_tooltip(0))


class NosTests(unittest.TestCase):
    setUp = NeutTests.setUp

    def test_full_mixed_log_totals_ranking_and_timed_rate(self):
        first = datetime.strptime(CAP_LINES[0][2:21], '%Y.%m.%d %H:%M:%S')
        parsed = []
        for line in CAP_LINES:
            timestamp = datetime.strptime(line[2:21], '%Y.%m.%d %H:%M:%S')
            self.now.return_value = 100 + (timestamp - first).total_seconds()
            event = parse_incoming_cap_drain(line)
            self.assertIsNotNone(event)
            parsed.append(event)
            self.meter.add(event)
        state = self.meter.snapshot()
        self.assertEqual(len(parsed), 130)
        self.assertEqual(sum(e.kind == 'nos' for e in parsed), 86)
        self.assertEqual(state['total_gj'], 3948)
        self.assertEqual(state['neut_gj'], 2307)
        self.assertEqual(state['nos_gj'], 1641)
        self.assertEqual(state['hits'], 117)
        self.assertEqual(self.meter.hits_by_kind, {'neut': 42, 'nos': 75})
        self.assertAlmostEqual(state['gj_per_second'], 32 / 15)
        self.assertEqual([(source_label(s['source']), s['total_gj']) for s in state['sources']],
                         [('Pilot Gamma', 2446), ('Pilot Alpha', 940), ('Pilot Beta', 562)])
        self.assertEqual(state['sources'][0]['neut_gj'], 805)
        self.assertEqual(state['sources'][0]['nos_gj'], 1641)
        self.assertTrue(all(harness.parse_damage(line) is None for line in NOS_LINES))

    def test_nos_gains_and_wrong_sign_or_direction_are_excluded(self):
        for line in (NOS_LINES[0].replace('-15 GJ', '15 GJ'),
                     NOS_LINES[0].replace('drained to', 'drained from'),
                     NOS_LINES[0].replace('-15 GJ', '15 GJ').replace('drained to', 'drained from'),
                     NOS_LINES[0].replace('0xffe57f7f', '0xff7fffff')):
            self.assertIsNone(parse_incoming_cap_drain(line))

    def test_negative_neut_or_directionless_nos_is_excluded(self):
        self.assertIsNone(parse_incoming_cap_drain(LINES[0].replace('47 GJ', '-47 GJ')))
        self.assertIsNone(parse_incoming_cap_drain('(combat) -15 GJ energy drained to Pilot - Nosferatu'))

    def test_identical_same_second_records_count_as_separate_activations(self):
        repeated = [line for line in NOS_LINES if '02:56:24' in line]
        self.assertEqual(len(repeated), 2)
        self.assertEqual(repeated[0], repeated[1])
        for line in repeated:
            self.meter.add(parse_incoming_cap_drain(line))
        self.assertEqual(self.meter.total, 108)
        self.assertEqual(self.meter.hits, 2)

    def test_negative_zero_nos_does_not_create_loss(self):
        event = parse_incoming_cap_drain(next(line for line in NOS_LINES if '-0 GJ' in line))
        self.assertEqual(event.kind, 'nos')
        self.assertEqual(event.amount, 0)
        self.meter.add(event)
        self.assertEqual(self.meter.snapshot()['total_gj'], 0)
        self.assertEqual(self.meter.hits, 0)
        self.assertEqual(self.meter.snapshot()['sources'], [])

    def test_negative_decimal_nos_is_a_positive_loss(self):
        event = parse_incoming_cap_drain(NOS_LINES[0].replace('-15 GJ', '-1,234.5 GJ'))
        self.assertEqual(event.amount, 1234.5)
        self.assertEqual(event.kind, 'nos')
        self.assertEqual(event.module, 'Small Energy Nosferatu II')

    def test_same_source_combines_neut_and_nos_for_ranking(self):
        self.meter.add(CapDrainEvent(100, 'A', 'Neutralizer'))
        self.meter.add(CapDrainEvent(200, 'A', 'Nosferatu', 'nos'))
        self.meter.add(CapDrainEvent(250, 'B', 'Neutralizer'))
        top = self.meter.snapshot()['sources'][0]
        self.assertEqual((top['source'], top['total_gj'], top['neut_gj'], top['nos_gj']), ('A', 300, 100, 200))
        self.now.return_value = 115
        expired = self.meter.snapshot()
        self.assertEqual(expired['gj_per_second'], 0)
        self.assertEqual((expired['neut_gj'], expired['nos_gj']), (350, 200))


class NosWindowTests(unittest.TestCase):
    setUp = harness.PilotWindowTests.setUp

    def append_lines(self, lines):
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(lines) + '\n')
        self.win._read_logs_once()
        self.win._update_combat_meters()

    def test_full_mixed_log_displays_combined_total_and_separate_subtotals(self):
        self.win._go()
        self.append_lines(CAP_LINES)
        self.win._read_logs_once()
        self.assertEqual(self.win._neut_total_label.cget('text'), 'SESSION 3,948 GJ')
        self.assertEqual(self.win._cap_breakdown_label.cget('text'), 'NEUT 2,307 GJ  |  NOS 1,641 GJ')
        self.assertEqual(self.win._neut_rows[0][0].cget('text'), '1. Pilot Gamma')
        self.assertEqual(self.win._neut_rows[0][1].cget('text'), '2,446 GJ')
        self.assertIn('NEUT 805 GJ / NOS 1,641 GJ', self.win._neut_tooltip(0))
        self.assertEqual(self.win.data.cap_drain.hits, 117)
        self.assertEqual((self.win.data.dr, self.win.data.dd), (0, 0))

    def test_stop_freezes_and_reset_clears_both_kinds(self):
        self.win._go()
        self.append_lines(CAP_LINES)
        before = self.win._neut_rate_label.cget('text')
        self.win._stop()
        self.clock.return_value = 1000
        self.win._update_combat_meters()
        self.assertEqual(self.win._neut_rate_label.cget('text'), before)
        self.assertEqual(self.win._neut_display['nos_gj'], 1641)
        self.win._reset()
        self.win._update_combat_meters()
        self.assertEqual(self.win._cap_breakdown_label.cget('text'), 'NEUT 0 GJ  |  NOS 0 GJ')
        self.assertEqual(self.win._neut_total_label.cget('text'), 'SESSION 0 GJ')

    def test_nos_only_quit_saves_history_and_retains_old_neut_meaning(self):
        old = {'character': 'Old pilot', 'neut_received_gj': 55, 'neut_hits': 1}
        history_path = self.folder / 'HISTORY_FILE.json'
        history_path.write_text(json.dumps([old]), encoding='utf-8')
        self.win._go()
        self.append_lines(NOS_LINES)
        self.doCleanups()
        history = json.loads(history_path.read_text(encoding='utf-8'))
        self.assertEqual(history[0], old)
        row = history[1]
        self.assertEqual(row['cap_drain_received_gj'], 1641)
        self.assertEqual(row['nos_received_gj'], 1641)
        self.assertEqual(row['neut_received_gj'], 0)
        self.assertEqual(row['nos_hits'], 75)
        self.assertEqual(row['neut_hits'], 0)
        self.assertEqual(sum(row['nos_sources_gj'].values()), 1641)
        self.assertEqual(row['neut_sources_gj'], {})

    def test_initial_play_does_not_import_old_nos(self):
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(NOS_LINES) + '\n')
        self.win._go()
        self.win._read_logs_once()
        self.assertEqual(self.win.data.cap_drain.total, 0)

    def test_pause_skips_paused_nos_then_tracks_new_entries_on_resume(self):
        self.win._go()
        self.append_lines([NOS_LINES[0]])
        self.win._pause()
        self.clock.return_value = 1000
        self.append_lines([NOS_LINES[1]])
        self.assertEqual(self.win.data.cap_drain.total, 15)
        self.assertEqual(self.win._neut_rate_label.cget('text'), '0.0 GJ/s')
        self.win._pause()
        self.win._read_logs_once()
        self.win._update_combat_meters()
        self.assertEqual(self.win.data.cap_drain.total, 15)
        self.append_lines([NOS_LINES[1]])
        self.assertEqual(self.win.data.cap_drain.total, 30)
        self.assertEqual(self.win._neut_display['nos_gj'], 30)
        self.assertEqual(self.win._neut_display['neut_gj'], 0)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + harness.test_args, verbosity=2)
