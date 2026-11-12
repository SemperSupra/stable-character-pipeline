# R014 actual MHR foot orientation and toe-contact bakeoff

This is a **four-job research factorial** using actual original MHR v1.0.1 18,439-vertex source mesh, 126-bone rig, native foot 3-link IK, real 169-frame Go world-contact trajectory and independently justified bounded pelvis-height reach controller from the stacked source [PR #458](https://github.com/SemperSupra/stable-character-pipeline/pull/458). New source is public synthetic, no protected likeness or private runners.

## Why this experiment exists

The latest real model run [43301146695](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43301146695) established near-exact planted ankle position (<0.00013 world coordinate units), no inverted/collapsed triangles in five canonical poses and no unreachable foot targets. But ball/toe proxy movement between consecutive contact frames reaches 0.1494 world units left / 0.0843 right. The pelvis height preplan also jumps by up to 0.0504 per 24fps frame: both remain biomechanically unacceptable. Full gait production HOLD.

## Four independent test jobs

**Coordinate-safe Blender IK target rotation** is a supported source-native operation (KinematicConstraint.use_rotation), not a new AI model. Preserve each original foot-bone world quaternion. Across 169 frames independently on neutral and opaque shape_20 morph variant, test:
- world-fixed: hold source foot orientation fixed in world during both swing/stance. Strong diagnostic for foot spinning; swing may look unnatural.
- stance-hold: freeze a foot's initial target orientation during each explicit Go contact interval while the swing foot tracks root heading, allowing turns but risking transition snaps.

All jobs preserve exact source-foot world location targets and objective contact/ankle/toe residuals, root/foot native scene, full 169-frame animation, five true CPU Cycles poses, native Blender source and machine receipts. They may fail; green workflow just means data collected.

## Promotion gate

Require planted ankle AND toe motion within verified bounds, realistic orientation/cross-frame continuity, source calibrated knee/ankle ROM, heel/ball/sole contact and no mesh inversion/area collapse at sampled poses, then natural pelvis motion and human visual approval. The actual ball head is only a toe proxy, **not** a plantar contact or collision mesh. No 1080p/4K photo-real skin/eyes/hair, soft tissue, adult anatomy completeness, or footage acceptance from this batch.

Private [R014 owner DLE #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138); independent R015 morphology #141; R009 film #23. Draft/unmerged, no secrets/private minutes/host contamination; Drive custody after independent check.
