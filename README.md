# Eve-Overlay-Evolved v0.7.8

An EVE Online desktop overlay for fleet DPS, incoming damage, capacitor drain,
income tracking and spoken EWAR alerts.

## Download, extract, launch

1. Download **Eve-Overlay-Evolved-v0.7.8-Windows-x64.zip** from the release assets.
2. Use **Extract All** into a new writable folder.
3. Open that folder and double-click **START.bat**.
4. Select your characters, then press **Play**. Use **SHOW PANELS** to restore dashboards.

Windows 10/11 x64. Python, Tkinter and dependencies are bundled; no installation
or first-run download is needed. Keep all subfolders together. GitHub's automatic
source ZIP does not include the runtime.

## Folder layout

```text
Eve-Overlay-Evolved-v0.7.8-Windows-x64/
├── START.bat          Launch the application
├── README.md          Quick start and folder map
├── app/               Application code and dependency manifests
│   └── assets/        Icons, alliance logo and voice clips
├── runtime/           Bundled Python, Tk and packages
├── data/              Your settings and session history
│   ├── cache/         Rebuildable market/name caches
│   └── logs/          Startup and optional debug logs
└── docs/              User guide, release notes, credits and images/
```

Only START.bat and README.md are files in the release root. The source ZIP also
has `tools/` for build/audio utilities, `tests/` for regression checks, and `.gitignore`.

## Upgrade and saved data

Close the old app. Extract the new release into a fresh folder.

- From **v0.7.7 or earlier:** copy `ratting_config.json` and `ratting_history.json`
  from the old folder into the new **data/** folder before launch.
- From **v0.7.8 or later:** copy your existing **data/** folder into the new release.

If legacy state files are placed beside START.bat, startup copies them to their
new locations only if those destinations are absent. Originals are preserved;
existing files in data/ always take precedence. Nothing is fetched from another
installation automatically.

Voice clips now live in **app/assets/**; SamL is in **app/assets/voices/saml/**.
Startup errors are recorded in **data/logs/startup.log**. Diagnostics:
`START.bat --self-test`.

## Features and architecture

The fleet overview shows target DPS. Dashboards include aqua target DPS, red
incoming damage and amber combined neut/Nos drain. Personal scram/point/web/jam
events play the chosen voice in Voice mode; logged other-target scram/point/web
events beep. Beep-only and Off modes remain available, with 100%/200%/300% gain.
Jamming uses confirmed personal combat events; other-target jam formats remain
unverified. Robot, Commanding, Dramatic, News anchor and SamL are bundled.

START.bat invokes bundled Python, which runs app/startup.py. app/app_paths.py
resolves resources and saved data; app/ratting.py owns the UI and log reader.
Separate modules handle damage, cap drain, EWAR audio and window placement.

- [Full user guide and architecture](docs/USER-GUIDE.md)
- [Release notes](docs/RELEASE-NOTES.md) and [changelog](docs/CHANGELOG.md)
- [Development and builds](docs/CONTRIBUTING.md)
- [Third-party notices](docs/THIRD-PARTY-NOTICES.txt)

Validated with 109 automated checks, clean ZIP extraction, portable startup
without system Python on PATH, and legacy-settings import.

**Contributions:** [@bitsbetrippin](https://github.com/bitsbetrippin).
**Original concept/base:** [Eve-Ratting](https://github.com/psychojf/Eve-Ratting)
by [@psychojf](https://github.com/psychojf). [Full attribution](docs/ATTRIBUTION.md).

Repository: [bitsbetrippin/eve-overview-evolved](https://github.com/bitsbetrippin/eve-overview-evolved).
