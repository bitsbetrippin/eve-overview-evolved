# Eve-Overlay-Evolved v0.8.0 beta

**Battle Review is here.** Keep the live cockpit, then revisit each engagement's
peak damage and capacitor pressure when the fight ends.

- Automatically save a battle after 60 seconds without damage dealt or received.
- Select Current or a saved fight independently for outgoing DPS and incoming damage.
- Review highest single-target 15-second DPS, top attacker peaks and combined incoming peak.
- Recall combined peak GJ/s, total neut/Nos loss, split totals and top drain sources.
- See UTC date/EVE time ranges; keep per-character JSON payloads locally in data/battles/.
- Purge saved battles for all characters from Settings, with confirmation and active-fight preservation.
- Save interrupted fights as [partial]; preserve history through Reset and app restarts.
- Keep recording and live fleet DPS while browsing an older engagement.

Saved peaks follow log timestamps, use a full 15-second denominator and keep
independent source peaks separate from combined peaks. Cap drain, misses and
EWAR alone do not start or extend a battle. Damage before Play is not imported.
Anomaly Site gap remains separate from the fixed 60-second battle boundary.

All fleet DPS, income tools, themes, Initiative branding, five voice styles,
100%/200%/300% alert gain and personal ECM jam alerts remain available.
The root still has only START.bat and README.md as files. The README now provides
a full feature checklist; the guide includes the new architecture and screenshots.

Extract the Windows ZIP into a fresh folder and run START.bat. From v0.7.8 onward,
copy your old data/ folder after closing the old app. From earlier versions,
copy root ratting_config.json and ratting_history.json into the new data/ folder.
Python and dependencies are bundled; GitHub's automatic source ZIP is separate.

Validation: 133 automated checks (24 new battle checks), real Tk dashboard and
Settings rendering, clean ZIP launches with no system Python on PATH, conflicting
Python/Tk environment settings and legacy-data import. No live EVE session is
claimed by these checks. Battle summaries remain local and user data is excluded
from the release package.

Contributions: @bitsbetrippin. Original concept/base: Eve-Ratting by @psychojf.
Repository: https://github.com/bitsbetrippin/eve-overview-evolved
