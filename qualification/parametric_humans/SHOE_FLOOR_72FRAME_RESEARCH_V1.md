# R009 — shoe/ground floor falsifier (2026-11-07)

**Outcome: FIRST RED, source-original/CC0 research only. No gait, physical contact, root-motion, Blender, release, or CPE approval.**

## Authority and scope

Existing [R009 DLE #272](https://github.com/SemperSupra/stable-character-pipeline/issues/272) and draft PR #336. This is a scoped, source-only corrective instrument on the existing Aster/Juniper + CC0 MakeHuman research series. The exact *combined* Juniper armhole + pelvis/hip skirt-yoke candidate is pinned SHA256 `b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748`. Both 35-joint skeletons and 72 animation channels are preserved from the original source. No protected Naomi/Alison, private vendor material, or rights change.

## Measured first RED

`shoe_floor_contact_v1.py` independently reconstructs the glTF skinned shoe vertices through the existing CPU transform and linear-blend skinning evaluator. It uses the source-original Y-up world coordinate, floor at world `Y=0`, two separately enumerated feet per actor, and all 72 animation frames. Every row reports lowest sole-vertex Y, source vertex count, count below -1mm and below -5mm, and near-floor vertex count. A strict source SHA, joint count, actor names, clock continuity and no-overwrite check prevent accidental false passes.

| Metric | Aster | Juniper |
|---|---:|---:|
| Frames with one sole point below **-5 mm** | 72/72 | 72/72 |
| Lowest shoe point across sequence | **-13.16 mm** | **-13.14 mm** |
| Mean lowest stance shoe Y | -9.73 mm | -9.80 mm |
| Foot-frame observations with any point below -1 mm | 110/144 | 109/144 |
| Simulated all-frame root-Y correction needed to make *lowest* point touch zero | +7.38 to +13.16 mm | +7.49 to +13.14 mm |

The root-Y correction is **diagnostic only**; it has not been applied. Raising the rig to conceal shoe penetration without foot-roll, sole/contact friction, center-of-mass consistency, and native visual qualification could introduce foot sliding or implausible vertical bobbing. Footwear zero *body triangle crossings* in earlier research is not the same as absence of penetration into the *ground plane*.

## New fail-closed validator

`shoe_floor_gate_v1.py` is stdlib-only and validates all 2×2×72 source-bound shoe measurements, no missing or duplicate frame/side, finite positions, correct coordinate convention, integer count consistency and internally recomputed summary statistics. It separately rejects penetration below -5 mm and whole-body hovering above +10 mm, rejects forbidden root/nativity/approval claims, and never emits a physical contact approval. Tests include negative controls for missing/duplicated samples, stale source, nonfinite values, fabricated counters, faked native or release status, and floating feet. The first synthetic fixture had a stale `frames_both_feet_above_plus_10mm` value for its deliberately floating sample; corrected the fixture rather than weakening the validator. **14/14 source-free tests pass**; the actual 72-frame original-only receipt yields `RED_FOOT_FLOOR_PENETRATION` for both actors.

## Next independent workcell

Native Blender 72-frame sole-to-floor sampling with camera/ground axis validation, heel/ball/toe stance phase and contact-duration evidence, sagittal foot yaw and toe-off/heel-strike, terrain/friction controls, and actor-specific corrective motion hypotheses. Prefer explicit foot-lock/IK and phase-aware root-height refinement, not a single global elevation constant. Preserve source GLBs and source-anchored negative results; do not treat this CPU-only floor measurement as ground reaction forces, natural gait, or human visual acceptance. Branch parent-base SHA drift remains HELD; no merge/release/CPE.

### Reproduce

```bash
cd qualification/parametric_humans
python3 -m unittest -v test_shoe_floor_gate_v1
python3 shoe_floor_contact_v1.py --glb /path/to/approved-source-b92f7556.glb --out /tmp/shoe_floor_cpu72.json
```

Run the stdlib-only `shoe_floor_gate_v1.py` `gate()` over the complete receipt. Keep source GLBs and large frame-level measurements in owner-private Drive, and publish only compact source/test and false-approval-safe receipts to Git.
