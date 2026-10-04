"""Event-time battle boundaries, durable payloads and independent real Tk views."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_panels as harness
from battle_history import BattleStore, BattleTracker, battle_title
from neut_meter import CapDrainEvent

ratting = harness.ratting
START = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def at(second):
    return START + timedelta(seconds=second)


def log(second, text):
    return f"[ {at(second):%Y.%m.%d %H:%M:%S} ] (combat) {text}"


class BattleTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1]/'build/test-data'
        base.mkdir(parents=True, exist_ok=True)
        folder = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.store = BattleStore(self.folder/'battles')
        self.now = 100
        self.tracker = BattleTracker(self.store, '123', 'Pilot A', clock=lambda: self.now)

    def hit(self, second, amount=150, name='Pirate', direction='from'):
        self.tracker.damage(at(second), direction, amount, name)

    def finish(self):
        self.tracker.finish('idle')
        return next(iter(self.store.records.values()))

    def test_damage_either_direction_starts_but_zero_and_cap_do_not(self):
        self.tracker.cap_drain(at(0), CapDrainEvent(100, 'Neuter', 'Neut'))
        for amount in (0, -1, float('nan'), float('inf')):
            self.hit(0, amount)
        self.assertIsNone(self.tracker.active)
        self.hit(0, direction='to')
        self.assertEqual(self.tracker.snapshot()['outgoing']['total'], 150)
        self.hit(1)
        self.assertEqual(self.tracker.snapshot()['incoming']['total'], 150)

    def test_exact_60_second_idle_closes_once_without_more_log_lines(self):
        self.hit(0)
        self.now = 159.999
        self.tracker.poll()
        self.assertFalse(self.store.records)
        self.now = 160
        self.tracker.poll()
        self.tracker.poll()
        self.assertEqual(len(self.store.records), 1)
        record = next(iter(self.store.records.values()))
        self.assertTrue(record['complete'])
        self.assertEqual(record['started_at'], record['ended_at'])
        self.assertIsNone(self.tracker.active)

    def test_log_gap_splits_battles_even_when_read_in_one_batch(self):
        self.hit(0)
        self.hit(59)
        self.assertFalse(self.store.records)
        self.hit(119)
        self.assertEqual(len(self.store.records), 1)
        self.assertEqual(next(iter(self.store.records.values()))['incoming']['total'], 300)
        self.assertEqual(self.tracker.snapshot()['incoming']['total'], 150)

    def test_damage_refreshes_idle_deadline(self):
        self.hit(0)
        self.now = 150
        self.hit(50, direction='to')
        self.now = 209.999
        self.tracker.poll()
        self.assertTrue(self.tracker.active)
        self.now = 210
        self.tracker.poll()
        self.assertEqual(len(self.store.records), 1)

    def test_peak_uses_log_time_and_exact_15_second_window(self):
        self.hit(0, 1500)
        self.hit(14, 1500)
        self.hit(15, 750)
        self.hit(30, 3000)
        record = self.finish()
        self.assertEqual(record['incoming']['total'], 6750)
        self.assertEqual(record['incoming']['peak_rate'], 200)
        self.assertEqual(record['incoming']['peak_at'], at(14).isoformat())
        self.assertEqual(record['incoming']['sources'][0]['peak_rate'], 200)

    def test_independent_source_peaks_do_not_falsely_sum(self):
        self.hit(0, 1500, 'A')
        self.hit(20, 3000, 'B')
        self.hit(21, 1500, 'C')
        self.hit(22, 6000, 'Target', 'to')
        record = self.finish()
        self.assertEqual([r['name'] for r in record['incoming']['sources']], ['B', 'A', 'C'])
        self.assertEqual(record['incoming']['peak_rate'], 300)
        self.assertEqual(sum(r['peak_rate'] for r in record['incoming']['sources']), 400)
        self.assertEqual(record['outgoing']['peak_rate'], 400)

    def test_outgoing_single_target_and_all_target_peaks_are_separate(self):
        self.hit(0, 1500, 'A', 'to')
        self.hit(1, 3000, 'B', 'to')
        self.hit(2, 1500, 'A', 'to')
        record = self.finish()['outgoing']
        self.assertEqual(record['peak_rate'], 400)
        self.assertEqual(record['sources'][0]['peak_rate'], 200)
        self.assertEqual(record['total'], 6000)

    def test_neut_and_nos_split_and_combined_peak_without_extending_fight(self):
        self.hit(0)
        self.tracker.cap_drain(at(1), CapDrainEvent(150, 'A', 'Neut', 'neut'))
        self.tracker.cap_drain(at(2), CapDrainEvent(75, 'A', 'Nos', 'nos'))
        self.now = 159
        self.tracker.cap_drain(at(59), CapDrainEvent(15, 'B', 'Neut', 'neut'))
        self.now = 160
        self.tracker.poll()
        record = next(iter(self.store.records.values()))
        cap = record['cap_drain']
        self.assertEqual((cap['total'], cap['neut_gj'], cap['nos_gj']), (240, 165, 75))
        self.assertEqual((cap['peak_rate'], cap['peak_neut_rate'], cap['peak_nos_rate']), (15, 10, 5))
        self.assertEqual((cap['sources'][0]['neut_gj'], cap['sources'][0]['nos_gj']), (150, 75))
        self.assertEqual(record['last_damage_at'], at(0).isoformat())
        self.assertEqual(record['ended_at'], at(59).isoformat())

    def test_cap_at_idle_boundary_closes_but_is_not_counted(self):
        self.hit(0)
        self.tracker.cap_drain(at(60), CapDrainEvent(150, 'A', 'Neut'))
        self.assertIsNone(self.tracker.active)
        self.assertEqual(next(iter(self.store.records.values()))['cap_drain']['total'], 0)

    def test_same_second_hits_count_and_recent_memory_is_bounded_by_window(self):
        for second in range(100):
            for _ in range(50):
                self.hit(second, 1)
        group = self.tracker.active['incoming']
        self.assertLessEqual(len(group.rolling.buckets), 15)
        record = self.finish()
        self.assertEqual(record['incoming']['total'], 5000)
        self.assertEqual(record['incoming']['peak_rate'], 50)

    def test_reversed_log_records_do_not_corrupt_event_time_windows(self):
        self.hit(10)
        self.hit(9, 9999)
        self.tracker.cap_drain(at(8), CapDrainEvent(9999, 'A', 'Neut'))
        record = self.finish()
        self.assertEqual(record['incoming']['total'], 150)
        self.assertEqual(record['cap_drain']['total'], 0)

    def test_partial_close_and_midnight_utc_titles(self):
        start = datetime(2026, 10, 3, 23, 59, 50, tzinfo=timezone.utc)
        self.tracker.damage(start, 'to', 150, 'A')
        self.tracker.damage(start+timedelta(seconds=20), 'from', 150, 'B')
        self.tracker.finish('paused')
        record = next(iter(self.store.records.values()))
        self.assertFalse(record['complete'])
        self.assertEqual(battle_title(record), '2026-10-03 23:59:50–10-04 00:00:10 EVE [partial]')

    def test_reopen_persistence_and_character_isolation(self):
        self.hit(0)
        record = self.finish()
        other = BattleTracker(self.store, '456', 'Pilot B')
        other.damage(at(1), 'from', 300, 'Other')
        other.finish('idle')
        reopened = BattleStore(self.store.folder)
        self.assertEqual(reopened.for_character('123'), [record])
        self.assertEqual(reopened.for_character('456')[0]['incoming']['total'], 300)
        self.assertFalse(list(self.store.folder.glob('*.tmp')))

    def test_bad_or_incomplete_payloads_are_preserved_but_not_loaded(self):
        self.hit(0)
        record = self.finish()
        bad = deepcopy(record)
        del bad['incoming']['sources'][0]['peak_at']
        path = self.store.folder/(record['id']+'.json')
        path.write_text(json.dumps(bad), encoding='utf-8')
        with self.assertLogs(level='ERROR'):
            reopened = BattleStore(self.store.folder)
        self.assertFalse(reopened.records)
        self.assertEqual(reopened.unreadable, 1)
        self.assertEqual(json.loads(path.read_text()), bad)
        with self.assertRaises(ValueError):
            self.store.save(bad)

    def test_atomic_failure_keeps_payload_for_retry(self):
        self.hit(0)
        with patch('battle_history.os.replace', side_effect=OSError('test disk full')), self.assertLogs(level='ERROR'):
            self.tracker.finish('idle')
        self.assertFalse(self.store.records)
        self.assertEqual(len(self.tracker.pending), 1)
        self.assertIn('test disk full', self.tracker.error)
        self.assertFalse(list(self.store.folder.iterdir()))
        self.now += 4
        self.tracker.poll()
        self.assertFalse(self.store.records)
        self.now += 1
        self.tracker.poll()
        self.assertEqual(len(self.store.records), 1)
        self.assertFalse(self.tracker.pending)
        self.assertFalse(self.tracker.error)

    def test_purge_preserves_active_fight_and_unrelated_files(self):
        self.hit(0)
        self.finish()
        self.hit(100)
        (self.store.folder/'readme.json').write_text('keep')
        (self.folder/'ratting_config.json').write_text('keep settings')
        (self.folder/'ratting_history.json').write_text('keep income')
        (self.store.folder/('f'*32+'.json')).write_text('corrupt')
        self.assertEqual(self.store.purge(), 2)
        self.assertFalse(self.store.records)
        self.assertTrue(self.tracker.active)
        self.assertEqual((self.store.folder/'readme.json').read_text(), 'keep')
        self.assertEqual((self.folder/'ratting_history.json').read_text(), 'keep income')
        self.assertEqual((self.folder/'ratting_config.json').read_text(), 'keep settings')


class BattleUITests(unittest.TestCase):
    def setUp(self):
        self.case = harness.FleetPanelTests()
        self.addCleanup(self.case.doCleanups)
        self.ui = self.case.open_fleet()
        self.win = self.ui._windows['123']
        self.win._go()

    def saved_fight(self):
        for second, text in ((0, '1500 to Target A - Gun - Hits'),
                             (1, '3000 to Target A - Gun - Hits'),
                             (2, '1500 from Attacker A - Gun - Hits'),
                             (3, '3000 from Attacker B - Gun - Hits'),
                             (4, '<color=0xffe57f7f>150 GJ energy neutralized Neuter - Neut'),
                             (5, '<color=0xffe57f7f>-75 GJ energy drained to Neuter - Nos')):
            self.win._parse(log(second, text))
        self.win.battles.finish('idle')
        self.win._update_combat_meters()
        return next(iter(self.win._battle_choices))

    def choose(self, variable, choice):
        variable.set(choice)
        self.win._battle_selection_changed()
        self.ui.root.update_idletasks()

    def test_independent_selectors_cap_summary_and_live_fleet_recording(self):
        choice = self.saved_fight()
        self.win.data.combat = ratting.CombatMeter()
        self.win._parse(log(100, '750 to Current target - Gun - Hits'))
        self.win._parse(log(101, '150 from Current attacker - Gun - Hits'))
        self.choose(self.win._out_battle_var, choice)
        self.assertEqual(self.win._target_dps_label.cget('text'), '300 DPS')
        self.assertEqual(self.win._meter_status.cget('text'), 'SAVED')
        self.assertEqual(self.win._combat_display['attackers'][0][0], 'Current attacker')
        self.choose(self.win._in_battle_var, choice)
        self.assertEqual(self.win._combat_display['attackers'][0], ('Attacker B', 3000, 200))
        self.assertEqual(self.win._neut_rate_label.cget('text'), '15.0 GJ/s')
        self.assertEqual(self.win._neut_total_label.cget('text'), 'BATTLE 225 GJ')
        self.assertEqual(self.win._cap_breakdown_label.cget('text'), 'NEUT 150 GJ  |  NOS 75 GJ')
        self.assertIn('12:00:00–12:00:05 EVE', self.win._battle_detail.cget('text'))
        self.win._parse(log(102, '750 to Current target - Gun - Hits'))
        self.ui.root.after_cancel(self.ui._health_job)
        self.ui._health_check()
        self.assertEqual(self.ui._tree.set('123', 'target_dps'), '100')
        self.assertEqual(self.win.battles.snapshot()['outgoing']['total'], 1500)
        self.choose(self.win._out_battle_var, 'Current')
        self.assertEqual(self.win._target_dps_label.cget('text'), '100 DPS')
        self.assertEqual(self.win._in_battle_var.get(), choice)
        self.choose(self.win._in_battle_var, 'Current')
        self.assertEqual(self.win._combat_display['attackers'][0][0], 'Current attacker')
        self.assertTrue(self.win._neut_total_label.cget('text').startswith('SESSION'))

    def test_log_reader_does_not_count_a_record_twice(self):
        path = self.case.folder/'20260922_120000_123.txt'
        with path.open('a', encoding='utf-8') as stream:
            stream.write(log(0, '1500 from Attacker - Gun - Hits')+'\n')
        self.win._read_logs_once()
        self.win._read_logs_once()
        self.assertEqual(self.win.battles.snapshot()['incoming']['total'], 1500)

    def test_purge_confirmation_keeps_active_battle_and_cancel_preserves_selection(self):
        choice = self.saved_fight()
        self.choose(self.win._in_battle_var, choice)
        self.win._parse(log(100, '1500 to Current target - Gun - Hits'))
        settings = ratting.MainUISettings(self.ui.root, self.ui)
        with patch.object(ratting.messagebox, 'askyesno', return_value=False):
            settings._purge_battles_button.invoke()
        self.assertEqual(self.win._in_battle_var.get(), choice)
        self.assertEqual(len(self.ui._battle_store.records), 1)
        with patch.object(ratting.messagebox, 'askyesno', return_value=True):
            settings._purge_battles_button.invoke()
        self.assertFalse(self.ui._battle_store.records)
        self.assertTrue(self.win.battles.active)
        self.assertEqual(self.win._in_battle_var.get(), 'Current')
        self.assertEqual(self.win._out_battle_box.cget('values'), ('Current',))
        self.assertIn('0 saved battles', settings._battle_count.cget('text'))

    def test_pause_stop_reset_and_hide_close_partial_records(self):
        for index, (action, reason) in enumerate(((self.win._pause, 'paused'),
                                                (self.win._stop, 'stopped'),
                                                (self.win._reset, 'reset'))):
            self.win._go()
            self.win._parse(log(index*100, '1500 from Attacker - Gun - Hits'))
            action()
            latest = self.ui._battle_store.for_character('123')[0]
            self.assertEqual(latest['close_reason'], reason)
            self.assertFalse(latest['complete'])
            self.assertIsNone(self.win.battles.active)
        self.win._go()
        self.win._parse(log(400, '1500 from Attacker - Gun - Hits'))
        self.ui.cfg['bg_monitor'] = False
        self.ui._toggle_window('123')
        self.assertEqual(self.ui._battle_store.for_character('123')[0]['close_reason'], 'monitoring_paused')

    def test_cap_only_misses_and_ewar_do_not_start_a_battle(self):
        with patch.object(ratting._ALERT_AUDIO, 'notify'), patch.object(self.win, '_flash_alert'):
            for text in ('Your Ogre II misses Pirate completely',
                         'Warp scramble attempt from Pirate to you!',
                         '<color=0xffe57f7f>150 GJ energy neutralized Neuter - Neut',
                         '0 from Attacker - Gun - Hits'):
                self.win._parse(log(0, text))
        self.assertIsNone(self.win.battles.active)
        self.assertEqual(self.win.data.cap_drain.snapshot()['total_gj'], 150)

    def test_idle_tick_drains_pending_damage_before_closing(self):
        self.win._parse(log(0, '1500 from Attacker - Gun - Hits'))
        self.win.battles.last_arrival -= 61
        with (self.case.folder/'20260922_120000_123.txt').open('a', encoding='utf-8') as stream:
            stream.write(log(50, '1500 from Attacker - Gun - Hits')+'\n')
        self.win.root.after_cancel(self.win._tick_job)
        self.win._tick()
        self.assertFalse(self.ui._battle_store.records)
        self.assertEqual(self.win.battles.snapshot()['incoming']['total'], 3000)
        self.win.battles.last_arrival -= 61
        self.win.root.after_cancel(self.win._tick_job)
        self.win._tick()
        self.assertEqual(len(self.ui._battle_store.records), 1)

    def test_empty_direction_and_controls_remain_visible_with_saved_view(self):
        self.win._parse(log(0, '1500 from Attacker - Gun - Hits'))
        self.win.battles.finish('idle')
        self.win._refresh_battle_choices()
        choice = next(iter(self.win._battle_choices))
        self.choose(self.win._out_battle_var, choice)
        self.choose(self.win._in_battle_var, choice)
        self.assertEqual(self.win._target_dps_label.cget('text'), '0 DPS')
        self.assertEqual(self.win._target_name_label.cget('text'), 'No outgoing damage')
        self.assertIn('n/a', self.win._target_peak_tooltip())
        self.assertEqual(self.win._neut_rate_label.cget('text'), '0.0 GJ/s')
        self.assertGreater(self.win.root.winfo_height(), self.win._body.winfo_reqheight())
        settings = ratting.MainUISettings(self.ui.root, self.ui)
        self.ui.root.update()
        for control in (settings._purge_battles_button, settings._ap):
            self.assertTrue(control.winfo_viewable())
            self.assertLessEqual(control.winfo_rooty()+control.winfo_height(), settings.w.winfo_rooty()+settings.w.winfo_height())

    def test_new_window_loads_own_history_and_defaults_to_current(self):
        choice = self.saved_fight()
        self.choose(self.win._out_battle_var, choice)
        self.ui._windows['456']._refresh_battle_choices()
        self.assertEqual(self.ui._windows['456']._out_battle_box.cget('values'), ('Current',))
        self.win._quit()
        self.ui._windows.pop('123')
        win = ratting.CharacterWindow(self.ui.root, self.ui, '123', 'Test Pilot A',
                                     str(self.case.folder/'20260922_120000_123.txt'), self.ui.cfg)
        self.ui._windows['123'] = self.win = win
        self.assertEqual(win._out_battle_var.get(), 'Current')
        self.assertEqual(win._in_battle_var.get(), 'Current')
        self.assertEqual(len(win._out_battle_box.cget('values')), 2)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + harness.test_args, verbosity=2)
