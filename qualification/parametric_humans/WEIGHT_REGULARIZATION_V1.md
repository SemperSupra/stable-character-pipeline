# R009 MakeHuman 35-joint weight regularization v1 — research only

## Source and custody

- Inputs are source-hash-pinned project-original Aster/Juniper and MakeHuman official CC0 body.
- Body already aligned to source-original experimental 35-joint rigs and 72-frame animation in v0.
- New operation: 4 iterations of bounded alpha=0.5 adjacency Laplacian applied to each body’s 35-dimensional joint-weight probability distribution, matching coincident UV-seam vertices without merging geometry. Retain four strongest influences and renormalize.
- Appends new skinned attribute accessors; does not modify or delete the source binary prefix, original geometry, 35-joint armatures, wardrobe, materials or motion.

## Executed / independent controls

- Python source-free and actual-source adversarial tests: 9/9 pass.
- Complete 72-frame CPU linear blend skinning comparison across both actors: all 72/72 frames show lower p99 edge stretch and lower severe (>50%) edge-strain fraction, separately for Aster and Juniper.
- Signed body/garment contact in rest and four selected animation frames: garment penetration persists and remains a first scientific failure.
- UV seam weight continuity, normalized nonnegative 4-influence weights, 35-joint index limits and binary-prefix immutability independently asserted.
- Official Blender-native post-transfer evaluation: NOT_RUN. Physical cloth simulation: NOT_RUN. Face/expression realism: NOT_QUALIFIED.

## Stage-specific holds

- Does not establish correct anatomical skinning; synthetic test movement is not natural human locomotion.
- Aster masculine form still provisional: official MakeHuman male/female morph geometry must be source-pinned, composed and visually audited before any realism claim.
- Juniper torso and outfit bodice clipping substantially fails signed-distance QA. Full 72-frame cloth collision required.
- This ZIP belongs in owner-private Drive; tested source and concise evidence belong in existing public draft PR #336 and DLE #272. No merge/release/branch deletion.

## Reproduce

With NumPy, SciPy, trimesh, project-original companion code (`costume_garment_v1.py` and `sculpt_human_v1.py` in original public PR) and exact source-bound candidate GLB:

```sh
python -m unittest -v test_weight_transfer_regularize_v1
python weight_transfer_regularize_v1.py --candidate-glb aster_juniper_makehuman35_candidate_v0.glb --out-glb /tmp/regularized.glb --receipt /tmp/regularized.json
python observe_makehuman35_motion_v0.py --glb /tmp/regularized.glb --out /tmp/regularized_motion.json
python observe_makehuman35_garment_v0.py --glb /tmp/regularized.glb --expected-sha256 $(sha256sum /tmp/regularized.glb | cut -d' ' -f1) --out /tmp/regularized_garment.json
```

The original broad research producer `retarget_makehuman_v0.py` requires the CC0 body-only OBJ and pinned costume source; it is included in this bundle. No protected real-person model sources are required or included.
