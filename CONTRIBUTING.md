# Contributing to Eve-Overlay-Evolved

Contributions and reports belong in
[bitsbetrippin/eve-overview-evolved](https://github.com/bitsbetrippin/eve-overview-evolved).
Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and retain the original
and Evolved credits in [ATTRIBUTION.md](ATTRIBUTION.md).

## Development

Use Python 3.9+ with Tkinter to run source. Install optional features with
`python -m pip install -r requirements.txt`, then `python ratting.py`.
The portable Windows release bundles all these packages.

- Keep UI/session changes in `ratting.py`, named combat metrics in
  `combat_meter.py`, path discovery in `eve_paths.py`, and release identity
  in `app_info.py`. Monitor placement belongs in `window_placement.py`; incoming neutralizer/Nos accounting belongs in `neut_meter.py`.
- Keep Tk operations on the UI thread and slow lookups off it.
- Preserve legacy JSON filenames and saved custom paths.
- Treat log lines and clipboard contents as data, never executable input.
- Keep the app a passive log reader; do not add game-input automation or
  client memory access. Document new network or clipboard behavior.
- Preserve aqua/red combat-panel colors when adding themes.

## Verification

The release builder runs all four test suites against a fresh runtime:

```bat
python build_release.py
```

For direct tests, copy the runtime folder from a portable release beside
the source and use:

```bat
runtime\python.exe -I -B tests\test_release.py
runtime\python.exe -I -B tests\test_combat.py
runtime\python.exe -I -B tests\test_panels.py
runtime\python.exe -I -B tests\test_neuts.py
```

Use synthetic or anonymized log fixtures and isolated settings in tests. Do not commit personal
logs, JSON state, runtime binaries, build folders or caches. For changes
that affect layout, inspect a rendered pilot window as well as test results.

## Pull requests and reports

Keep changes focused. Explain the problem, resulting behavior and checks
performed. Include the application version, Windows/Python version,
reproduction steps and a short redacted example when reporting a bug.
Do not upload a complete private gamelog or clipboard dump.

Release metadata lives in `app_info.py`. Monitor placement belongs in `window_placement.py`; incoming neutralizer/Nos accounting belongs in `neut_meter.py`. Update the startup banner,
README, changelog and release notes alongside it, then rebuild the ZIP.
Tag the tested source commit and attach the versioned Windows ZIP to the
release. GitHub's automatic source ZIP does not include the runtime.

Report security problems through the channels in [SECURITY.md](SECURITY.md).
