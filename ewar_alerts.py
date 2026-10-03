"""Recipient-aware English EWAR events and serialized, offline alert playback."""
from collections import deque
from dataclasses import dataclass
from array import array
from functools import lru_cache
from html import unescape
from pathlib import Path
import io
import logging
import math
import re
import sys
import threading
import time
import wave

try:
    import winsound
except ImportError:
    winsound = None

LABELS = {"SCRAM": "SCRAMBLED", "POINT": "POINTED", "WEB": "WEBBED"}
FILES = {"SCRAM": "scrambled.wav", "POINT": "pointed.wav", "WEB": "webbed.wav"}
VOICE_FOLDERS = {"Robot": "", "Commanding": "voices/commanding",
                 "Dramatic": "voices/dramatic", "News anchor": "voices/news_anchor",
                 "SamL": "voices/saml"}
# Packaged for manual preview only; no JAM log trigger until its format is verified.
PREVIEW_CLIPS = {"SamL": {"JAM": "jammed.wav"}}
VOLUME_GAINS = {"Low (100%)": 1.0, "Medium (200%)": 2.0, "High (300%)": 3.0}
DEFAULT_VOICE = "Robot"
DEFAULT_VOLUME = "Low (100%)"
_PREFIX = r"^(?:\[\s*\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}\s*\]\s*)?"
_TACKLE = re.compile(_PREFIX + r"\(combat\)\s+Warp (scramble|disruption) attempt from (.+?) to (.+?)[!.]?\s*$", re.I)
_WEB = re.compile(_PREFIX + r"\(notify\)\s+(.+?) (?:has|have) started webifying (.+?)[!.]?\s*$", re.I)


@dataclass(frozen=True)
class EwarEvent:
    kind: str
    source: str
    target: str

    @property
    def incoming(self):
        return self.target.casefold() == "you"


def voice_files(voice):
    return {**FILES, **PREVIEW_CLIPS.get(voice, {})}


def parse_ewar(raw):
    """Read explicit recipients; only an exact 'you' means the log's pilot."""
    plain = " ".join(unescape(re.sub(r"<[^>]+>", "", raw)).split())
    match = _TACKLE.search(plain)
    if match:
        event = EwarEvent("SCRAM" if match[1].lower() == "scramble" else "POINT",
                          match[2].strip(), match[3].strip())
    else:
        match = _WEB.search(plain)
        if not match:
            return None
        event = EwarEvent("WEB", match[1].strip(), match[2].strip())
    if not event.source or not event.target or event.target in ("!", "."):
        return None
    if event.incoming and event.source.casefold() == "you":
        return None
    return event


def parse_incoming_ewar(raw):
    """Compatibility helper for personal-only consumers."""
    event = parse_ewar(raw)
    return (event.kind, event.source) if event and event.incoming else None


def amplify_wav(data, gain):
    """Boost 16-bit PCM with a soft limiter; 100% preserves the original bytes.

    Digital gain cannot override the Windows mixer or speaker output limit.
    Only peaks near full scale are limited, avoiding wraparound/hard clipping.
    """
    if not math.isfinite(gain) or not 1 <= gain <= 3:
        raise ValueError("Alert gain must be between 1 and 3")
    if gain == 1:
        return data
    with wave.open(io.BytesIO(data), "rb") as source:
        params = source.getparams()
        if params.sampwidth != 2 or params.comptype != "NONE":
            raise ValueError("Alerts require uncompressed 16-bit PCM")
        samples = array("h", source.readframes(params.nframes))
    if sys.byteorder != "little":
        samples.byteswap()
    knee = 0.85 * 32767
    headroom = 32767 - knee
    for i, sample in enumerate(samples):
        value = sample * gain
        peak = abs(value)
        if peak > knee:
            peak = knee + headroom * (1 - math.exp(-(peak - knee) / headroom))
        samples[i] = round(math.copysign(peak, value))
    if sys.byteorder != "little":
        samples.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setparams(params)
        target.writeframes(samples.tobytes())
    return output.getvalue()


@lru_cache(maxsize=64)
def voice_wav(path, gain):
    return amplify_wav(Path(path).read_bytes(), gain)


@lru_cache(maxsize=3)
def beep_wav(gain):
    """PCM replacement for Beep so all alert modes honor the chosen gain."""
    rate = 22050
    samples = array("h")
    for frequency, duration in ((1200, .13), (1650, .16)):
        count = int(rate * duration)
        for i in range(count):
            fade = min(1, i / (rate * .005), (count - 1 - i) / (rate * .005))
            samples.append(round(4000 * fade * math.sin(2 * math.pi * frequency * i / rate)))
    if sys.byteorder != "little":
        samples.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setparams((1, 2, rate, len(samples), "NONE", "not compressed"))
        target.writeframes(samples.tobytes())
    return amplify_wav(output.getvalue(), gain)


class AlertAudio:
    """One player for the fleet; coalesce each type/scope for 10 seconds.

    Different effects remain separate queued clips. Old queued events expire so
    a busy fleet cannot leave a backlog of obsolete warnings. Personal alerts
    play before queued nearby beeps, which never suppress personal alerts.
    No Tk calls here.
    """
    def __init__(self, assets, player=None, clock=time.monotonic):
        self.assets = Path(assets)
        self.player = player or self._play
        self.clock = clock
        self.pending = deque(maxlen=4)
        self.nearby_pending = deque(maxlen=3)
        self.last = {}
        self.lock = threading.Lock()
        self.worker = None

    def notify(self, kind, mode="Voice", preview=False, *, voice=DEFAULT_VOICE,
               volume=DEFAULT_VOLUME, nearby=False):
        voice = voice if voice in VOICE_FOLDERS else DEFAULT_VOICE
        volume = volume if volume in VOLUME_GAINS else DEFAULT_VOLUME
        if mode not in ("Voice", "Beep"):
            return False
        if kind not in FILES and not (preview and not nearby and kind in PREVIEW_CLIPS.get(voice, {})):
            return False
        if nearby:
            mode = "Beep"
        with self.lock:
            now = self.clock()
            key = (nearby, kind)
            pending = self.nearby_pending if nearby else self.pending
            if not preview and now - self.last.get(key, -float("inf")) < 10:
                return False
            if any(item[1] == kind for item in pending):
                return False
            if not preview:
                self.last[key] = now
            pending.append((now, kind, mode, voice, volume, preview))
            if self.worker is None:
                self.worker = threading.Thread(target=self._drain, daemon=True)
                self.worker.start()
        return True

    def clear(self):
        with self.lock:
            self.pending.clear()
            self.nearby_pending.clear()
            self.last.clear()

    def _drain(self):
        while True:
            with self.lock:
                pending = self.pending if self.pending else self.nearby_pending
                if not pending:
                    self.worker = None
                    return
                at, kind, mode, voice, volume, preview = pending.popleft()
            if not preview and self.clock() - at > 8:
                continue
            try:
                self.player(kind, mode, voice, volume)
            except Exception:
                logging.exception("Could not play EWAR alert")

    def _play(self, kind, mode, voice=DEFAULT_VOICE, volume=DEFAULT_VOLUME):
        if winsound is None:
            return
        gain = VOLUME_GAINS.get(volume, 1.0)
        data = None
        if mode == "Voice":
            filename = voice_files(voice)[kind]
            chosen = self.assets / VOICE_FOLDERS.get(voice, "") / filename
            fallback = self.assets / filename
            for path in dict.fromkeys((chosen, fallback)):
                try:
                    data = voice_wav(str(path), gain)
                    break
                except (OSError, ValueError, EOFError, wave.Error):
                    logging.exception("Voice clip unavailable: %s", path)
        if data is None:
            data = beep_wav(gain)
        # Synchronous playback in the worker keeps warnings separate. No mixer
        # settings change, and no files or installed TTS engine are needed.
        winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_NODEFAULT)
