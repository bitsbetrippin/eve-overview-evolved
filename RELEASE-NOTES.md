# Eve-Overlay-Evolved v0.7.2

Download **Eve-Overlay-Evolved-v0.7.2-Windows-x64.zip**, Extract All,
then run **START.bat**. Python and dependencies are bundled.

The fleet overview now displays **TARGET DPS** for each character, using the
same rolling 15-second, latest-hit-target meter as the dashboard. It refreshes
every 500 ms and does not require bounty payouts or separate overlays.
Inactive rows show PAUSED, STOPPED, OFFLINE or NO TICK instead of stale live DPS.
The **OVL** column retains the separate overlay toggle and right-click menu.

Press Play on your dashboards, enable **Background Monitoring** in Settings
and Apply, then hide dashboards by clicking their character rows.
For already-hidden dashboards, show and hide them again after enabling the setting.
New installations default background monitoring on; existing preferences remain.

Upgrade: close the old app, extract into a new folder, and copy
ratting_config.json and ratting_history.json before launching.
Narrow overview layouts expand to fit the additional column.

Validation: 63 automated checks, including real Tk fleet rows and synthetic logs.
Live EVE gameplay has not been tested.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
