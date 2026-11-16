# R044 matched lighting stress: photorealism method qualification, not acceptance

This standalone **public synthetic** workcell extends validated R037/R039/R040/R043 render/EXR primitives without modifying their implementation or their existing workflows. It is a new, independent stacked draft workcell based on public R043 PR #537 SHA 81e315684d37239881167b5bbd8180d7f95e9f7e. DLE authority: private Stable Character R037 #176. The source is an original procedural *stylized* bust, not a source-admitted MakeHuman / private digital person.

## Experiment (predeclared)
Fixed mesh, orthographic camera, source pose, sample budget, objects and background. Compare baseline Principled BSDF vs conservative SSS+procedural microbump/roughness under:
- diffuse_soft: key 230 W, radius/size 5, fill 250 W, rim 150 W
- directional_hard: key 730 W, radius/size 0.45, fill 55 W, rim 350 W

The physical units above are Blender light parameters on an invented scene, not calibrated photometry or human tissue parameters. Each light condition builds one scene and renders both materials before discarding it. The model must keep mesh hashes and camera hashes identical in both arms and, independently, between conditions. Every treatment returns actual Cycles PNG/EXR, an unchanged source geometry/pose/camera receipt and an independent measured image difference; the R039 header and R040 official OpenEXR pixel decoder must verify object index and depth invariance. New independent manifest checker verifies pinned light values and source SHA, artifact SHA, positive finite numbers and 2x2 matrix completeness, with adversarial controls.

## Reproduce on an admitted disposable machine
Use Go 1.23+, Blender Cycles and official OpenEXR 3.3.3 + NumPy 1.26.4 (isolated venv; never global packages).

    python3 -m unittest discover -s lightingprobe -p test_verify.py -v
    (cd renderlab && go vet ./... && go test -race ./...)
    blender -b -t 2 --python lightingprobe/stress.py -- --out out
    # Reuse the exact Go and EXR decoder calls in .github/workflows/r044-lighting-stress.yml

## Interpretation / research gate
A passing 2x2 experiment proves **only** that material-only image changes survive two explicitly distinct light configurations while preserving scene geometry, camera, segmentation/depth and original source metadata. A higher changed-pixel fraction does not mean better photographic realism. No trained model, actual person, human owner preferences, anatomical validity, interactive game performance, temporal video or R009 film claim is made. Treat artifacts as short-lived public source-clean CI evidence; preserve compact numeric result and exact source SHA in private R037 DLE, not protected media or people in public CI. No paid/private Actions or local host modification.
