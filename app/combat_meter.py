"""Named combat damage from EVE's English gamelog, with bounded rolling totals."""
from collections import deque
from html import unescape
import re
import time

_TAGS = re.compile(r"<[^>]+>")
_DAMAGE = re.compile(
    r"\(combat\)\s*(\d{1,3}(?:,\d{3})+|\d+)\s+(to|from)\s+(.+?)\s+[-\u2013\u2014]\s+.+$",
    re.IGNORECASE,
)


def parse_damage(line):
    """Return (direction, amount, name) for plain or HTML-tagged damage lines."""
    plain = unescape(_TAGS.sub("", line)).strip()
    match = _DAMAGE.search(plain)
    if match is None:
        return None
    amount, direction, name = match.groups()
    return direction.lower(), int(amount.replace(",", "")), " ".join(name.split())


class CombatMeter:
    """Use arrival time, like the existing DPS meter; never infer selected locks.

    The target is the latest name receiving a logged hit. Identical logged names
    share a bucket because these combat records do not supply a unique NPC ID.
    """

    def __init__(self, window=15, max_events=10000):
        self.window = window
        self.events = deque(maxlen=max_events)
        self.outgoing = {}
        self.incoming = {}
        self.last_target = None
        self.last_target_at = 0.0

    def _remove_oldest(self):
        _, direction, name, amount = self.events.popleft()
        totals = self.outgoing if direction == "to" else self.incoming
        remaining = totals[name] - amount
        if remaining > 0:
            totals[name] = remaining
        else:
            del totals[name]

    def _expire(self, now):
        while self.events and self.events[0][0] <= now - self.window:
            self._remove_oldest()

    def add(self, direction, amount, name):
        now = time.monotonic()
        self._expire(now)
        name = " ".join(name.split()) or "Unknown"
        if direction == "to":
            self.last_target = name
            self.last_target_at = now
        if amount <= 0:
            return
        if len(self.events) == self.events.maxlen:
            self._remove_oldest()
        self.events.append((now, direction, name, amount))
        totals = self.outgoing if direction == "to" else self.incoming
        totals[name] = totals.get(name, 0) + amount

    def snapshot(self):
        now = time.monotonic()
        self._expire(now)
        target = self.last_target if now - self.last_target_at < self.window else None
        attackers = sorted(self.incoming.items(), key=lambda item: (-item[1], item[0].casefold()))[:3]
        return {
            "target": target,
            "target_dps": self.outgoing.get(target, 0) / self.window,
            "attackers": [(name, damage, damage / self.window) for name, damage in attackers],
        }
