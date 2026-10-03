"""Apply a mild robot texture to the newly synthesized mono PCM voice clips."""
from array import array
import math
from pathlib import Path
import wave

for name in ('scrambled', 'pointed', 'webbed'):
    path = Path(__file__).resolve().parent / 'assets' / (name + '.wav')
    with wave.open(str(path), 'rb') as source:
        params = source.getparams()
        assert params.nchannels == 1 and params.sampwidth == 2
        samples = array('h', source.readframes(params.nframes))
    for i, value in enumerate(samples):
        samples[i] = round(value * (0.78 + 0.22 * math.sin(2 * math.pi * 42 * i / params.framerate)))
    with wave.open(str(path), 'wb') as target:
        target.setparams(params)
        target.writeframes(samples.tobytes())
    print(name, round(params.nframes / params.framerate, 2), 'seconds')
