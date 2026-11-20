# N03D-AE — Actual-source held-out root versus leg factorial

**Authority:** public #662, numerical #650, private product R009 #23. Branch is stacked on N03D-AC #700, because true native 360x60Hz matched-source observations are a necessary input. AD reference #701 is independently executable.

## Research question
Which motion component—root, leg motion relative to pelvis, or their interaction—has the greatest explanatory power for lost source ankle/toe stationarity after the existing Diffeomorphic-to-MPFB retarget? This does not evaluate post-IK shoe physical behavior; it is an exact native-*observed* joint-position decomposition with alternative projected trajectories.

Train an exact SOURCE Hips X/Z -> target MPFB pelvis X/Y positive-scale+yaw+translation map using only the first 180 of 360 genuine native 60Hz samples; never fit the 180..359 heldout samples. For each side, decompose target bone foot WORLD = target PELVIS + (target FOOT - PELVIS). Independently take source ankle-to-hips local vector from original real 100STYLE and the train-only source-root similarity fit. Preserve the actual target's frame-0 foot-to-pelvis static rest-offset rather than pretending source anatomical joint centers are the same.

Four source-preserving factor combinations:
- original root + original local leg = measured MPFB foot HEAD
- mapped source-root travel + original local leg
- original root + mapped original source hip-relative leg *motion delta*
- mapped source-root travel + mapped source hip-relative leg motion delta

All four are computed in memory from immutable observed source and target traces. Target candidate paths are not Blender-actuated, do not satisfy 5-bone IK or ROM, and are not deformed shoes or valid stance. Score their 60Hz horizontal speeds only on the SAME heldout intervals pre-selected from original source ankle+toe jointly low/slow <=0.08m/s and within 20mm source-toe observed minimum. Evaluate p50/p95/max and first RED; no cherry-picked contact by target results. Source contact still UNKNOWN.

## Scope & next work
Real native pinned source, 2 fictional actors x 2 sides, 360 full clip at 60Hz, 2x2 full cross, heldout timestamps and independent hostility/rights/clock/false native-actuation controls; public free GHA CPU. If source-root factor changes outcomes, next implement physically constrained actual native 5-bone IK+root and remeasure real deformed shoe. An independent *external* retargeter implementation (e.g. Toyxyz) is separate and requires a source/license and dependency admission first; this study deliberately DOES NOT claim such comparative engine is executed.

PASS_NARROW means experiment correctness only. No Naomi/Alison/private source, private/paid runners, merge, production build or MVP acceptance. JSON-only short retention. Preserve all prior negatives.
