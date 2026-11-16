# R045 — native camera rays vs decoded real Cycles EXR (source-safe)

Private DLE authority: https://github.com/SemperSupra/stable-character-pipeline-private/issues/176. Stacked on public R044 draft #551 exact SHA 7bf4e4dccb6a0f10590a0cfee933e848a774e2aa, inheriting R037/R039/R040/R043. All sources are original public-safe stylized procedural geometry; no protected human person, private source, owner feedback or paid compute.

## Scientific question

Can decoded real Cycles depth/object-ID values be independently checked against source-native Blender scene mesh ray intersections and known fixed orthographic pixel geometry, rather than trusting pass-header declarations or paired scene equality alone?

The new Blender script executes the previous R044 two-light by two-material screen from the SAME Blender scene. It independently calls Blender scene.ray_cast for up to 256 predeclared pixel-center rays, including ±1px source-only neighbor stability to exclude ambiguous silhouettes. It binds the mesh/camera SHA, source code SHA, lighting config SHA, source-known object IDs, geometric surface normals and expected camera-forward ray length. The independent official OpenEXR 3.3.3 pixel decoder compares actual Z and ID arrays under all four rendered treatments. Thresholds predeclared: at least 64 stable source rays; at least 98% jointly correct against source at <=0.05 world-units Z and <=0.01 object index error. No empirical scale or offset can be fitted. Native source normals are captured but physical/shading normal correctness is NOT claimed.

The parent R037 Go image+source+digest, R039 EXR header, R040 decoded pixel and R044 multi-light treatments remain mandatory in CI. Negative test fixtures inject wrong depths, indices, NaNs, dimensions, duplicate JSON and insufficient source stable samples.

## Reproduction

Full bounded executable steps: .github/workflows/r045-ray-depth.yml

1. Start disposable CPU Blender and run: blender -b -t 2 --python depthprobe/trace_scene.py -- --out out
2. Run each upstream Go image/EXR header check under renderlab; run official OpenEXR pixel comparison in isolated venv.
3. python3 -m unittest discover -s depthprobe -p test_audit.py -v
4. python3 depthprobe/audit.py --root out --out out/r045_report.json

## Strict interpretation

PASS_NARROW_REAL_EXR_VS_SOURCE_NATIVE_RAYCAST proves only limited source-known geometry ray vs EXR-Z/ID agreement on original synthetic scenes, not anatomical realism, identity, physically correct surface normals, 3DGS, video, or actual human intent preference. No release, owner policy or canonicalization is authorized. Preserve the actual first RED in DLE without tuning away the difference.
