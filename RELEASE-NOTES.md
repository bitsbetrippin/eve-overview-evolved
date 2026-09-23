# Eve-Overlay-Evolved v0.6.1

This patch addresses dashboards opening outside the visible monitor area
or being difficult to recover from the fleet overview.

Download **Eve-Overlay-Evolved-v0.6.1-Windows-x64.zip**, choose **Extract All**,
and double-click **START.bat**. Python, Tcl/Tk and dependencies are included.

- New dashboards open beside the overview in a cascade.
- Saved off-screen positions recover using the current monitor work areas.
- **SHOW PANELS** reveals, expands and moves active dashboards and their
  existing detached sections beside the overview. Session counters and
  Play/Pause/Stop state are retained; press Play to begin tracking.
- A character-row click recovers an off-screen dashboard.
- Reachable saved positions, including left-hand monitors, are preserved.

The aqua target-DPS meter, red incoming-attacker ranking, v0.6 branding,
and credits remain included. Contributions: **@bitsbetrippin**. Original
concept and base implementation: **Eve-Ratting by @psychojf**.

To upgrade, close the old app, extract into a new folder, then copy
`ratting_config.json` and `ratting_history.json` from the old folder before
launching. Do not overwrite the new runtime or source with old files.

Validation: 32 startup, combat, monitor-placement and real Tk GUI checks;
clean ZIP launches without system Python on PATH and with conflicting
Python/Tk environment settings. Test logs are synthetic; live EVE gameplay
and online market-price services have not been integration-tested.

Repository: https://github.com/bitsbetrippin/eve-overview-evolved
Release tag: v0.6.1 (the existing v0.6 tag remains unchanged).
Upstream: https://github.com/psychojf/Eve-Ratting
See README.md for layout, architecture and troubleshooting.
