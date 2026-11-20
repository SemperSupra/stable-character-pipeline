# N03D-AB — 24/60Hz true native material-cohort temporal IK falsifier

**Authority:** public N03D P0 issue #662; R009 private MVP #23; Blender pin policy #669; source ancestry N03D-Y #696 -> AA #698. Draft research **not** source adoption or owner release.

## Question and preregistered design

AA established that keeping material vertex IDs fixed within a true native 3x3 IK Jacobian eliminated the worst moving-patch nonlinear prediction errors. This trial asks whether the local result survives the **time** axis, without mistakenly treating the lowest shoe patch as anatomical heel/toe or physical planted stance.

* Full 2 actors x 2 actual weighted shoe sides x 2 distinct windows (original 24Hz source samples 24..27 and 48..51). Both actors are **fictional** 163-bone MPFB rigs, each dressed in genuine pinned CC0 MakeHuman shirts/pants/shoes; source is pinned, explicitly licensed 100STYLE BVH retargeted by pinned GPL Diffeomorphic. No Naomi/Alison/private identity data on public runners.
* Hold the same underlying CC0 skinned shoe **vertex IDs throughout each four-frame window**, selected once at its opening actual native frame.
* Preserve source motion, current 163-bone topology, source root, unchanged garments. Introduce a **temporary, nonstretch, five-bone IK target** per shoe only; do not save corrected Blender/actions.
* At every 24Hz source frame build actual deformed shoe centroid-XY and fixed material-cohort min-Z 3x3 Jacobian with +/-2mm target probes. Compute one damped least squares correction capped at 10mm relative to the **current source foot**; the XY target is the first-frame cohort coordinate, and z target is ground zero. This is a forced *hypothesis* on a possibly swinging foot, **not** admitted stance or production motion.
* Replay the source and capped candidate independently at 24Hz and at **60Hz held-out interpolation samples** (7 regular 60Hz intervals plus the exact fourth 24Hz endpoint). Re-measure actual mesh partition min-Z, persistent shoe cohort XY speed, actual five-link pose rotation displacement, and extrapolated 24Hz model-gap bound. 60Hz bounds are conservative carry-forward, **not** independently measured 60Hz Jacobian accuracy.
* Independent stdlib hostile critic validates exact rights, source SHA/clock, complete factorial, all true-subframe evidence, finite numeric fields, nonzero material cohort, IK budget and source non-mutation. It reports penetration, sliding/unknown near-contact and other failures; **always HOLD** without source stance truth, anatomical foot labeling, joint limits and independent human/visual observation. Same workflow also runs inherited source/rights hostile tests.
* This is a **one-step-per-source-frame IK feasibility/falsification**, not yet nonlinear joint root+IK optimization, force-preserving contact, garment collision acceptance, or post-correction animation artifact.

## Interpretation and disposition

Comparison is admissible only when 2/2 public Linux jobs terminate success at the exact SHA and upload JSON-only provenance. Job success establishes **test execution**, not good gait. Check worst actual world-shoe penetration and 24/60Hz sliding against reference 10mm and 0.08m/s, heldout hover, IK pose change >0.35rad, actual nonlinear response gap >2mm, and whether controls improve. A window with no consecutive near-ground frames is UNKNOWN rather than PASS. All negative findings remain.

Next P0 if this trial rejects the candidate: replace forced-window anchors with independently verified 100STYLE source stance (source FK 60Hz + target 24Hz correspondence), mapped anatomical heel/toe support and a nonlinear constrained root + five-bone IK **temporally joint** solve. The independent sensor must verify post-IK skinned world shoes at higher-rate subframes. Until then both protected private R009 and public source-safe alternate MVP remain HOLD.

Free/public GitHub-hosted Ubuntu CPU only, SHA-pinned Blender 5.2.4 LTS; source/vendor/Blend ephemeral; compact JSON 3-day retention. No paid minutes, GPUs, private original data, merges, releases, or hidden version promotion. Human DLE + machine-readable JSON + automated agent fail-closed disposition serve the three audiences.
