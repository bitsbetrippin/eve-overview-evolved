# Eve-Overlay-Evolved v0.7.5

Extract **Eve-Overlay-Evolved-v0.7.5-Windows-x64.zip** and run **START.bat**.

Settings > EWAR SOUND: **Voice** > VOICE STYLE: **SamL** > **APPLY**.
SamL includes four user-supplied clips, converted from MP3 to 16-bit mono WAV:

- Scrambled, Pointed, Webbed: use the existing automatic incoming-event triggers.
- **Jammed: placeholder only.** Its TEST button works with SamL selected;
  automatic ECM-jamming detection is deferred until a later release.

All clips retain their full duration (about 3.5–3.6 seconds). Originals remain
unchanged. Low/Medium/High (100%/200%/300%) gain applies to previews and alerts.
Selections persist. Robot / Low remain the defaults; no other voices are replaced.
The four previews play sequentially without live-alert expiry. Live alerts keep
the 8-second queue expiry and 10-second repeat limit per effect across the fleet.

Voice files live in assets/voices/saml. The logo and all 16 audio files are
bundled for offline use. No MP3 decoder or speech engine is needed to run.

Upgrade: close the old app, extract into a new folder, then copy
ratting_config.json and ratting_history.json before launching.

Validation: 88 automated checks, including imported-clip checksums and duration,
SamL routing, Jammed preview-only behavior, saved settings and portable startup.
Live EVE gameplay and perceived speaker loudness have not been tested.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
