# Eve-Overlay-Evolved v0.7.8

The Windows ZIP now has only **START.bat** and **README.md** as files in its root.
Code/assets live in **app/**; Python remains in **runtime/**; documentation and
screenshots are in **docs/**. Settings and history live in **data/**, with
cache/ and logs/ subfolders. Source utilities live in tools/ and tests/.

Extract into a **new folder** and run START.bat. To upgrade from v0.7.7 or earlier,
close the old app and copy its root ratting_config.json and ratting_history.json
into the new data/ folder before launch. From v0.7.8 onward, copy the data/ folder.
Legacy files placed in the release root are copied into the new layout only if
the destination is absent; originals and existing data are preserved.

All combat meters, fleet DPS, the Initiative logo, voice/volume settings and
personal ECM jam alerts are retained. SamL WAVs are now in app/assets/voices/saml/.
Startup errors are in data/logs/startup.log. No Python installation is needed.

Validation: 109 automated checks; clean root layout; resource lookup from another
working directory; byte-preserving legacy import and existing-data precedence;
clean ZIP launches with invalid external Python/Tk settings.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
