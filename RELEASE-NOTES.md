# Eve-Overlay-Evolved v0.7.7

Extract **Eve-Overlay-Evolved-v0.7.7-Windows-x64.zip** and run **START.bat**.

**Jammed is now live.** Confirmed personal `You're jammed by` combat events
play your selected voice and show a red JAMMED alert with the attacker's identity.
SamL uses the full clip already supplied. Robot, Commanding, Dramatic and
News anchor each have a new Jammed clip; its TEST button works for every style.

Settings > EWAR SOUND: Voice > VOICE STYLE: SamL (or another style) > APPLY.
Beep mode beeps; Off mutes. Low/Medium/High gain and saved choices are preserved.
Other-target scram/point/web events still beep. The supplied log confirms only
personal jamming; nearby/outgoing jam detection awaits its own verified format.
Generic targeting failures, warp interference and sensor tuning do not trigger jams.

Duplicate jam records share the 10-second audio cooldown. Personal alerts retain
priority over nearby beeps; their queue expiry is now 15 seconds so four full
SamL clips can play in turn. Nearby expiry stays 8 seconds. Alerts describe
recorded events, not continuous jam state or duration.

All 20 audio WAVs are bundled. No Python installation or audio synthesis setup
is needed. Upgrade into a fresh folder, copying ratting_config.json and
ratting_history.json from the closed old app if you want to retain your settings.

Validation: 104 automated checks, including anonymized real ECM replay,
duplicate suppression, all five voices, volume levels and portable startup.
The contributed full log contains three jam records, all recognized as personal.
Live EVE gameplay has not been tested.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
