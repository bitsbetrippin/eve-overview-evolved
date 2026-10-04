# v0.8.1 tutorial image provenance

The unannotated inputs are real Tk captures with synthetic pilot data:
`overview-v0.8.1.png` and `settings-v0.8.1.png`. Settings were captured after
selecting SamL and High (300%) and before Apply, so the Apply button is active.
The sample log path uses a fictional `Pilot` Windows user.

The annotated PNGs were created with the built-in image-generation edit tool
and visually checked against these inputs. The UI code was not changed.

## Overview edit prompt

Preserve the entire fleet overview and all UI text, controls, colors and positions.
Add a red box tightly around the upper-right gear, immediately left of X, and a
red arrow from a dark margin labeled OPEN SETTINGS. Exclude the X and diamond
from the box. Keep the full window visible; do not invent controls.

## Settings edit prompt

Preserve the entire Settings panel, text, controls, positions and selected values.
Add red boxes around the Voice Style dropdown (SamL), Alert Volume dropdown
(High (300%)) and green Apply button. Add a right margin with red arrows and
numbered labels: 1 Choose SamL; 2 High (300%); 3 Click APPLY. Keep EWAR SOUND
set to Voice and clearly visible. Keep the full panel, avoid overlaps, and do
not invent menus or change values.
