# Security policy — Eve-Overlay-Evolved

Include the application version and source commit when reporting a
problem. The currently documented release is **v0.6**.

## Application boundary

- Reads EVE Gamelogs and local JSON settings/history/caches.
- Reads clipboard text for loot valuation when CLIP is unlocked.
- Requests public ESI market and item data; no EVE account keys are needed.
- Writes app state beside the script and uses bundled Python in the
  portable Windows release.
- Does not read EVE process memory, inspect game network traffic, modify
  the game client or automate in-game inputs.

The release builder downloads official Python and dependency wheels,
verifies the runtime SHA-256 and enforces pinned wheel hashes. End-user
startup does not install packages or download a runtime.

Settings/history can contain character names, local paths and activity
details. Redact these before sharing diagnostic material.

## Reporting

Report vulnerabilities to the maintainers of
[bitsbetrippin/eve-overview-evolved](https://github.com/bitsbetrippin/eve-overview-evolved),
not to the original project's author for changes made in this fork.
Use the repository's private vulnerability-reporting channel if enabled,
or a private contact channel provided by its owner. Do not post credentials,
private logs or a working exploit in a public issue.

Include impact, version/commit, reproduction steps and a minimal redacted
sample. Issues of interest include untrusted log/clipboard execution,
unexpected file access, state corruption and unexpected disclosure through
network requests. Ordinary startup and UI bugs belong in the issue tracker.
