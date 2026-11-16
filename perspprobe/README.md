# R057 — Perspective camera ray-to-EXR depth verification

Owning photorealism experiment DLE: [private R037 #176](https://github.com/SemperSupra/stable-character-pipeline-private/issues/176). This is a standalone original-synthetic free-cloud research branch **stacked on** R045 [PR #556](https://github.com/SemperSupra/stable-character-pipeline/pull/556) exact source SHA `f8d863f04c72e5c28411e12c57091be360c31a17`. It changes only `perspprobe/` and its dedicated workflow, not the R037/R039/R040/R044/R045 owning code or protected Blender assets.

## Predeclared experiment

- One original procedural stylized 3D bust, unchanged scene/geometry/world camera transform throughout; real Blender Cycles CPU 256×256, 12 samples and source metadata.
- Two **perspective** focal lengths, 35.0 mm and 65.0 mm, native camera sensor width 36 mm, horizontal sensor fit, zero shift and 1:1 pixel aspect. Two material states (baseline vs synthetic SSS/microbump) at each lens, four real PNG + four actual multilayer EXR image files.
- Independent native `scene.ray_cast` pixel-center rays constructed from Blender's reported `camera.data.view_frame(scene=...)` in camera local coordinates, transformed by camera-to-world quaternion. Native source-mesh object index and Euclidean camera-to-hit distance are retained for each of up to 256 known points per focal length. Source-only ±1 pixel neighbor tests exclude silhouettes; at least 64 stable source points required.
- Independent official OpenEXR 3.3.3 pixel decoder compares actual EXR Z/object index to those source-native rays; **no fitted camera scale or depth offset**. The predeclared R045 numerical tolerances remain ≥98% joint ID+depth matches per image, depth absolute error ≤0.05 uncalibrated source Blender units, object-index absolute error ≤0.01.
- Strict fixture/rights, same-scene geometry digest, distinct camera SHA, exact 35/65 focal settings, no camera shift, bounded 2×2 matrix, no nonfinite rays, ray norms, no path symlinks, actual PNG/EXR byte SHA and physically changed beauty shading. Malicious fixtures intentionally tamper lens, camera shift, material or rights, depth NaN, object ID and pixel coordinates.

## Reproduction

See `.github/workflows/r057-perspective.yml`: standard **free public Ubuntu** runner, Blender CPU, only pinned NumPy/OpenEXR in an isolated environment, no private GitHub Actions, credentials, model downloads, server or proprietary input.

```
blender -b -t 2 --python perspprobe/scene.py -- --out out
python3 -m unittest discover -s perspprobe -p test_audit.py -v
python3 perspprobe/audit.py --root out --out out/r057_report.json
```

An actual failure is `HOLD` with the source/ray/EXR mismatch retained, not a reason to fabricate a camera transform or reinterpret data. The result `PASS_NARROW_PERSPECTIVE_SOURCE_RAYS_VS_REAL_CYCLES_EXR`, if observed, means **only** verified native perspective source geometry versus real rasterized Cycles depth/object semantics at two lenses for an original stylized fixture. It does not prove shading normal accuracy, moving humanoid skin/rig fidelity, real tissue physics, cinematic photorealism, owner preference, source rights of third-party assets or R009 MVP acceptance. All consequential canonical/owner gates remain private.
