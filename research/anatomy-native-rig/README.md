# R036 — Native MPFB hm08→anatomical binding vertical slice

**Purpose:** Execute a real headless Blender scene built from the exact pinned MakeHuman/MPFB hm08 base OBJ, using a deliberately tiny **original diagnostic** 2-bone rig with skinned mesh, three entirely synthetic organ *proxies*, shared timeline, render toggles, animation frames, native save/reopen and GLB skin verification.

**No photoreal/anatomical success claim.** This is *not* the upstream MPFB native human rig, licensed medical organs, production topology alignment, anatomical IK, muscular or FEM physiology. Do not confuse this source geometry (real MakeHuman base) with mature native character integration; first acceptance requires attaching registered anatomy to an actual MPFB rig, preserving real motion and shape controls.

## Rights and provenance
- Upstream MPFB version: `makehumancommunity/mpfb2` commit `9de0707fdc88438d7c53a1a2ac7937d9221e2431`.
- Single downloaded file: `src/mpfb/data/3dobjs/base.obj`, Git blob SHA-1 `d26635e9326e3cca30778fd7b9c00062b03cce09` according to GitHub file API observed from upstream master. Download by pinned commit and require an exact Git blob match. Do not publish/rehost downloaded OBJ.
- License sources: https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md and LICENSE.ASSETS.md. MPFB labels its core generated assets CC0; GPL-licensed source code is separate. This experiment directly uses only the one core base OBJ, not third-party community add-ons, human scans, donor assets or textures.
- The diagnostic anatomy proxy meshes and rig created by this script are entirely original and **non-medical**. No named-person identity data is present.

## Execution
Public GitHub Actions free-tier Linux/CPU Ubuntu installs distro Blender in a bounded job and runs:
```bash
# after source pin / rights preflight:
blender -b -t 2 --python research/anatomy-native-rig/native_vertical_slice.py -- --phase build --base "$RUNNER_TEMP/base.obj" --output "$RUNNER_TEMP/r036"
blender -b "$RUNNER_TEMP/r036/mpfb-anatomy-diagnostic.blend" -t 2 --python research/anatomy-native-rig/native_vertical_slice.py -- --phase verify --output "$RUNNER_TEMP/r036"
```
It verifies actual evaluated vertices and one organ deform at frame 24 versus frame 1; visibility-only switching doesn't change external body deformation; native Blender scene survives a different process and GLB contains a skin and multiple meshes. Three original rendered PNGs and serialized assets are created in ephemeral runner scratch; *none are published or stored in public CI artifacts*. Logs retain only SHA256, counts and bounded receipt. The next stage must independently review visual outputs in a **rights-approved** evidence venue.

## Next qualification waves
1. Replace two-bone dummy with the actual MPFB rig, official base skin-weight mappings, body morphs, organ anchors and validated anatomical rest-space frames.
2. Register real admitted atlas structures to the MakeHuman rest body, with spatial and temporal mapping under shape/pose changes; capture native metrics and cutaway image pairs.
3. Compare Blender-native corrective skinning vs MyoSim/OpenSim muscle-driven and SOFA/ArtiSynth soft-tissue corrections using the same real rig/animation and visual oracle.
4. Layer scene/simulation/selection via an accessible DOM tree + keyboard/AT, CLI and agent tool discovery. Export game/film LOD profiles with independent reimport/normal/UV/material and animation QA.

All work remains **draft**, non-product, and separate from R009 release holds. No merge/deploy/publication/acceptance follows from CPU smoke.
