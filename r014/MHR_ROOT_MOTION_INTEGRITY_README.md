# R014 MHR root motion and skin-hierarchy diagnostic

This is a **source-native 18,439-vertex / 126-bone** MHR v1.0.1 adult synthetic human research workcell. It addresses the observed failure of [actual gait retarget #446](https://github.com/SemperSupra/stable-character-pipeline/pull/446): model-space skin vertex displacement >17–23 native units despite a ~2.9-unit root trajectory and ankle target error ~0.6 units.

**Do not tune gait target geometry around that failure.** First isolate whether Blender is animating the proper rig root.

The experiment compares two independent immutable cloud source jobs:

- `object`: translate the armature **object** by 0.2 scene units with no IK, and verify that its skinned body moves rigidly.
- `pose-root`: translate the armature's existing **root pose bone** by 0.2 scene units with no IK, and verify the same property.

Both operate on exact SHA-pinned official MHR v1.0.1 public synthetic source, checksum-verified Blender 4.5.16, fresh Blender process reopened native FBX import, temporary GitHub Actions public ubuntu runners. Neither job includes private or identity media.

**Measured, not assumed:** root-bone actual world translation, all 18,439 actual evaluated body vertices against that translation, residual p95/max, rig parent relationships, 36,874 stable polygon-fan triangles, inversions/area collapse, zero-return restoration, actual native editable .blend and front-view neutral/translated PNGs. The source remains identical; outputs are numerical and technical images, no human realism or film claim.

If `object` fails but `pose-root` passes, then the full gait should retarget root translation to `root` bone pose instead of the armature object, with a *separate* static leg-IK feasibility gate and fresh-reopen evidence before 169-frame footage. If both fail, investigate parent inverse and skin bind/source matrices; do not widen ankle thresholds. If both pass, the leg-IK constraints are the likely distortion source, requiring independent IK solver tests and target-space calibration. This is a falsifiable decision tree, not a predetermined diagnosis.

DLE: [private R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138); [R015 #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141) controls semantic morphology mapping. Historical failed #446 artifacts are preserved. The PR must remain draft/unmerged. Free public runners only. R014/R009 video, anatomy and cinematic production acceptance remain HOLD.
