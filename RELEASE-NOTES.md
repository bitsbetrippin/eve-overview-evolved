# Eve-Overlay-Evolved v0.7.6

Extract **Eve-Overlay-Evolved-v0.7.6-Windows-x64.zip** and run **START.bat**.

In **Settings > EWAR SOUND: Voice**, scram, point and web events targeting
your character play your selected voice. Events targeting another pilot,
drone or your own outgoing EWAR target play a beep when present in the log.
Only personal events produce the personal EWAR visual warning.

Personal alerts play before queued nearby beeps, and nearby activity cannot
consume their repeat limit. Each effect repeats at most once every 10 seconds
per personal/nearby group across the fleet. Live queued events expire after
8 seconds; an already playing clip finishes before the next starts.

Beep mode beeps for both groups; Off mutes both. Saved voice and volume choices
are preserved. Low/Medium/High (100%/200%/300%) gain works for both sounds.
SamL and all other voice styles remain available. Jammed stays preview-only.
Only recognized English gamelog events can trigger alerts.

Upgrade: close the old app, extract into a new folder, then copy
ratting_config.json and ratting_history.json before launching.

Validation: 98 automated checks, including recipient routing, independent
cooldowns, queue priority, mute/Beep settings and clean portable startup.
Live EVE gameplay has not been tested.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
