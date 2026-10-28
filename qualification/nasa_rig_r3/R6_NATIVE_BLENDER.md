# R6 — Native Blender Python-wheel skinning round-trip

Authority: [public R6 DLE #63](https://github.com/SemperSupra/stable-character-pipeline/issues/63), parent source replay [R5 #51](https://github.com/SemperSupra/stable-character-pipeline/issues/51), prior source rig [R3 #43](https://github.com/SemperSupra/stable-character-pipeline/issues/43). Research-only draft, no merge/release/deploy/CPE/model promotion.

## Why this workcell matters

R5 [public Actions run 40591683857](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40591683857) reproduced original NASA independent photo/video and original MediaPipe Lite pose task, then generated a 10-second camera-plane skinned procedural GLB and mobile H264 MP4. Its independent Python glTF2 reader proved skin transform displacement; it **did not prove Blender itself can evaluate animation skin**. Previous R3 Ubuntu apt Blender successfully parsed the GLB but EGL crashed later; the distro Blender/Pillow dependency install also timed out. R6 uses a separate public CPU worker with the `bpy==4.5.0` Python wheel instead of apt or GPU-workbench rendering.

## Exact inputs and execution

- Read-only same-repository public R5 Actions artifact run 40591683857, expected GLB SHA256 `69a9869e21542dcdaade37f290c29b6d7217ae0e392f450aeb40efe00611ac6a`, observation JSON SHA256 `a6b56e7d794a5b74701031a75d350a9b2163182950861c1d135ec18b748c9b53`; source record independently recorded NASA original video/photo and pinned official model SHA. This convenience witness expires 2026-10-30; R5 direct original-source workflow remains durable and independently re-runnable.
- Standard public `ubuntu-24.04`, Python 3.11, wheel `bpy==4.5.0`, `Pillow==11.3.0`, `imageio-ffmpeg==0.6.0`. No `apt`, private runner or CUDA. One clean runner only; existing parallel matrix experiments are separate.
- Existing original `qualification/nasa_rig_r3/blender_verify.py`: actual native Blender import, armature and mesh modifier/vertex-group checks, animation actions and evaluated 3D mesh coordinates at source times 13–22 seconds, nonzero vertex displacement, 10 independent Pillow CPU-rasterized frames **from Blender-evaluated geometry**, type-tagged native readback receipt and 10-second H264 yuv420p/faststart MP4.

## Three audiences and honest limits

Humans can view the actual 10-second H264 on iPhone and inspect Blender-evaluated PNG/contact frames. Automation gets machine JSON with actual Blender version, armatures, mesh/weights/action counts, deformed endpoint displacement, number of PNGs and GLB SHA. Agents get exact source PR/ref, GHA native test/log, independent fixture source and next baton in #63.

This is **not native Blender Workbench/Cycles rendering**: Python Pillow rasterizes the actual Blender-deformed polygons without needing EGL. The original GLB was made with estimated source 2D x/y, z=0 and arbitrary units. Even if R6 passes, it does not recover metric 3D anatomy, face identity, human biological likeness, contact physics, learned inference or model transfer to characters.

No user/private models, unauthorized weights, source media, paid/GPU runners, changes to R1–R5 branches, merges, releases, deployments or CPE promotions. If the Blender wheel fails, preserve first native error rather than relabeling earlier glTF reader success as native Blender pass.
## R6 historical first-failure correction (2026-10-28)

The original R6 Python `blender_verify.py` used `frame_set(1 + round(i*fps))` while the Go-exported NASA GLB glTF animation sampler begins at scene frame zero (source-relative 0–9 seconds). This made the Blender evaluated mesh one native scene frame (1/24 s in 24 FPS) ahead of the independent reader at nine samples, with a measured max coordinate mismatch of **0.023531349636** arbitrary camera-plane units. Previous R6 rendered media is retained as historic evidence, not silently relabeled or overwritten.

The independent source-bound R7 [issue #67](https://github.com/SemperSupra/stable-character-pipeline/issues/67), [draft #68](https://github.com/SemperSupra/stable-character-pipeline/pull/68), [native GHA 40635188730](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40635188730) proved exact coordinate agreement on all 192 × 10 corresponding vertices after correcting the clock origin: max Euclidean mismatch **2.8510642335e-7** arbitrary units.

This owning R6 corrective **candidate** now uses the source-specific `frame_clock.source_aligned_frames(n,fps)` helper, anchored to zero. Unlike MMD VMD/MMD Tools, the NASA GLB itself has an independent 0-based glTF clock, so global "+/-1 frame for all Blender workflows" rules are explicitly forbidden. An independent `test_frame_clock.py` falsifies the old +1 behavior, bad sample count and bad FPS; native R6 receipt includes actual Blender scene frame indices, source zero and source-based mapping. All existing R5 hashes, private/public rights and preview classification are retained. A new exact-head R6 native success is required before treating regenerated PNG/MP4 as corrected; earlier output SHA and source rights are not erased. The native R6 job is only a Blender CPU evaluated-mesh preview (Pillow, not Cycles).

R6 code qualification does not constitute R009 original Naomi/Alison scene, full-body identity, realistic contact/IK, new model inference, GPU execution, release or merge acceptance.
