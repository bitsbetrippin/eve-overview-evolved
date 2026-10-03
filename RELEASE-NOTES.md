# Eve-Overlay-Evolved v0.7.3

Download **Eve-Overlay-Evolved-v0.7.3-Windows-x64.zip**, Extract All and run
**START.bat**. Python, logo and voice clips are included for offline startup.

In Settings, enable **SHOW THE INITIATIVE LOGO** and click **APPLY**. The logo
appears beside target DPS on dashboards and above the fleet overview table.
**EWAR SOUND** offers Voice (default), Beep or Off. Test buttons preview each
robotic warning: **You are scrambled / You are pointed / You are webbed**.

Only incoming English log messages directed to you trigger personal alerts.
Nearby ships, drones and outgoing tackle are excluded. Different warning types
play in sequence; the same type repeats at most once every 10 seconds across
the fleet. Queued clips older than 8 seconds are discarded. An in-progress clip
may finish when sound is switched off. Voice does not announce pilot names.

Press Play to track. Enable Background Monitoring to keep reading while panels
are hidden. Pause/Stop halt new log reading. Warnings reflect logged attempts,
not a guarantee of the effect's continued presence or a notification that it ended.

Upgrade: close the old app, extract into a new folder, copy ratting_config.json
and ratting_history.json, then launch. Logo defaults off; existing settings persist.

Validation: 75 automated checks with synthetic logs and real Tk windows, WAV
integrity, and clean portable startup without installed Python. Live EVE gameplay
and the user's audio device have not been tested.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
