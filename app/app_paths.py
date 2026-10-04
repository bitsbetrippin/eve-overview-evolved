"""Resolve portable resources and writable data independently of the launch cwd."""
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parent
ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else APP_DIR.parent
DATA_DIR = ROOT / 'data'
CACHE_DIR = DATA_DIR / 'cache'
LOG_DIR = DATA_DIR / 'logs'

LEGACY_FILES = {
    'ratting_config.json': 'data/ratting_config.json',
    'ratting_history.json': 'data/ratting_history.json',
    'ratting_prices.json': 'data/cache/ratting_prices.json',
    'ratting_nameids.json': 'data/cache/ratting_nameids.json',
    'ratting_debug.log': 'data/logs/ratting_debug.log',
    'startup.log': 'data/logs/startup.log',
}


def prepare_data(root=ROOT):
    """Import legacy root state only if absent; preserve originals and new state."""
    root = Path(root)
    for folder in ('data', 'data/cache', 'data/logs'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    for name, relative in LEGACY_FILES.items():
        source, target = root / name, root / relative
        if not source.is_file() or target.exists():
            continue
        content = source.read_bytes()
        try:
            stream = target.open('xb')
        except FileExistsError:
            continue
        try:
            with stream:
                stream.write(content)
        except BaseException:
            target.unlink(missing_ok=True)
            raise


def resource_path(relative):
    base = Path(getattr(sys, '_MEIPASS', APP_DIR))
    return str(base / relative)
