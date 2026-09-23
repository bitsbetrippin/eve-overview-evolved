# Eve-Overlay-Evolved v0.6.1

A desktop combat and income overlay for EVE Online. Track target DPS,
who is dealing the most damage to you, bounties, loot and session progress
across multiple characters.

**Contributions:** [@bitsbetrippin](https://github.com/bitsbetrippin) — portable
launch workflow, combat-meter enhancements, feature direction, testing and
release development for Eve-Overlay-Evolved.

**Original concept and base implementation:**
[Eve-Ratting](https://github.com/psychojf/Eve-Ratting), by
[@psychojf](https://github.com/psychojf). This project builds on that work;
original authorship and bundled component notices are retained.
See [ATTRIBUTION.md](ATTRIBUTION.md).

**Repository:** [bitsbetrippin/eve-overview-evolved](https://github.com/bitsbetrippin/eve-overview-evolved).
The repository URL uses `overview`; the application name is **Eve-Overlay-Evolved**.
**Release tag:** `v0.6.1`.

## Download, extract, launch

1. Download **Eve-Overlay-Evolved-v0.6.1-Windows-x64.zip** from the release assets.
2. Right-click the ZIP and choose **Extract All** into a writable folder.
3. Open the extracted folder and double-click **START.bat**.
4. Select your characters, then press **Play** on a character dashboard.

The Windows 10/11 x64 package includes Python 3.13.15, Tcl/Tk and all app
packages. No Python installation, administrator access, pip command, PATH
editing or first-run setup download is needed. Keep the extracted files
and `runtime/` folder together. The console stays open while the app runs.
Quit all windows using the **X on the fleet overview**; a character
window's X hides that dashboard.

GitHub's **Code > Download ZIP** contains source without the runtime.
Use the versioned Windows release ZIP for the ready-to-run experience.
Market-price lookups use an internet connection while the app is running.

## What's new in v0.6.1

- New character dashboards open in a cascade beside the fleet overview.
- Saved positions are checked against current monitor work areas, including
  monitors left of the primary screen. Unreachable panels move back into view.
- **SHOW PANELS** in the fleet overview reveals, expands and repositions
  active character dashboards and their existing detached sections.
- Clicking a character whose dashboard is off-screen recovers it. Session
  counters and Play/Pause/Stop state are preserved during recovery.
- Added regression coverage for a complete fleet with multiple pilots,
  saved positions, hidden/collapsed dashboards and detached sections.

The release retains v0.6 branding and attribution, portable startup,
Documents/OneDrive log detection, aqua target DPS and red incoming-damage
rankings. See [CHANGELOG.md](CHANGELOG.md) and [RELEASE-NOTES.md](RELEASE-NOTES.md).

## Interface layout

The **fleet overview** is the main hub: one row per character with total
net ISK, ISK/hour, session time and the detached DPS-overlay toggle. Its
header provides Settings, Fleet Manager, clipboard lock and Quit. Hover
the application title for contributor and upstream credits. **SHOW PANELS**
beside ACTIVE RATTING FLEET brings dashboards back next to the overview.
Click a character row to show/hide that pilot's dashboard; the DPS column
controls the separate aggregate DPS overlay.

![Fleet overview in v0.6.1](overview-v0.6.1.png)

Each **character dashboard** is arranged from top to bottom:

| Section | Purpose |
| --- | --- |
| Character title bar | Pilot name; drag to move or double-click to collapse |
| **TARGET DPS — bold aqua** | DPS and name of the latest target hit |
| **TOP INCOMING DAMAGE — bold bright red** | Three attackers ranked by recent damage, with their DPS |
| Controls | Play, Pause, Stop, Reset, Next Site and clipboard lock |
| Alerts | Combat/EWAR notifications and session events |
| ISK tracker | ISK/hour, session timer, bounties, tax, kills, loot and net income |
| Missions or anomalies | Mission progress or site timing, counts and averages |

![Character dashboard with sample combat data](dashboard-v0.6.1.png)

*Preview uses synthetic combat data. The two combat panels stay aqua/red
across themes. Other panels follow the selected theme.*

ISK, Missions, Anomalies and Alerts can detach into separate windows.
The independent DPS overlay remains available from the overview's DPS cell:
left-click to toggle; right-click for position and view options. It shows
total outgoing/incoming DPS, a graph, or both. Windows transparency and
click-through behavior are intended for borderless/fixed-window play.

## Combat meters and controls

Both panels use a **rolling 15-second window** and refresh at the configured
UI interval, **250 ms by default**. DPS is damage inside that window divided
by 15; it ramps up as hits arrive and falls to zero as they expire.

- **Target DPS** follows the latest name you hit in the combat log.
  Selecting a target alone cannot update the meter. If drones and weapons
  hit different targets, the latest hit determines the displayed target.
- **Incoming damage** aggregates damage by attacker name, sorts highest
  first, and shows three attackers. Hover for the full name and damage
  total. Rankings reflect recent totals, not largest volley or lifetime damage.
- Identically named NPCs share totals because parsed damage lines do not
  provide unique NPC IDs. Long names retain full hover details. Parsing
  supports plain/HTML-tagged English damage lines, corporation tags,
  ship suffixes, punctuation and HTML entities.

The original aggregate DPS counters and detached overlay remain separate
from the per-target display.

| Control | Current behavior |
| --- | --- |
| Play | Starts/resumes tracking; a new log session backfills recent bounties |
| Pause | Pauses the timer and log reading; recent damage ages out of the meters |
| Stop | Stops reading and freezes displayed values, including combat panels |
| Reset / Next Site | Saves the session when applicable, clears counters and meters, and leaves tracking stopped; press Play again |
| CLIP | Locks/unlocks clipboard reading across the fleet |
| UNDO | Removes the last imported loot value from that character's session |

**Site gap** (45 seconds by default) groups combat into anomalies without
resetting the session. **Next Site** performs a full reset. For an
MTU/salvage run, keep one session running to count all sites and the final
loot haul together.

## Architecture

The UI, parsing and existing session logic remain centered in `ratting.py`.
Small modules isolate release identity, startup, log-path discovery and
named combat metrics and monitor-aware placement.

```mermaid
flowchart TD
    A[START.bat] --> B[Bundled Python: isolated mode]
    B --> C[startup.py: paths, Tcl/Tk, error reporting]
    C --> D[ratting.py: MainUI and CharacterWindow]
    E[EVE Gamelogs] --> F[Log reader: watchdog and polling]
    F --> G[Damage parsing and session events]
    G --> H[Data: aggregate DPS, income, history]
    G --> I[CombatMeter: named damage over 15 seconds]
    H --> D
    I --> D
    J[eve_paths.py: Documents and fallbacks] --> F
    K[app_info.py: name, version, attribution] --> C
    K --> D
    L[Public ESI prices and loot clipboard] --> H
    D --> M[Local JSON settings and history]
    N[window_placement.py: monitor work areas and recovery] --> D
```

| File / component | Responsibility |
| --- | --- |
| `START.bat` | Locates its folder and invokes bundled Python with `-I -B` |
| `startup.py` | Sets app/Tcl/Tk paths, starts `ratting.py`, provides `--self-test` and error logs |
| `app_info.py` | Product name, version, release tag, repository URL and credits |
| `ratting.py` | Tkinter windows, log tailing/rotation, session state, themes, alerts and price workers |
| `combat_meter.py` | Damage-line normalization, bounded named rolling totals, expiry and incoming ranking |
| `eve_paths.py` | Redirected Documents, OneDrive, standard Documents and Linux/Proton path candidates |
| `window_placement.py` | Monitor work areas, reachable title checks and dashboard recovery |
| `build_release.py` | Verifies/stages Python, installs pinned wheels, tests and builds the versioned ZIP |
| `requirements-windows.lock` | Exact Windows x64 wheels and SHA-256 hashes |
| `tests/test_release.py` | Startup, log paths, settings preservation and main-window checks |
| `tests/test_combat.py` | Parsing, attribution, rolling totals, log-to-widget updates and character panels |
| `tests/test_panels.py` | Multiple-pilot startup, row clicks, hidden/collapsed recovery and monitor geometry |

The UI uses Tk's event loop. File notifications and timer polling drive
incremental log reading; market lookups run in background threads. Named
damage buckets use monotonic arrival time and a bounded event queue. Stop
snapshots remain frozen while live damage expires. JSON settings/history
use temporary-file replacement when written.

The app reads gamelogs produced by EVE. It does not read game-process
memory, modify the client or automate game inputs. Public ESI requests
supply market prices; clipboard access supports loot valuation unless
locked with CLIP.

## Paths, settings and upgrades

Windows discovery starts with the current user's actual Documents folder,
including OneDrive/redirection, then checks known fallbacks. A typical
location is `Documents/EVE/logs/Gamelogs`. Saved custom `log_path` settings
are preserved; change the path in Settings if needed. Characters appear
after EVE has written gamelogs.

All app state is stored beside `ratting.py`:

| File | Contents |
| --- | --- |
| `ratting_config.json` | Log path, pilot preferences, themes and window positions |
| `ratting_history.json` | Saved sessions |
| `ratting_prices.json` / `ratting_nameids.json` | Disposable price and item-ID caches |
| `startup.log` | Most recent caught Python startup/application failure |
| `ratting_debug.log` | Optional internal diagnostics |

The `ratting_*` filenames and `ratting.py` entry point remain for
compatibility with earlier Eve-Ratting-based releases.

To upgrade, close the old app, extract v0.6.1 into a new folder, and copy
`ratting_config.json` and `ratting_history.json` into it before launching.
The caches may also be copied. Do not overwrite the new runtime/source
with files from the old release.

## Source development and release builds

For source development, install Python 3.9+ with Tkinter, clone this
repository, then run:

```bat
python -m pip install -r requirements.txt
python ratting.py
```

Keep the helper modules beside `ratting.py`. Optional packages provide
clipboard support (`pyperclip`), tray/images (`pystray`, `Pillow`), and
file notifications (`watchdog`). All are included in the Windows release.
Source retains Linux/Proton path fallbacks; v0.6.1 packaging and GUI
verification target Windows x64.

Build on Windows:

```bat
python build_release.py
```

The builder verifies the official CPython 3.13.15 x64 runtime, installs
hash-pinned wheels, runs a runtime self-test and all three regression suites,
then writes:

```text
dist/Eve-Overlay-Evolved-v0.6.1-Windows-x64.zip
dist/Eve-Overlay-Evolved-v0.6.1-Windows-x64.zip.sha256
```

For an offline rebuild, supply a cached runtime archive and the exact wheels:

```bat
python build_release.py --cache PATH-TO-RUNTIME-CACHE --wheel-dir PATH-TO-WHEELS
```

For direct regression testing, copy `runtime/` from a portable release
beside the source, then run:

```bat
runtime\python.exe -I -B tests\test_release.py
runtime\python.exe -I -B tests\test_combat.py
runtime\python.exe -I -B tests\test_panels.py
```

Runtime/build folders and user state are excluded from Git. Release source
belongs to the `v0.6.1` tag; the portable ZIP is the downloadable release
asset, distinct from GitHub's source-only ZIP.

## Troubleshooting and verification

- Missing runtime/script: extract the complete versioned Windows ZIP.
- No pilots: confirm the log path and that EVE has written gamelogs.
- Only the fleet overview appears: click **SHOW PANELS**. It brings active
  dashboards and existing detached sections beside the overview, expands
  collapsed dashboards and saves their new positions without resetting data.
- A pilot is absent from the fleet: enable it in Fleet Manager first.
- Meters show zero: press Play and allow new combat hits to arrive.
- Startup failure: read the console and `startup.log`, if created.
- Runtime check: `START.bat --self-test` reports product/version, Python,
  Tk, package versions and log path without reading logs or the clipboard.
- Internal diagnostics: set `EVE_OVERLAY_EVOLVED_DEBUG=1` or add
  `"debug_log": true` to the config. Legacy `EVE_RATTING_DEBUG` also works.

Validation covers 32 automated checks and clean-extraction startup without
system Python on PATH, including conflicting Python/Tk settings. GUI
previews and combat tests use synthetic data. Live EVE sessions and online
market-price services are not integration-tested.

See [HOW_TO.txt](HOW_TO.txt) and [CONTRIBUTING.md](CONTRIBUTING.md) for more.
Report bugs in [this project's issue tracker](https://github.com/bitsbetrippin/eve-overview-evolved/issues).
Bundled notices are in [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt).
