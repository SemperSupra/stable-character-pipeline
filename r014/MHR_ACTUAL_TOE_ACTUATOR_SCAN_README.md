# R014 actual native MHR ankle-preserving toe actuator sensor

Research source-only independent of rejected foot IK orientation #459/#460, stacked on canonical R014 pelvis-corrected actual full human gait [#458](https://github.com/SemperSupra/stable-character-pipeline/pull/458).

**Problem**: Actual signed Go 169-frame source retarget to native 126-bone MHR adult synthetic rig yields nearly exact planted ankles (max world error .000126), zero sampled inverted skin triangles, but planted ball-head translation up to .149 left/.084 right world units between consecutive frames. Native IK target rotation #459 sacrifices ankle accuracy, and separate foot CopyRotation #460 does not materially reduce ball slip, occasionally inverts skin triangles.

**This workcell** uses exact public GHA source run #43301146695 native Blender file, exact pinned Go source run #43246188313 contact sequence and independently verified internal SHA hashes, fresh reopened in checksum-verified Blender4.5.16. Two independent public CPU jobs each take left/right MHR leg:

1. Reconstruct all 169 saved animation frames. Identify the actual most slippery successive pair with both frames in contact from Go source rather than guess a contact frame.
2. For the worst second frame, capture unchanged ankle, ball head and ball tail world positions and inspect three real skeleton bone actuators: foot, transversetarsal and ball.
3. Sweep 3 source local Euler axes x +/-0.06/0.12/0.24 radians (54 true skinned positions per side). Measure ankle displacement relative to unmodified frame; ball head and tip movement; remaining ball-to-prior-stance world displacement; all 36,874 stable polygon-fan triangles for inversion/area collapse and all 18,439 world-space skin vertex displacements.
4. Emit a qualifying static frame candidate only when ankle changes <.002 Blender world units, no sampled inversions/collapse, and toe head error genuinely improves. Save actual held Blender scene, one source Cycles pose PNG, JSON and SHA receipts.
5. Do not extrapolate single-frame static correction into a full gait controller. The purpose is to learn whether a native foot/child bone can move the toe without losing ankle. No invented physical units, age/sex/body type inference, human biomechanics or cinematic claim.

All outputs 7-day staging in public GHA, durable assets archived separately in private Drive. No protected identity media, no private paid runner minutes or persistent host changes. Authoritative private [R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138), independent R015 #141, R009 #23. Draft/unmerged, product HOLD.