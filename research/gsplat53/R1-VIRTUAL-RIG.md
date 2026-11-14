# R1 virtual capture: native rig authority vs source-known Gaussian appearance

**Product science authority:** [Stable Character R034 #169](https://github.com/SemperSupra/stable-character-pipeline-private/issues/169#issuecomment-6883578932). Shared source-agnostic DOE: [Model Mechanisms #1](https://github.com/SemperSupra/model-mechanisms-private/issues/1#issuecomment-6883579500). Source-safe public implementation: this directory, stacked on source [Blender R0 PR #507](https://github.com/SemperSupra/stable-character-pipeline/pull/507).

## Invariants / architecture decision

When a model already exists with known geometry, rig, materials and animation, **the native 3D source is the authority**. Gaussian splats, SH or neural radiance are optional *appearance* or unknown-source *reconstruction* representations. They are not a required intermediate for morphologies, body rigs, garments, paint, UVs, soft tissue, collision or print geometry. Reconstructing a known model from its own renders is a **qualification exercise only**, not the production path.

Separate **semantic/source control Q1** (what parameters actually change geometry, rigging, behavior and materials) from **render advantage Q2** (does a learned appearance channel improve held-out photorealism, edit consistency or compute at frozen native truth?). This R1 only tests the **data/control substrate** required to ask Q1 and Q2; it is NOT a trained Gaussian reconstruction, optimized splat, comparable PBR appearance/material, soft-tissue or human model bakeoff. The native mesh is a source known ground-truth geometry control, and sampled splats are deliberately *unfitted*.

## Actual crossed experiment

**Source:** Original two-link rectangular articulated object (joint axis world Y, 0.56m per link, dimensions xyz = 0.56 x 0.15 x 0.18m). A rigid upper link and a lower linked segment pivot about world origin; this is an analytically posed procedural hinge, **not** a Blender Armature or deformable skinning rig. No human asset, third-party dataset/model/checkpoint or weights. Native Blender cubes have verified exact source-world vertices; Gaussian PLY is deterministic *samples of that exact known source surface* (204 per pose, source order/attachments stable); quadrature/resampling, not learned reconstruction. Each PLY uses original 17 standard binary Gaussian fields; normal, color SH-DC, positive log-scales, sigmoid-opacity, unit quaternion.

| DOE factor | Treatments | Grounded control |
|---|---|---|
| Geometry representation | Native MESH vs imported native GAUSSIAN_SPLAT POINTCLOUD | Same source geometry, pose, camera and edit |
| Skeleton/pose | 0°, 45°, 90° lower hinge Y rotation | Analytic lower endpoint `(L cosθ, 0, -L sinθ)`, exact world mesh vertices |
| Material/appearance edit | Default lower blue vs lower green | Explicit RGB material reference; SH-DC values on splats **not PBR** |
| Viewpoint | Front vs oblique | Exact camera-to-world and world-to-camera matrices; orthographic 1.75m |
| Frame clock | Index 0,1,2 @ 24 FPS | Exact source time and pose truth |

Total **2 representations × 3 poses × 2 material treatments × 2 cameras = 24 real RGB/alpha PNG renders**, plus 6 distinct Gaussian PLY payloads (one per pose × paint, reused across both cameras) and 12 view-scoped ground-truth JSON records. For each matched scene, record alpha IoU, mean absolute image difference (informational only), alpha centroid, render time and SHA256, source exact vertex/joint truth, raw camera matrices and per-frame clock. Cross-compare image response to pose and repaint, and PLY deterministic digest. **Do not interpret image RGB error/IoU as a learned splat quality ranking**: there is intentionally no splat training, parameter budget/optimizer alignment, photometric calibration or physically equivalent PBR material on the splats.

Positive oracles: native mesh world vertices match exact source within 5 decimals; Blender 5.3 POINTCLOUD/GAUSSIAN_SPLAT actual import; 24 nonempty finite renders; both representations visibly respond to pose and material; finite valid alpha overlap; 12 pairs/12 source states; reproducible source PLY generation; 204 constant Gaussian slots across pose and repaint. Negative controls: invalid pose/paint refused; deterministic hashes; byte-length/nonfinite/quaternion checks; no silent pose/paint no-op.

**Scope limitations:** Orthographic view is precisely known but does not exercise perspective calibration; source geometry acts as an opaque proxy, not deformable skin/tissue or actual human body. The camera does not need SfM/COLMAP because native camera matrices are authoritative. Per-vertex geometry/normal/depth may be deterministically computed from the source, but **this version archives RGB+alpha and exact mesh vertices/camera transforms only**; depth/normal image passes require another explicit experiment. Due different shading (mesh PBR-like vs Gaussian SH-DC), RGB scores are exploratory. The image comparison cannot claim a Gaussian learning/disentanglement advantage.

## Execution and next test

`python3 research/gsplat53/rig_fixture.py` validates original source geometry, poses and PLY controls. Blender 5.3.0 with published SHA256 and mirror failover runs `BAKEOFF_OUT=out/gsplat53-r1 blender --background --factory-startup --threads 4 --python-exit-code 1 --python research/gsplat53/virtual_rig_r1.py`. Actual CI is `.github/workflows/gsplat53-virtual-rig-r1.yml`, standard **free public** `ubuntu-24.04` CPU, read-only, 18-min timeout, short-lived artifacts; source receipts summarized into DLE for durability. No paid/private runner minutes, secrets, restricted human files or trained model checkpoint.

**Next R2 admission:** Use exactly the same known rig/pose/camera scene, split front training and oblique held-out views; fit Gaussian appearance only to training RGB, with frozen source geometry/skin weights and matched compute budget; compare PSNR/SSIM/LPIPS, holdout color/pose/lighting/temporal invariance, material edits and speed; compare native Blender PBR and learned appearance under identical optics. Introduce a texture/lighting nuisance and non-target edit control. If no measurable advantage, preserve the native renderer alone. Only then attempt rights-admitted full human/MHR/Anny/MPFB/cloth and scene compositing experiments. Shared method-neutral B1 DOE adapter required for canonical integration; this R1 is a scientific standalone, not a competing new production DSL.

Independent exact-head review and acceptance required before merging; no owner manual review gate.
