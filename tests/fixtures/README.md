# Neut log fixture

`incoming_neuts.txt` preserves the markup, amounts, event spacing and module
names from a contributed incoming-neutralizer log sample. Pilot names,
corporation/alliance labels and the date have been replaced. It includes
only the 20 neutralizer records needed for regression tests.

Expected totals: Pilot Alpha, 18 x 47 = 846 GJ; Pilot Beta, 2 x 140 = 280 GJ.
Combined total: 1,126 GJ. At the last event, the preceding 15-second window
contains 281 GJ (18.7333 GJ/s). Production rolling rates use arrival time.

Incoming direction is established by the amount's `0xffe57f7f` color marker.
Directionless text and other color markers are not treated as incoming.

`incoming_cap_drain.txt` adds the expanded mixed neutralizer/Nosferatu sample,
using the same anonymization. There are 44 neut records (42 positive) and
86 Nos records (75 positive); zero and negative-zero GJ cause no loss.
Expected totals: 2,307 GJ neut + 1,641 GJ Nos = 3,948 GJ. Pilot Gamma accounts
for 2,446 GJ (805 neut + 1,641 Nos); Alpha has 940 and Beta has 562 GJ.
The final 15-second window contains 32 GJ. Identical same-second lines are
preserved: multiple module activations must not be deduplicated by text.
Incoming Nos uses negative `GJ energy drained to` with the incoming color;
gains via `drained from` and positive amounts are excluded.
