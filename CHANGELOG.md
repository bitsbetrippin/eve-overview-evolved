# Changelog

## v0.6.1 — 2026-09-22

- Open new dashboards beside the overview in a cascade, replacing the
  old default at the far edge of the desktop.
- Recover saved off-screen positions using current monitor work areas;
  preserve reachable positions, including negative monitor coordinates.
- Validate character placement after Tk maps the window, when its actual
  coordinates become available.
- Add SHOW PANELS to recover hidden, collapsed and misplaced dashboards
  plus existing detached sections, preserving session data and run state.
- Recover an off-screen dashboard when its character row is clicked.
- Add ten placement and complete-fleet GUI regression checks.

## v0.6 — 2026-09-22

- Renamed the product to **Eve-Overlay-Evolved**; versioned startup,
  window/tray titles, diagnostics and the Windows ZIP filename.
- Added shared product metadata in `app_info.py`.
- Credited @bitsbetrippin's contributions and @psychojf's original
  Eve-Ratting concept and base implementation.
- Rewrote the README with architecture, data flow, layout, controls,
  module responsibilities, development and upgrade instructions.
- Updated user, contributor and security guidance, support links,
  notices and release documentation for the fork.
- Preserved legacy config/history/cache filenames and debug-variable
  compatibility so previous settings can migrate unchanged.

## v0.5 — uploaded combat-meter update

- Added the bold aqua target-DPS panel and bright red top-three incoming
  attacker panel above the character-dashboard controls.
- Added 15-second named rolling totals, target switching, expiry,
  long-name hover details, Stop snapshots and Reset behavior.
- Expanded parsing for tagged/plain damage lines and decorated names.
- Added synthetic combat and real Tk widget tests.

## Earlier portable startup work

- Added START.bat, bundled Python/Tk and pinned app dependencies.
- Added isolated paths, startup errors and an offline runtime self-test.
- Added Windows redirected-Documents and OneDrive log discovery.
- Added a checksum-verifying release builder and startup/path tests.

Original concept/base: [Eve-Ratting by psychojf](https://github.com/psychojf/Eve-Ratting).
Evolved contributions: [bitsbetrippin](https://github.com/bitsbetrippin).
