# W04 genuine Babylon WebGL diagnostic visual proof — iPhone-readable

**Authority:** [MMD DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), candidate-only [stacked DRAFT PR #55](https://github.com/SemperSupra/stable-character-pipeline/pull/55) on W04 [draft PR #34](https://github.com/SemperSupra/stable-character-pipeline/pull/34), base draft PR #20 unchanged. No merge, deployment, release, CPE policy promotion or third-party model use.

## What was executed

A real **Chromium WebGL** environment, not Babylon NullEngine or a mock:
- Genuine `@babylonjs/core@9.18.0` `Engine`, `Scene` and `ArcRotateCamera`, running under headless Chrome (SwiftShader software WebGL).
- Pinned MIT `noname0310/babylon-mmd` source commit `ccb750db2998ed1067017eaf67f3fc987cfba6f8`, **genuine** `PmxLoader.loadFile/importMeshAsync`, `VmdLoader.loadFromBufferAsync`, `MmdRuntime.createMmdModel/createRuntimeAnimation/setRuntimeAnimation/beforePhysics/afterPhysics`.
- **Original self-authored G10 synthetic four-bone two-link PMX/VMD** only. PMX SHA256 `fadfc3cb3d365cdb4b0c4cc26652c2e831a02ec7da518caae9142dd711468583`, VMD `e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c`, source artifact [G10a run 40455687379](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455687379). No external visual assets/textures or real-person identities.
- 31 actual source-frame poses at frames **0–30**, genuinely rendered to WebGL canvas. `capture.cjs` collects true Chromium PNG screenshot bytes and parallel pose evidence, not re-drawn Python silhouettes or interpolated images. Yellow, gold and red **diagnostic bone spheres and links** are drawn using Babylon's actual mesh primitives over the grey original source PMX mesh; they are overlays, not original PMX character features.

## Verified outcomes and first failure

**First public Actions run [40592792186](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40592792186):** native Chromium actual original 31 WebGL PNGs were produced, with source bone positions changing and original PMX mesh visibly present; but **run FAILED** due to one unexpected browser console error HTTP 404 for `/favicon.ico` automatically requested by Chromium. Inspected actual `http.log` from first-failure Actions artifact **12775680111**, ZIP SHA256 `3701eeaab0a095747e3b26fa081e0cecc6849588151bcf5c78be76c9b87b8ec1`. The root cause was an irrelevant browser favicon request, not a native PMX or WebGL initialization failure. **Correction:** committed `<link rel="icon" href="data:,">` in `index.html` to prevent the external/favicon resource request **without suppressing console errors or reducing required browser/visual checks**.

**Corrected exact-head public Actions run [40593023685](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40593023685):** **COMPLETED/SUCCESS**, native job `122501812516` logs inspected. Reports:
- Real 31 source-frame `PASS_GENUINE_BABYLON_WEBGL_NATIVE_PMXSOURCE_31_FRAME_VISUAL_CAPTURE` from true upstream Babylon and Chromium.
- Actual screenshot pixel changes 0→15 = **37,981**, 15→30 = **32,981**, 0→30 = **62,881**, all above predeclared 450 changed pixels.
- Actual iPhone `babylon_original_31frame_iphone.mp4`: **H.264**, **yuv420p**, **720×960** portrait, **93 decoded frames**, **3.1 sec**, three repeats of the genuine 31 WebGL screenshot frames, `-movflags +faststart`. SHA256 **`1428e16b4362598c8d871ff0ad7559dde691b8832745d34311e47b6971846b19`**. The screenshot at frame 15 has SHA256 `f09e951705245e0f0aef2d1e2a886af1c15676d15e1cdc3b895cd7ee679914fe`.
- Machine-readable `webgl_browser_captures.json` per-frame original named world-bone coordinates and exact PNG SHA, and `mobile_webgl_validation.json` independent pixel-motion/FFprobe manifest. Tampered PNG hash negative check correctly fails. Source-model byte identity verified prior to browser loading.
- Actual ephemeral GitHub Actions ZIP evidence artifact **12775037195**, ZIP SHA256 **`cb74e634e8ce6ed2ec028b5d13cbdf8ec57c1da535a9d5e33b8843fbbb3213fd`**, 14-day retention. Artifact downloaded to current ChatGPT session, and `sha256sum`/independent `ffprobe` verified the exact extracted video and PNG bytes before providing iPhone-direct `sandbox:/mnt/data/mmd_w04_verified/babylon_original_31frame_iphone.mp4` and screenshots. Those conversation links are session-scoped, not authorized permanent public hosting.

## Three audiences and gating

**Human:** direct iPhone-playable 720×960 MP4, three frames 0/15/30 and labeled original PMX + Babylon diagnostic overlays; a small geometric **test rig**, not photo-real human or licensed MMD character. No false claim that these are Blender previews.

**Automation:** isolated public workflow `.github/workflows/mmd-w04-browser-visual.yml` (18 minute maximum, source-read-only permissions and 14d artifact), real pinned dependency sources and byte SHA verification, browser WebGL checks, actual PNG byte digests, non-freeze tests and H264 ffprobe. CI uses temporary Chromium/SwiftShader software renderer, no GPU rental/cloud payment.

**Agents:** stable `scp.mmd.w04-real-browser-webgl.v1` frame evidence and `scp.mmd.w04-browser-iphone-verified.v1` media evidence, exact source fingerprints, qualification status scoped to synthetic source. No CPE admission changes or release promotion.

**Not qualified:** arbitrary asset licensing, production human/Naomi–Alison scene, native MikuMikuDance app CCD solver parity, all-source joint quaternion equality, true skinned vertex-to-pixel parity against direct converter, physical floor contact/friction/Bullet/cloth, crowd scale, platform-wide 3D rendering. Browser WebGL rendering is a **third observable source engine presentation**, but deliberate joint markers are a diagnostic overlay separate from source model surface semantics.

**Next baton:** extend WebGL capture to the original **G9 two-morph PMX/VMD**, check actual dynamic morph deformation and source frame original weights with pixel and morph-geometry evidence, then compare skin/rotation and physically meaningful ground/contact under separate tests; preserve independently held W02 review, W04 draft PR #34/#55, and blocked W19/W20 blind CPE authorization.
