"""Incoming-only English EWAR events and serialized, offline alert playback."""
from collections import deque
from html import unescape
from pathlib import Path
import logging
import re
import threading
import time

try:
    import winsound
except ImportError:
    winsound = None

LABELS = {"SCRAM": "SCRAMBLED", "POINT": "POINTED", "WEB": "WEBBED"}
FILES = {"SCRAM": "scrambled.wav", "POINT": "pointed.wav", "WEB": "webbed.wav"}
_TACKLE = re.compile(r"\(combat\)\s+Warp (scramble|disruption) attempt from (.+?) to you[!.]?\s*$", re.I)
_WEB = re.compile(r"\(notify\)\s+(.+?) has started webifying you[!.]?\s*$", re.I)


def parse_incoming_ewar(raw):
    """Require the recipient to be 'you', excluding outgoing and nearby tackle."""
    plain = " ".join(unescape(re.sub(r"<[^>]+>", "", raw)).split())
    match = _TACKLE.search(plain)
    if match:
        source = match[2].strip()
        if source.casefold() != "you":
            return ("SCRAM" if match[1].lower() == "scramble" else "POINT", source)
    match = _WEB.search(plain)
    if match and match[1].strip().casefold() != "you":
        return "WEB", match[1].strip()
    return None


class AlertAudio:
    """One player for the fleet; coalesce each type for 10 seconds, never overlap.

    Different effects remain separate queued clips. Old queued events expire so
    a busy fleet cannot leave a backlog of obsolete warnings. No Tk calls here.
    """
    def __init__(self, assets, player=None, clock=time.monotonic):
        self.assets = Path(assets)
        self.player = player or self._play
        self.clock = clock
        self.pending = deque(maxlen=3)
        self.last = {}
        self.lock = threading.Lock()
        self.worker = None

    def notify(self, kind, mode="Voice", preview=False):
        if kind not in FILES or mode not in ("Voice", "Beep"):
            return False
        with self.lock:
            now = self.clock()
            if not preview and now - self.last.get(kind, -float("inf")) < 10:
                return False
            if any(item[1] == kind for item in self.pending):
                return False
            if not preview:
                self.last[kind] = now
            self.pending.append((now, kind, mode))
            if self.worker is None:
                self.worker = threading.Thread(target=self._drain, daemon=True)
                self.worker.start()
        return True

    def clear(self):
        with self.lock:
            self.pending.clear()
            self.last.clear()

    def _drain(self):
        while True:
            with self.lock:
                if not self.pending:
                    self.worker = None
                    return
                at, kind, mode = self.pending.popleft()
            if self.clock() - at > 8:
                continue
            try:
                self.player(kind, mode)
            except Exception:
                logging.exception("Could not play EWAR alert")

    def _play(self, kind, mode):
        if winsound is None:
            return
        path = self.assets / FILES[kind]
        if mode == "Voice" and path.is_file():
            try:
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                return
            except RuntimeError:
                logging.exception("Voice clip unavailable; falling back to beep")
        winsound.Beep(1200, 130)
        winsound.Beep(1650, 160)
