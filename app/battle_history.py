"""Per-pilot battle summaries with event-time peaks and atomic local persistence."""
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

WINDOW = 15
IDLE = 60
_ID = re.compile(r'[0-9a-f]{32}')


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds')


def battle_title(record):
    start = datetime.fromisoformat(record['started_at'])
    end = datetime.fromisoformat(record['ended_at'])
    finish = end.strftime('%H:%M:%S') if start.date() == end.date() else end.strftime('%m-%d %H:%M:%S')
    partial = ' [partial]' if not record['complete'] else ''
    return f"{start:%Y-%m-%d %H:%M:%S}–{finish} EVE{partial}"


def _valid(record):
    try:
        if record['schema_version'] != 1 or not _ID.fullmatch(record['id']):
            return False
        if not isinstance(record['character_id'], str) or not isinstance(record['character_name'], str):
            return False
        if not isinstance(record['complete'], bool):
            return False
        if record['window_seconds'] != WINDOW or record['idle_seconds'] != IDLE:
            return False
        if record['close_reason'] not in ('idle', 'paused', 'stopped', 'reset', 'closed', 'monitoring_paused'):
            return False
        for key in ('started_at', 'ended_at', 'last_damage_at'):
            value = datetime.fromisoformat(record[key])
            if value.utcoffset() is None:
                return False
        if not record['started_at'] <= record['last_damage_at'] <= record['ended_at']:
            return False
        for section in ('outgoing', 'incoming', 'cap_drain'):
            group = record[section]
            for field in ('total', 'peak_rate', 'peak_amount'):
                if not isinstance(group[field], (int, float)) or not math.isfinite(group[field]) or group[field] < 0:
                    return False
            if not isinstance(group['sources'], list):
                return False
            if group['peak_at'] is not None and datetime.fromisoformat(group['peak_at']).utcoffset() is None:
                return False
            if group['peak_amount'] > 0 and group['peak_at'] is None:
                return False
            for row in group['sources']:
                if not isinstance(row['name'], str):
                    return False
                if datetime.fromisoformat(row['peak_at']).utcoffset() is None:
                    return False
                for field in ('total', 'peak_rate', 'peak_amount'):
                    if not isinstance(row[field], (int, float)) or not math.isfinite(row[field]) or row[field] < 0:
                        return False
                if section == 'cap_drain':
                    if not isinstance(row['module'], str):
                        return False
                    for field in ('neut_gj', 'nos_gj'):
                        if not math.isfinite(row[field]) or row[field] < 0:
                            return False
        for field in ('neut_gj', 'nos_gj', 'peak_neut_rate', 'peak_nos_rate'):
            if not math.isfinite(record['cap_drain'][field]) or record['cap_drain'][field] < 0:
                return False
        return True
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


class BattleStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.records = {}
        self.generation = 0
        self.unreadable = 0
        for path in self.folder.glob('*.json'):
            if not _ID.fullmatch(path.stem):
                continue
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
                if not _valid(record) or record['id'] != path.stem:
                    raise ValueError('Invalid battle payload')
                self.records[record['id']] = record
            except (OSError, ValueError, TypeError):
                self.unreadable += 1
                logging.exception('Could not load battle %s', path)

    def for_character(self, character_id):
        return sorted((r for r in self.records.values() if r['character_id'] == str(character_id)),
                      key=lambda r: (r['started_at'], r['id']), reverse=True)

    def save(self, record):
        if not _valid(record):
            raise ValueError('Invalid battle payload')
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.folder,
                                             suffix='.tmp', delete=False) as stream:
                tmp = Path(stream.name)
                json.dump(record, stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.folder/(record['id']+'.json'))
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
        self.records[record['id']] = deepcopy(record)
        self.generation += 1

    def purge(self):
        """Delete only archived payload filenames; never traverse other data."""
        removed = 0
        try:
            for path in self.folder.glob('*.json'):
                if _ID.fullmatch(path.stem):
                    path.unlink()
                    self.records.pop(path.stem, None)
                    removed += 1
        finally:
            self.generation += 1
        self.unreadable = 0
        return removed


class _Rolling:
    """One bucket per log second rather than one object per damage event."""
    def __init__(self):
        self.buckets = deque()
        self.names = {}
        self.total = 0.0

    def add(self, at, name, amount):
        while self.buckets and self.buckets[0][0] <= at - WINDOW:
            _, bucket = self.buckets.popleft()
            for key, value in bucket.items():
                self.names[key] -= value
                self.total -= value
                if abs(self.names[key]) < 1e-8:
                    del self.names[key]
        if not self.buckets or self.buckets[-1][0] != at:
            self.buckets.append((at, {}))
        bucket = self.buckets[-1][1]
        bucket[name] = bucket.get(name, 0) + amount
        self.names[name] = self.names.get(name, 0) + amount
        self.total += amount


class _Group:
    def __init__(self):
        self.rolling = _Rolling()
        self.total = 0.0
        self.peak = 0.0
        self.peak_at = None
        self.sources = {}

    def add(self, at, name, amount):
        self.rolling.add(at, name, amount)
        self.total += amount
        row = self.sources.setdefault(name, {'name': name, 'total': 0.0,
                                             'peak_amount': 0.0, 'peak_rate': 0.0, 'peak_at': None})
        row['total'] += amount
        if self.rolling.names[name] > row['peak_amount']:
            row.update(peak_amount=self.rolling.names[name], peak_rate=self.rolling.names[name]/WINDOW, peak_at=stamp(at))
        if self.rolling.total > self.peak:
            self.peak, self.peak_at = self.rolling.total, stamp(at)
        return row

    def snapshot(self):
        return {'total': self.total, 'peak_amount': self.peak, 'peak_rate': self.peak/WINDOW,
                'peak_at': self.peak_at,
                'sources': sorted(deepcopy(list(self.sources.values())),
                                  key=lambda r: (-r['peak_rate'], r['name'].casefold()))}


class BattleTracker:
    def __init__(self, store, character_id, character_name, clock=None):
        self.store, self.character_id, self.character_name = store, str(character_id), character_name
        self.clock = clock or time.monotonic
        self.active = None
        self.pending = []
        self.error = ''
        self.retry_at = 0
        self.last_arrival = 0

    def damage(self, ts, direction, amount, name):
        if direction not in ('to', 'from') or not math.isfinite(amount) or amount <= 0:
            return
        at = ts.timestamp()
        if self.active and at < self.active['last_event']:
            return  # Do not corrupt event-time windows with reversed log records.
        if self.active and at - self.active['last_damage'] >= IDLE:
            self.finish('idle')
        if self.active is None:
            self.active = {'id': uuid.uuid4().hex, 'start': at, 'last_damage': at, 'last_event': at,
                           'outgoing': _Group(), 'incoming': _Group(), 'cap_drain': _Group(),
                           'neut': _Group(), 'nos': _Group()}
        self.active['last_damage'] = self.active['last_event'] = at
        self.last_arrival = self.clock()
        self.active['outgoing' if direction == 'to' else 'incoming'].add(at, name or 'Unknown', amount)

    def cap_drain(self, ts, event):
        if self.active is None or event.kind not in ('neut', 'nos') or not math.isfinite(event.amount) or event.amount <= 0:
            return
        at = ts.timestamp()
        if at < self.active['last_event']:
            return
        if at - self.active['last_damage'] >= IDLE:
            self.finish('idle')
            return
        self.active['last_event'] = at
        row = self.active['cap_drain'].add(at, event.source, event.amount)
        row.setdefault('neut_gj', 0.0)
        row.setdefault('nos_gj', 0.0)
        row[event.kind+'_gj'] += event.amount
        row['module'] = event.module
        self.active[event.kind].add(at, event.source, event.amount)

    def snapshot(self, reason='active'):
        if self.active is None:
            return None
        a = self.active
        cap = a['cap_drain'].snapshot()
        cap.update(neut_gj=a['neut'].total, nos_gj=a['nos'].total,
                   peak_neut_rate=a['neut'].peak/WINDOW, peak_nos_rate=a['nos'].peak/WINDOW)
        return {'schema_version': 1, 'id': a['id'], 'character_id': self.character_id,
                'character_name': self.character_name, 'started_at': stamp(a['start']),
                'ended_at': stamp(a['last_event']), 'last_damage_at': stamp(a['last_damage']),
                'complete': reason == 'idle', 'close_reason': reason,
                'window_seconds': WINDOW, 'idle_seconds': IDLE,
                'outgoing': a['outgoing'].snapshot(), 'incoming': a['incoming'].snapshot(), 'cap_drain': cap}

    def finish(self, reason):
        if self.active is not None:
            self.pending.append(self.snapshot(reason))
            self.active = None
        self.flush()

    def flush(self):
        while self.pending:
            try:
                self.store.save(self.pending[0])
            except OSError as exc:
                self.error = str(exc)
                self.retry_at = self.clock()+5
                logging.exception('Battle save failed; retaining summary for retry')
                return
            self.pending.pop(0)
        self.error = ''

    def poll(self):
        if self.active and self.clock() - self.last_arrival >= IDLE:
            self.finish('idle')
        elif self.pending and self.clock() >= self.retry_at:
            self.flush()
