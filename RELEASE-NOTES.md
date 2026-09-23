# Eve-Overlay-Evolved v0.7.1

Download **Eve-Overlay-Evolved-v0.7.1-Windows-x64.zip**, Extract All, then
double-click **START.bat**. Python and dependencies are included.
Click SHOW PANELS if needed and press Play to start tracking.

The amber **INCOMING CAP DRAIN** panel now includes **Nosferatu**:

- Combined neutralizer + Nos session GJ and a 15-second GJ/sec rate.
- Separate NEUT/NOS subtotals, plus a breakdown for each top source on hover.
- Source rankings use combined session loss. Hover also shows the last module.
- Negative incoming `GJ energy drained to` amounts are counted as positive
  loss. Capacitor gains, wrong signs/directions and unknown colors are excluded.
- Zero records add no loss. Distinct identical same-second records still count.

Stop freezes all values; Reset / Next Site clears them. Pause stops reading;
resume skips paused entries, matching existing behavior. Old records are not
backfilled. Original English raw-log color tags are required for direction.
The meter tracks reported loss, not remaining capacitor or net cap balance.

Session history preserves neut-only fields and adds Nos-only and combined
fields. Old history records are unchanged. Close the old app, extract into a
new folder, and copy ratting_config.json/ratting_history.json to upgrade.

Validation: 60 automated checks, including the expanded anonymized sample
with 2,307 GJ neut + 1,641 GJ Nos = 3,948 GJ, real Tk UI checks, and clean
portable launches without system Python. Live EVE gameplay is not tested.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
Release tag: v0.7.1. Earlier tags remain unchanged.
See README.md for architecture, layout, supported formats and controls.
