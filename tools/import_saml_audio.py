"""Developer-only MP3 import. Requires miniaudio==1.71; users only need the WAVs."""
import argparse
import hashlib
import json
from pathlib import Path
import wave

SOURCES = {'Sam-Scrambled.mp3': 'scrambled.wav', 'Sam-Pointed.mp3': 'pointed.wav',
           'Sam-Web.mp3': 'webbed.wav', 'Sam-Jammed.mp3': 'jammed.wav'}


def convert(source, destination):
    import miniaudio
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    for filename, output in SOURCES.items():
        original = source / filename
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        sound = miniaudio.decode_file(str(original), output_format=miniaudio.SampleFormat.SIGNED16,
                                      nchannels=1, sample_rate=22050)
        path = destination / output
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((1, 2, 22050, len(sound.samples), 'NONE', 'not compressed'))
            stream.writeframes(sound.samples.tobytes())
        assert hashlib.sha256(original.read_bytes()).hexdigest() == before
        manifest.append(dict(source=filename, source_sha256=before, output=output,
                             output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             duration_seconds=round(len(sound.samples)/22050, 3),
                             channels=1, sample_rate=22050, pcm_bits=16))
    (destination/'import-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[1]/'app/assets/voices/saml')
    args = parser.parse_args()
    convert(args.source.resolve(), args.destination.resolve())
