# Changelog

## v0.8.1 beta — 2026-10-03

- Add a README walkthrough for Settings, SamL voice, High (300%) alert gain and Apply.
- Add annotated overview/settings images with red boxes, arrows and numbered controls.
- Update release labels and documentation; retain v0.8.0 application behavior.
- Verify the tutorial images/links and rebuild the portable release with all 133 existing checks.

## v0.8.0 beta — 2026-10-03

- Add automatic per-character battle capture with a fixed 60-second damage-idle boundary.
- Record log-time 15-second peaks, totals, target/attacker identities and UTC ranges.
- Add independent Current/saved-battle selectors for aqua DPS and red incoming/cap panels.
- Save incoming neut/Nos combined and split battle totals, peak rates and source summaries.
- Persist atomic JSON payloads under data/battles/; skip corrupt records and retry failed writes.
- Save interruption summaries as partial; keep live fleet monitoring during history review.
- Add Settings archive count and confirmed purge, preserving active fights and income history.
- Rebuild README feature coverage, architecture documentation and UI previews.
- Add 24 focused battle checks (133 total) and verify the portable ZIP and upgrade path.

## v0.7.8 — 2026-10-03

- Leave only START.bat and README.md as files in the Windows release root.
- Organize application/assets under app/, guides/images under docs/, and source utilities under tools/.
- Store settings/history in data/, caches in data/cache/, and logs in data/logs/.
- Import legacy root state only when the new destination is absent; preserve originals and existing new state.
- Update startup, resource paths, audio utilities, build packaging and contributor documentation.
- Add five layout/path/migration checks (109 total), plus clean-launch and upgrade validation.

## v0.7.7 — 2026-10-03

- Detect personal ECM jams from the contributed `You're jammed by` combat format, preserving attacker identity.
- Activate the full SamL Jammed clip; add Jammed recordings and previews for the other four voice styles.
- Show personal JAMMED alerts with the EWAR color and pulse; preserve Voice/Beep/Off and volume settings.
- Suppress duplicate jam audio through the existing 10-second cooldown; ignore generic targeting failures.
- Extend personal queue expiry to 15 seconds for four full SamL alerts; nearby expiry stays 8 seconds.
- Add anonymized real-log fixtures and six new checks (104 total). Nearby/outgoing jam formats remain unverified.

## v0.7.6 — 2026-10-03

- Beep for scram/point/web events targeting another pilot, drone or outgoing target in the monitored log.
- Keep selected-voice alerts and personal visual warnings exclusive to events targeting the log's character (`you`).
- Give personal alerts priority over queued nearby beeps, with independent repeat limits.
- Preserve Beep-only and Off settings, volume gain and the preview-only Jammed placeholder.
- Explain sound routing in Settings; add ten regression checks (98 total).

## v0.7.5 — 2026-10-03

- Add SamL voice selection with four supplied recordings converted to 16-bit mono WAVs.
- Route SamL scrambled/pointed/webbed clips through existing gain and event handling.
- Include Jammed as an explicitly marked manual-preview placeholder, with no log trigger.
- Preserve full clip durations and keep all four queued manual previews from expiring.
- Five new regression checks cover imports, previews, routing and saved selection (88 total).

## v0.7.4 — 2026-10-03

- Low/Medium/High digital gain (100%/200%/300%) with peak limiting for voice and beep.
- Four offline synthetic styles: Robot, Commanding, Dramatic and News anchor.
- Preview and persist voice/volume settings; preserve Robot/100% for existing users.
- Queue captures the selected profile and settings changes discard pending clips.
- Eight new automated checks cover gain, limiting, style routing and persistence (83 total).

## v0.7.3 — 2026-10-03

- Optional Initiative alliance logo beside target DPS and above the fleet table.
- Bundled robotic voice warnings for scrambled, pointed and webbed events.
- Voice/Beep/Off settings with previews, serialized playback and repeat throttling.
- Fix false personal scram alerts from nearby/outgoing tackle; add point parsing.
- Apply background monitoring changes immediately to hidden dashboards.
- Twelve new automated checks for EWAR, audio and live settings (75 total).

## v0.7.2 — 2026-09-23

- Add a live per-character TARGET DPS column to the fleet overview (15-second window).
- Preserve separate overlay controls under OVL and saved column widths.
- Show explicit inactive/stale states; widen old overview layouts on upgrade.
- Default background monitoring on for new settings, preserving explicit preferences.
- Add real Tk regression coverage for hidden log reading, status and overlay clicks.

## v0.7.1 — 2026-09-22

- Include incoming Nosferatu in the renamed INCOMING CAP DRAIN panel.
- Combine neut/Nos loss in session GJ, rolling GJ/sec and source rankings;
  add separate session and per-source NEUT/NOS subtotals.
- Recognize negative `energy drained to` records as loss; exclude gains,
  wrong directions/signs and unrecognized color markers. Zero adds no loss.
- Preserve identical same-second records as separate activations while
  incremental reading prevents recounting them on the next poll.
- Keep history's neut-only fields; add Nos-only and combined fields.
- Add 12 regression checks and an anonymized 130-record mixed log fixture.
- Correct Pause documentation: existing resume behavior skips paused entries.

## v0.7 — 2026-09-22

- Add the amber INCOMING NEUTS dashboard panel with session GJ, rolling
  15-second GJ/sec and the top three sources by session GJ.
- Parse the incoming color-tagged neutralizer format, preserving source
  and module details; skip outgoing/ambiguous records and Nosferatu.
- Integrate Stop, Pause and Reset; retain neut totals and per-source amounts
  in session history JSON, including sessions with only neut activity.
- Add anonymized log fixtures and 16 neutralizer parsing/accounting/UI tests.
- Update architecture/layout documentation and portable packaging.

## v0.6.1 — 2026-09-22

- Open new dashboards beside the overview in a cascade, replacing the
  old default at the far edge of the desktop.
- Recover saved off-screen positions using current monitor work areas;
  preserve reachable positions, including negative monitor coordinates.
- Validate character placement after Tk maps the window, when its actual
  coordinates become available.
- Add SHOW PANELS to recover hidden, collapsed and misplaced dashboards
  plus existing detached sections, preserving session data and run state.
- Recover an off-screen dashboard when its character row is clicked.
- Add ten placement and complete-fleet GUI regression checks.

## v0.6 — 2026-09-22

- Renamed the product to **Eve-Overlay-Evolved**; versioned startup,
  window/tray titles, diagnostics and the Windows ZIP filename.
- Added shared product metadata in `app_info.py`.
- Credited @bitsbetrippin's contributions and @psychojf's original
  Eve-Ratting concept and base implementation.
- Rewrote the README with architecture, data flow, layout, controls,
  module responsibilities, development and upgrade instructions.
- Updated user, contributor and security guidance, support links,
  notices and release documentation for the fork.
- Preserved legacy config/history/cache filenames and debug-variable
  compatibility so previous settings can migrate unchanged.

## v0.5 — uploaded combat-meter update

- Added the bold aqua target-DPS panel and bright red top-three incoming
  attacker panel above the character-dashboard controls.
- Added 15-second named rolling totals, target switching, expiry,
  long-name hover details, Stop snapshots and Reset behavior.
- Expanded parsing for tagged/plain damage lines and decorated names.
- Added synthetic combat and real Tk widget tests.

## Earlier portable startup work

- Added START.bat, bundled Python/Tk and pinned app dependencies.
- Added isolated paths, startup errors and an offline runtime self-test.
- Added Windows redirected-Documents and OneDrive log discovery.
- Added a checksum-verifying release builder and startup/path tests.

Original concept/base: [Eve-Ratting by psychojf](https://github.com/psychojf/Eve-Ratting).
Evolved contributions: [bitsbetrippin](https://github.com/bitsbetrippin).
