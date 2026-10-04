# Contributing to Eve-Overlay-Evolved

Contributions and reports belong in
[bitsbetrippin/eve-overview-evolved](https://github.com/bitsbetrippin/eve-overview-evolved).
Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and retain the original
and Evolved credits in [ATTRIBUTION.md](ATTRIBUTION.md).

## Development

Use Python 3.9+ with Tkinter to run source. Install optional features with
`python -m pip install -r app/requirements.txt`, then `python app/ratting.py`.
The portable Windows release bundles all these packages.

- Keep UI/session changes in `app/ratting.py`, named combat metrics in
  `app/combat_meter.py`, path discovery in `app/eve_paths.py`, and release identity
  in `app/app_info.py`. Monitor placement belongs in `app/window_placement.py`; incoming neutralizer/Nos accounting belongs in `app/neut_meter.py`.
- Keep battle timing, peak accounting and payload schema in `app/battle_history.py`.
  Cover damage-idle boundaries, delayed batches, source peaks, corrupt files and independent UI selection.
- Keep Tk operations on the UI thread and slow lookups off it.
- Preserve JSON filenames and saved custom paths; writable state belongs under data/.
- Centralize resource/data paths in app/app_paths.py. START.bat and README.md are the only release-root files.
- Treat log lines and clipboard contents as data, never executable input.
- Keep the app a passive log reader; do not add game-input automation or
  client memory access. Document new network or clipboard behavior.
- Preserve aqua/red combat-panel colors when adding themes.

## Verification

The release builder runs all six test suites against a fresh runtime:

```bat
python tools/build_release.py
```

For direct tests, copy the runtime folder from a portable release beside
the source and use:

```bat
runtime\python.exe -I -B tests\test_release.py
runtime\python.exe -I -B tests\test_combat.py
runtime\python.exe -I -B tests\test_panels.py
runtime\python.exe -I -B tests\test_neuts.py
runtime\python.exe -I -B tests\test_ewar.py
runtime\python.exe -I -B tests\test_battles.py
```

Use synthetic or anonymized log fixtures and isolated settings in tests. Do not commit personal
logs, JSON state, runtime binaries, build folders or caches. For changes
that affect layout, inspect a rendered pilot window as well as test results.

## Pull requests and reports

Keep changes focused. Explain the problem, resulting behavior and checks
performed. Include the application version, Windows/Python version,
reproduction steps and a short redacted example when reporting a bug.
Do not upload a complete private gamelog or clipboard dump.

Release metadata lives in `app/app_info.py`. Monitor placement belongs in `app/window_placement.py`; incoming neutralizer/Nos accounting belongs in `app/neut_meter.py`. Update the startup banner,
README, changelog and release notes alongside it, then rebuild the ZIP.
Tag the tested source commit and attach the versioned Windows ZIP to the
release. GitHub's automatic source ZIP does not include the runtime.

Report security problems through the channels in [SECURITY.md](SECURITY.md).
