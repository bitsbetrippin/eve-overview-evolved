# Eve-Overlay-Evolved v0.8.0 beta

**See the damage. Hear the threat. Review the fight.**

A portable EVE Online overlay that puts live DPS, incoming pressure, capacitor
drain, spoken EWAR warnings and fleet income in one place. The new **Battle
Review** remembers your engagements so you can compare peaks after the grid
goes quiet.

## Download, extract, launch

1. Download **Eve-Overlay-Evolved-v0.8.0-Windows-x64.zip** from the [release assets](https://github.com/bitsbetrippin/eve-overview-evolved/releases).
2. Choose **Extract All** into a fresh writable folder.
3. Double-click **START.bat**.
4. Select your characters and press **Play**. **SHOW PANELS** restores dashboards.

Windows 10/11 x64. Python, Tk and dependencies are included: no installer, PATH
changes or first-run downloads. Keep the subfolders together. GitHub's automatic
source ZIP does not include the runtime; use the versioned Windows ZIP to play.

## New in v0.8.0: every fight has a history

- **Automatic battle capture.** Dealing or receiving positive damage starts a
  fight. After **60 seconds without damage**, the app saves a local summary.
- **Your best target DPS.** The aqua panel has its own **Current / saved battle**
  dropdown. Review the highest single-target **15-second DPS** and target name;
  hover for the combined outgoing peak and total damage.
- **Who hit you hardest.** Battle Review below incoming damage selects the top
  three attackers by their individual **15-second peaks**, plus the combined
  incoming peak. Attacker peaks need not occur at the same time.
- **Cap pressure, included.** That incoming selector also recalls peak combined
  **GJ/s**, battle GJ lost, separate **NEUT / NOS** totals and the top drain sources.
- **EVE-time titles.** Each saved fight carries its UTC date and time range.
  Separate per-character histories survive restarts in **data/battles/**.
- **Review while you fly.** The two selectors work independently. Reviewing a
  saved battle leaves recording and the fleet's live DPS running. Choose
  **Current** to return either section to its normal display.
- **Local history management.** **Settings > PURGE SAVED BATTLES** clears the
  archive for all characters after confirmation. Active fights, settings and
  income-session history are preserved.

![Saved battle review with synthetic combat data](docs/images/battle-review-v0.8.0.png)

Saved peaks use EVE log timestamps, so a delayed batch is not counted as one
instantaneous burst. A peak is rolling damage or GJ over 15 seconds divided by
15, even for a short fight. Misses, EWAR and cap drain alone do not start or
extend a battle. Pause, Stop, Reset, Quit or suspended monitoring saves an active
fight as **[partial]**. No old gamelog damage is imported on startup.

## Your cockpit at a glance

| Feature | What you get |
| --- | --- |
| **Fleet overview** | Live target DPS beside every pilot, plus net ISK, ISK/hour and session time |
| **Aqua target DPS** | Bold rolling damage rate and the latest target hit; independent Battle Review |
| **Red incoming damage** | Three attackers ranked by recent pressure, with full identities on hover |
| **Amber capacitor drain** | Incoming neut + Nos loss, 15-second GJ/s, split totals and source rankings |
| **Spoken EWAR alerts** | Scrambled, Pointed, Webbed and Jammed warnings for your ship |
| **Recipient-aware sound** | Selected voice for personal threats; beep for logged other-target scram/point/web |
| **Five voice choices** | Robot, Commanding, Dramatic, News anchor and user-supplied SamL clips |
| **Adjustable alert gain** | Low 100%, Medium 200%, High 300%, with Voice / Beep / Off and preview buttons |
| **Fleet-friendly monitoring** | Keep tracking with dashboards hidden when Background Monitoring is enabled |
| **Make it yours** | Optional Initiative logo, themes, opacity, remembered positions and detachable panels |
| **Income and site tools** | Bounties, tax, clipboard loot valuation, session history, missions and anomaly timing |
| **Portable by design** | One START.bat launcher, bundled runtime and a separate local data folder |

![Fleet overview with synthetic data](docs/images/overview-v0.8.0.png)

The app is a passive log reader. It does not automate ship controls or read game
memory. Combat support uses English gamelog formats. Target DPS follows the
latest **hit**, not a selected lock; identically named NPCs share a damage bucket.
Jamming alerts require a confirmed personal jam record. Alerts report logged
events, not continuous effect duration. Public ESI prices require internet access;
combat history and bundled audio work locally.

## Folder layout and architecture

```text
Eve-Overlay-Evolved-v0.8.0-Windows-x64/
├── START.bat          Launch the application
├── README.md          Quick start and feature guide
├── app/               UI, log readers and metric modules
│   └── assets/        Icons, alliance logo and voice clips
├── runtime/           Bundled Python, Tk and packages
├── data/              Your settings and income-session history
│   ├── battles/       Saved battle JSON payloads, per character
│   ├── cache/         Rebuildable market/name caches
│   └── logs/          Startup and optional debug logs
└── docs/              User guide, release notes, credits and screenshots
```

Only **START.bat** and **README.md** are files in the release root. Source adds
`tools/`, `tests/` and `.gitignore`.

START.bat runs bundled Python in isolation. `app/startup.py` prepares paths and
starts `app/ratting.py`, which owns the Tk UI and incremental log reader.
`combat_meter.py` and `neut_meter.py` supply the live meters; the new
`battle_history.py` tracks event-time peaks and writes atomic battle payloads.
Separate modules handle EWAR audio, resource/data paths and monitor placement.

## Upgrade and keep your setup

Close the old app and extract this release into a **new folder**.

- From **v0.7.8 or later**, copy the old **data/** folder into the new release.
- From **v0.7.7 or earlier**, copy root `ratting_config.json` and
  `ratting_history.json` into the new **data/** folder before launching.

Legacy state beside START.bat is also imported when its new destination is
absent. Existing data and original legacy files are preserved. Your voice,
volume, logo, log path and window preferences stay with your settings.

Voice clips are in **app/assets/**; SamL is in **app/assets/voices/saml/**.
Startup failures are logged in **data/logs/startup.log**. Run
`START.bat --self-test` for portable-runtime diagnostics.

## Guides and release checks

- [User guide: controls, Battle Review and architecture](docs/USER-GUIDE.md)
- [What's changed](docs/RELEASE-NOTES.md) and [full changelog](docs/CHANGELOG.md)
- [Development and builds](docs/CONTRIBUTING.md)
- [Component notices](docs/THIRD-PARTY-NOTICES.txt)

Validated with **133 automated checks**, actual Tk windows, clean ZIP startup
without system Python on PATH, and legacy-data migration. Screenshots use
synthetic combat; live EVE sessions are not part of these automated checks.

**Contributions:** [@bitsbetrippin](https://github.com/bitsbetrippin).
**Original concept/base:** [Eve-Ratting](https://github.com/psychojf/Eve-Ratting)
by [@psychojf](https://github.com/psychojf). [Full attribution](docs/ATTRIBUTION.md).

Repository: [bitsbetrippin/eve-overview-evolved](https://github.com/bitsbetrippin/eve-overview-evolved).
