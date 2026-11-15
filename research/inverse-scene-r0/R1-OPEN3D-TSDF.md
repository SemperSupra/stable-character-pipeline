# R63 R1 — actual Open3D 0.19 CPU TSDF geometric reconstruction

**R63 authority:** [Oneirifact geometry/critic DLE](https://github.com/SemperSupra/oneirifact-private/issues/88#issuecomment-6899176131). **Data/fixture input:** stacked R63 [public numerical source branch](https://github.com/SemperSupra/stable-character-pipeline/pull/514) with original synthetic 3D living-room source scenes and exact cameras, metric z-depth and instance labels. This file and experiment introduce **real upstream Open3D 0.19 CPU**, not a reimplementation of its TSDF.

**Question:** What can a non-neural, scene-level, calibrated RGB-D geometric fusion backend actually recover with 2 views, with noisy depth and missing pixels, and with increased view coverage? How does its *actual exported triangular mesh* compare with source-known 3D render/depth against withheld views? This is a strong geometry comparison and a possible external adapter for editable feature graph priors, but TSDF itself does not provide semantic parts, materials, joints or an Oneirifact graph.

**Source documented upstream:** [Open3D official RGBD Integration 0.19](https://www.open3d.org/docs/0.19.0/tutorial/pipelines/rgbd_integration.html) and [ScalableTSDFVolume 0.19 API](https://www.open3d.org/docs/0.19.0/python_api/open3d.pipelines.integration.ScalableTSDFVolume.html), [source](https://github.com/isl-org/Open3D). The CPU-only official PyPI `open3d-cpu==0.19.0` is pinned, with `numpy==2.1.3` and `pillow==11.1.0`. All model dependencies use public original synthetic camera RGB/depth; no pretrained weights, private code, actual persons, GHA private or paid runners.

## Executed experimental protocol (receipt decides status)

For both R63 source scenes, integrate 48×48 real analytic ray-traced RGB and optical-axis depth in meters using Open3D `RGBDImage.create_from_color_and_depth(depth_scale=1)`, `PinholeCameraIntrinsic`, `ScalableTSDFVolume(voxel_length=0.045m,sdf_trunc=0.135m,RGB8)` and exact world-to-OpenCV extrinsics. `extract_triangle_mesh()` is an actual upstream marching-cubes mesh; save PLY with original code. Use Open3D **tensor RaycastingScene** to predict heldout source silhouette and metric z-depth from triangle mesh, no custom fake mesh rasterizer.

| Protocol | Integrated source frames | Evaluation |
|---|---|---|
| **train_two_clean** | Views 0,1 | Views 2,3 never integrated: genuine withheld camera geometry |
| **train_two_noisy** | Same views 0,1 with seeded 0.025m Gaussian metric depth noise and ~10% depth dropout | Same genuinely withheld 2,3, tests noise/dropout geometry sensitivity |
| **four_views_upper_bound** | All 0,1,2,3 | Views 2,3 **included in fusion**: coverage/overfit upper-bound control only; do **NOT** report as heldout |

At least 2 source scenes ×3 protocols = **six actual Open3D TSDF integration/mesh extractions**, separate PLY and sha256 receipts; per scenario record triangle and vertex count, watertight/edge-manifold flags, two view mask IoU, shared ray-hit metric-depth MAE, false positive/negative source foreground counts, wall seconds and max process RSS. These are geometry/coverage/correct camera tests, not raw RGB/texture fidelity or semantic object count. **Low 48×48 input resolution** limits geometric fidelity; selected TSDF voxel/truncation must be treated as one parameter point, not optimized.

**Important negative gates:** incorrect camera/frame/metric depth conventions must make the output fail; empty or nonfinite mesh is RED, not report PASS. Marching-cubes mesh of two partial views can be non-watertight without being a test harness failure, but that limits collision/printing claims. A successful whole-scene fusion does not mean semantic instance separation or a procedural Oneirifact param fit has occurred.

**Execution:** free GitHub-hosted `ubuntu-24.04`, source-only and read token, 12-minute timeout, 3-day artifact retention, no paid/privacy changes. Run `python3 research/inverse-scene-r0/open3d_tsdf.py` after pinned pip installation (see workflow `.github/workflows/r63-open3d-tsdf-cpu.yml`), inspect `OPEN3D_TSDF_REP`, `OPEN3D_TSDF_FINAL` and `receipt.json`.

**Next comparison:** choose realistic source RGB-D resolution and coverage/noise treatment before comparing future PyTorchGeoNodes, Mira-Scene or pretrained single-image methods. Never equate Open3D TSDF mask IoU with Oneirifact parameter/graph recovery; benchmark different capability axes in one multi-axis matrix, not one false rank.
