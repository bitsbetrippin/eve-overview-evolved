# Combat meters release — 2026-09-22

- Added a bold aqua TARGET DPS panel above the controls on every character
  dashboard, showing the latest target hit and its rolling 15-second DPS.
- Added a bright red TOP INCOMING DAMAGE panel directly underneath,
  ranking three named attackers by damage in the same rolling window.
- Added full-name and damage-total hover details, safe fitting of long names,
  and fixed aqua/red colors across themes.
- Preserved Stop snapshots and Reset behavior for both new panels.
- Parse plain and HTML-tagged damage lines, including corporation tags,
  ship suffixes, punctuation and HTML entities in names.
- Kept the portable START.bat launch and bundled runtime/dependencies.

Target selection itself is not visible to this log-based application.
The displayed target is the latest name you hit. Identically named NPCs
share totals. Incoming rankings reflect the last 15 seconds, not the
largest single hit or lifetime damage. Press Play to start tracking.

Validation: 22 automated tests covering damage attribution, target switches,
expiry, ranking, bounded memory, real log-to-widget updates, Stop/Reset,
long-name layout, theme colors and the previous portable-startup checks.
Visual review used synthetic combat data. Live EVE gameplay was not tested.

---

# Portable startup release

- Added START.bat: locates the extracted folder and launches ratting.py
  with a private, bundled Python runtime.
- Bundled Python 3.13.15, Tcl/Tk and all app dependencies for Windows x64.
  Startup requires no package installation or network access.
- Isolated Python from system PATH, PYTHONHOME and PYTHONPATH settings.
- Set Tcl/Tk paths relative to the app folder.
- Detect Windows' actual Documents folder, including OneDrive redirection,
  with standard Documents and Linux/Proton fallbacks.
- Preserve existing saved custom EVE log paths and user configuration.
- Keep launch errors visible and write Python startup errors to startup.log.
- Include an offline runtime self-test and repeatable release builder with
  checksum verification, pinned wheels and GUI regression checks.

Based on upstream commit 9e3cd612af5d1f7d078c746ac2703c6c19c4b9f1.
This is a local build for your fork, not an upstream-published release.

Validated: runtime/dependency imports and Tk initialization; real dashboard
construction and clean shutdown using empty test logs; path detection;
configuration preservation; missing source error handling.
Live gameplay tracking and market-price services are not integration-tested.
