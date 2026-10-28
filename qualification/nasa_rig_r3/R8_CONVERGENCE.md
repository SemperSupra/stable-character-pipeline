# R8 — converge independently passing R6 camera-plane preview and R7 numerical oracle

Authority: [R6 #63](https://github.com/SemperSupra/stable-character-pipeline/issues/63), [R7 #67](https://github.com/SemperSupra/stable-character-pipeline/issues/67), original NASA source replay R5 #51, private product #2. **RESEARCH ONLY**.

## Problem: sibling branches changed one evaluator

R6 native candidate corrective [#71](https://github.com/SemperSupra/stable-character-pipeline/pull/71) and R7 numerical candidate [#68](https://github.com/SemperSupra/stable-character-pipeline/pull/68) are siblings atop R6 #65; both edit `qualification/nasa_rig_r3/blender_verify.py`. R6 previously sampled Blender 1 frame early/late relative to glTF 0-based animation while R7 numerically proved a 1/24s discrepancy before correcting it. R6 correction passed its own native real bpy4.5 replay and 10/10 raster equality; R7 passed native two independent readers and all indexed 192×10 positions, but retaining independent files as competing imports would drift. The native R6 path renders CPU Pillow polygons, not Blender Cycles.

## Minimal reconciliation

This stacked research branch is based on **R7 exact commit `666598b59a4eaf54bfb2a8092d4f014a22cbfab3`** and retains unchanged the independent glTF skin reader, numeric comparator, seven R7 negative controls, Go source GLB, original source rights and recipe.

It adopts R6's proven `frame_clock.source_aligned_frames(n,fps)` source-specific helper and five negative tests, emits the exact scene-frame indices and clock classification, and runs **both** source-proven native workflows (one R6 self-test + iPhone H264, one R7 two parallel independent 192-vertex readers + joined numeric comparison). Native frames must be [0,24,...,216] at 24fps. No automatic global rule for MMD VMD imports: those use different upstream clock origin behavior. No new upstream model/MediaPipe inference, identity/animal/physics/photoreal claims.

Independent acceptance requires both exact-head GitHub workflows terminal SUCCESS, original R5 source GLB and landmark SHA unchanged, numeric comparator `PASS_INDEXED_VERTEX_PARITY` under 0.0005 uncalibrated-unit tolerance, and R6 native 10-frame/H264/raster visual witnesses. FAIL retains first failure and blocks promotion. Public Actions artifacts are ephemeral and NOT substitute for source-controlled replay. Hold all merges/releases/deployments/private data/CPE promotions pending owner review.
