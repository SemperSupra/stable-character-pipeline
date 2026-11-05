# Stance/swing world-target IK — isolated corrective

Owner authority: [Shetland DLE #293](https://github.com/SemperSupra/stable-character-pipeline/issues/293), parent source [#294](https://github.com/SemperSupra/stable-character-pipeline/pull/294), independent frozen hoof observer [#298](https://github.com/SemperSupra/stable-character-pipeline/pull/298).

Failed first hypothesis [#299](https://github.com/SemperSupra/stable-character-pipeline/pull/299) is closed UNMERGED with real 48-frame FAIL: 4/4 hooves insufficient lift. This experiment **does not simply rotate bones on another axis**; it authors a deterministic world-space four-foot trajectory, keeps intended stance ground X stationary while the body translates, uses a two-link Blender IK solver on each upper/lower leg chain, and bakes the evaluated constraints as ordinary pose tracks before GLB export.

Time: 48 frames / 24 fps, fixed frame clock and stride. Walk footfall sequence: hind-left, front-left, hind-right, front-right. Stance fraction .625, swing fraction .375, planned 10.5cm ankle lift. Units in meters; no global large-horse motion data, no user-uploaded photos/video, no third-party models. Black-only optional `SCP_COATS=black` for bounded native science; default still produces black/pinto/white.

**Uncertainties:** the 26-joint source itself is simplified, lower-tail target IK can make unnatural knees/stifles and still hover; source target is not evaluated foot-ground contact. Exported Blender visual bake must be proven in the independent source-frozen 48f observed skinned hoof geometry, and first failure preserved. Technical success never authorizes scientific PASS, visual promotion, a merge, release or CPE. Product work deferred until evidence.

Human: rendered PNG / GLB for inspection. Automation: source-only deterministic Python and immutable auditor. Agent: discover target plan, inspect exact synthetic source and measured receipt, suggest bounded next corrective; no unauthorized promotion.
