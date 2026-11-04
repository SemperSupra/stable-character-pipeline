# R009 native MIT park motion candidate V2 — disjoint corrective source workcell

Controlling public DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/272. Protected original Naomi/Alison product owner: private R009 #23. This new-path workcell is based on **frozen public source producer #282** head 7a4c8f16a55cd6c1abcd0a62ba45509d0709d49f without modifying its camera/park owner files, and uses existing #274 immutable native MIT 80-bone source Blender SHA256 2e5c5fcc826c95d200b06cc2dcd22138944102426a86f1f683689ae458aff7ab.

## Hypothesis and controlled A/B

The earlier genuine H264 technical pass used 1.15Hz repeated pure local-axis oscillations with constant-speed roots; the six visually inspected old frames show stiff gait and tiny figures. Isolated source variant V2 explicitly replaces **only** the 72 source-keyed root X and 10 verified original bone local-X channels, easing root velocity in/out and tying 3.2 motion cycles to source travel rather than wall-clock. Changes include alternating thigh/arm pairs, swing-only calf flexion, ankle rock and start/stop amplitude taper. The original MIT source static rig, actor IDs, source UVs, six MIT body/head/opacity textures, camera framing correction and authored park geometry are reused unchanged. It does not infer anatomical coordinate systems or add synthetic sole ground truth.

This is a **research candidate**, not an asserted biomechanics improvement: increasing realism, preventing foot skate and respecting signed JCS/ROM require actual original source-dependent native geometry and independent decoded-film visual comparison, not self-certified authored keys. No source-derived animation is represented as human captured gait.

## Evidence ladder

1. Public standard $0 GitHub Actions, no secrets or private runner: nine adverse/structural tests, previous MIT material and original park tests, SHA256 for prior original source archive/Blender and all six official upstream MIT texture Git blobs, Blender 4.5.15 verified release.
2. Native Blender: read actual 80-bone source armatures with exact root names, require ten original named bones and 72 observed evaluated root states (rather than trusting the authored curve count).
3. Render actual native-source skinned characters using original MIT colors, Cycles front/oblique 72 x 12fps PNG sets, source-hash manifest, two H264 videos with 72-frame ffprobe verification and six human-review PNGs.
4. **Independent next consumer**, not the producer: compare decoded V1 vs V2 same-frame actor visibility/relative size, camera crop and foot/limb appearance, then inspect 72-frame heel/toe-ground native mesh witness. Retain first RED. Green source CI alone is no quality admission.
5. Keep original V1 PR #282 and its concurrently owned staging correction unchanged; after full visual+physical review, owner integrates a demonstrably improved variant or closes this experimental candidate with exact evidence and preserved source.

## Boundaries

Project-authored park plus pinned upstream MIT Rocketbox only. Raw third-party texture/FBX bytes are not committed as code or uploaded as source in artifacts; Microsoft copyright/license notice maintained. Protected Naomi/Alison binaries, identities, owner Drive IDs, private runners and commercial source grants never enter this workcell. Three audiences: human source/film/contact sheet; automation CLI/tests and re-run workflow; agent JSON, SHA identities and fail-closed product_accepted:false, true_foot_contact:UNKNOWN, signed_human_rom:NOT_RUN. No branch deletion, merge, release, deployment or CPE promotion authorized.
