# R014 / Motion S3 preflight — measured CMU source named-leg roles vs actual MHR v1.0.1 rest skeleton

Both [GHA #43383274016](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43383274016) source-metadata-only jobs SUCCESS on original 07_01 and 07_02 metadata. Reopened exact SHA-pinned original public MHR v1.0.1 FBX 126-bone, 18,439-vertex human, verified 0.01 armature scale, compared named CMU femur/tibia/foot/toe source roles with native `l/r_upleg`, `l/r_lowleg`, `l/r_foot`, `l/r_ball` rest bone heads. No CMU original raw clips/ASF/AMC imported here; source from SHA-verified GHA S2 original FK profile only.

| Segment | Original CMU07 source, left | Original native MHR target, left |
| --- | ---: | ---: |
| Hip to knee | 0.390856449 publisher metres | 0.419764916 Blender world units |
| Knee to ankle | 0.417975191 publisher metres | 0.420582994 Blender world units |
| Ankle to toe proxy | Not independently reported as contact anatomy | 0.147916161 Blender world units |

Source/MHR upper-lower ratio-of-ratios L1.0673028, R0.9945201. Native target original bilateral geometry leg lengths virtually symmetric. Both source clips share subject-specific ASF rest source. Numeric ratio-of-ratios are comparison only; these do **not** calibrate MHR stature, sex/age/fat, actual human joint coordinate systems, or accept motion/source-to-target retarget.

CI HOLD named `PASS_NAMED_REST_ROLE_SPANS_ONLY_NOT_NATIVE_MOTION_RETARGET`. Original source all-joint Go/Python FK parity [public PR #484](https://github.com/SemperSupra/stable-character-pipeline/pull/484) and native source metadata S2 [#469](https://github.com/SemperSupra/stable-character-pipeline/pull/469). R014 geometry #138 and R012 original-human data #35 remain independent gates. W07 `scp.walk_motion.v1` is specifically **2D synthetic/72-frame**, not an implicit 3D ASF carrier; a versioned 3D adapter requires W07 owner crosswalk, transform/clock proof, source ingestion grant, true MHR 3D animation witness, contact/ROM/skin and cinematic human review. Research-only draft/unmerged. All evidence ZIP CRC+internal SHA verified; original human source rights never copied into a public asset.
