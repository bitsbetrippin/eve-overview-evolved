"""Developer-only: generate original synthetic styles with eSpeak NG 1.52.0."""
import argparse
from array import array
import math
from pathlib import Path
import subprocess
import wave

ROOT = Path(__file__).resolve().parent
PROFILES = {
    # Original generic deliveries, with no actor recordings or voice cloning.
    'commanding': ('en-us+m1', 165, 25, 'Warning. You are {word}.'),
    'dramatic': ('en-us+m3', 140, 55, 'You are <break time="180ms"/> {word}.'),
    'news_anchor': ('en-us+klatt', 170, 38, 'Alert. You are {word}.'),
}


def generate(executable):
    executable = executable.resolve()
    for style, (voice, speed, pitch, phrase) in PROFILES.items():
        folder = ROOT / 'assets/voices' / style
        folder.mkdir(parents=True, exist_ok=True)
        for word in ('scrambled', 'pointed', 'webbed'):
            path = folder / (word + '.wav')
            subprocess.run([str(executable), '--path='+str(executable.parent), '-v', voice,
                            '-s', str(speed), '-p', str(pitch), '-m', '-w', str(path),
                            phrase.format(word=word)], check=True)
            with wave.open(str(path), 'rb') as stream:
                params = stream.getparams()
                samples = array('h', stream.readframes(params.nframes))
            # Match the original robot's average level for the same phrase,
            # reserving peak headroom where possible for the volume booster.
            with wave.open(str(ROOT/'assets'/(word+'.wav')), 'rb') as stream:
                reference = array('h', stream.readframes(stream.getnframes()))
            rms = lambda values: math.sqrt(sum(v*v for v in values) / len(values))
            gain = min(rms(reference) / max(1, rms(samples)), 24000 / max(1, max(abs(v) for v in samples)))
            samples = array('h', (round(v*gain) for v in samples))
            with wave.open(str(path), 'wb') as stream:
                stream.setparams(params)
                stream.writeframes(samples.tobytes())
            print(style, word, round(params.nframes/params.framerate, 2), 'seconds')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--espeak', type=Path, required=True)
    generate(parser.parse_args().espeak)
