"""Incoming neutralizer and Nosferatu losses in EVE's English, colored gamelog."""
from collections import namedtuple
from html import unescape
import math
import re

from combat_meter import CombatMeter

# The text alone has no direction. Require the incoming amount color at the
# start of the combat payload; a color inside a ship/pilot name is not enough.
_INCOMING = re.compile(r'\(combat\)\s*<color\s*=\s*[\"\']?0xffe57f7f[\"\']?\s*>', re.I)
_FORMATTING = re.compile(r'</?(?:color|font|b|i|u|a)(?:\s[^>]*|=[^>]*)?>', re.I)
_CAP_DRAIN = re.compile(
    r'\(combat\)\s*(-?(?:\d{1,3}(?:,\d{3})+|\d+))(\.\d+)?\s+GJ\s+'
    r'energy\s+(neutralized|drained to)\s+(.+)$', re.I)
CapDrainEvent = namedtuple('CapDrainEvent', 'amount source module kind', defaults=['neut'])


def parse_incoming_cap_drain(line):
    """Return a positive loss amount, distinguished as neut or Nosferatu.

    The supplied raw log identifies incoming capacitor loss with 0xffe57f7f.
    Keep that direction marker until after classification, then remove markup.
    Nosferatu loss also requires a negative amount and 'drained to'; capacitor
    gained via 'drained from' and positive/ambiguous records are excluded.
    """
    if not _INCOMING.search(line):
        return None
    plain = ' '.join(unescape(_FORMATTING.sub('', line)).split())
    match = _CAP_DRAIN.search(plain)
    if not match:
        return None
    whole, fraction, action, payload = match.groups()
    kind = 'nos' if action.lower() == 'drained to' else 'neut'
    if whole.startswith('-') != (kind == 'nos'):
        return None
    source, separator, module = (' ' + payload).rpartition(' - ')
    if not separator or not module.strip():
        return None
    source = source.strip().removesuffix(' -').strip()
    amount = abs(float(whole.replace(',', '') + (fraction or '')))
    if not math.isfinite(amount):
        return None
    return CapDrainEvent(amount, source.strip() or 'Unknown source', module.strip(), kind)


def source_label(source):
    """Prefer the final pilot field in decorated ship [alliance] [corp] [pilot] names."""
    match = re.fullmatch(r'[^\[\]]+\s+(?:\[[^\[\]]+\]\s+){1,2}\[([^\[\]]+)\]', source)
    return match.group(1) if match else source


def format_gj(amount):
    return f'{amount:,.1f}'.rstrip('0').rstrip('.')


class CapDrainMeter:
    """Combined session losses and a bounded rate, retaining neut/Nos breakdowns."""
    def __init__(self, window=15, max_events=10000):
        self.recent = CombatMeter(window=window, max_events=max_events)
        self.total = 0.0
        self.totals = {}
        self.modules = {}
        self.hits = 0
        self.by_kind = {'neut': 0.0, 'nos': 0.0}
        self.hits_by_kind = {'neut': 0, 'nos': 0}
        self.totals_by_kind = {'neut': {}, 'nos': {}}

    def add(self, event):
        if event.kind not in self.by_kind or not math.isfinite(event.amount) or event.amount <= 0:
            return
        self.total += event.amount
        self.hits += 1
        self.by_kind[event.kind] += event.amount
        self.hits_by_kind[event.kind] += 1
        kind_totals = self.totals_by_kind[event.kind]
        kind_totals[event.source] = kind_totals.get(event.source, 0) + event.amount
        self.totals[event.source] = self.totals.get(event.source, 0) + event.amount
        self.modules[event.source] = event.module
        self.recent.add('from', event.amount, event.source)

    def snapshot(self):
        self.recent.snapshot()  # Expire recent events; session totals remain.
        top = sorted(self.totals.items(), key=lambda item: (-item[1], item[0].casefold()))[:3]
        return {
            'total_gj': self.total,
            'neut_gj': self.by_kind['neut'],
            'nos_gj': self.by_kind['nos'],
            'hits': self.hits,
            'gj_per_second': sum(self.recent.incoming.values()) / self.recent.window,
            'sources': [
                {'source': source, 'total_gj': amount,
                 'neut_gj': self.totals_by_kind['neut'].get(source, 0),
                 'nos_gj': self.totals_by_kind['nos'].get(source, 0),
                 'gj_per_second': self.recent.incoming.get(source, 0) / self.recent.window,
                 'module': self.modules[source]}
                for source, amount in top
            ],
        }
