# R072 — actual H264 depth-parallax counterexamples to a 2D motion critic

**Existing authority:** [R070 draft #615](https://github.com/SemperSupra/stable-character-pipeline/pull/615) exact base `d29d2b49780cb5de0ea82e32c4c35f033e58ad33`, [public Visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), [private R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168), [private R009 MVP #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). DLE=Durable, Legible, Executable. Research-only draft stacked on R070, no edit to previous owner/critic branches.

## Falsifiable 3D hypothesis

A 2D similarity transform fitted to same-depth visual reference markers can report a stationary foreground/background subject as **moving** when the camera translates horizontally, because pinhole x displacement is `-f * cameraTranslation / subjectDepth`. A successful R070 verdict on a fixed-fiducial 2D scene **must not be generalized to scenes with depth parallax**. We explicitly seek to reproduce the unsafe pass, rather than hide it.

**Eight independent original synthetic public GHA jobs**, each Go-stdlib source-world scene with camera pose/3D object coordinates, render new fixed color squares, actual ffmpeg H264 encode + decode, pass resulting decoded PNGs through R070 unmodified, independently adjudicate the R070 receipt in R072 with exact source/decoded-frame SHA binding:

| Scene / camera | Frozen source-world oracle | Required observation |
|---|---|---|
| coplanar-pan | static red at Z=4, camera +0.4 X | R070 STILL, safe coplanar control |
| coplanar-world-right | red actual world +0.6 X | R070 RIGHT, safe coplanar control |
| coplanar-world-left | red actual world -0.6 X | R070 LEFT, safe coplanar control |
| parallax-near-still | static red Z=2 vs references Z=4 | **R070 reports LEFT (unsafe)** while world truth STILL; R072 MUST flag false motion |
| parallax-far-still | static red Z=8 vs references Z=4 | **R070 reports RIGHT (unsafe)** while world truth STILL; R072 MUST flag false motion |
| mixed-reference-depths | reference Z=3,5,4 | R070 UNKNOWN / fails reference consistency |
| lost-red | red disappears in second frame | R070 UNKNOWN / missing witness |
| yaw-projective | camera yaw +0.22 rad, static objects | R070 UNKNOWN / out of 2D similarity scope |

Independent **analytic test** checks pinhole 2D displacement: camera +0.4, focal 180 px, Z=4 -> -18px; Z=2 -> -36px; Z=8 -> -9px. A static subject at near Z=2 therefore has -18px *spurious* motion relative to equal-depth static references; far Z=8 has +9px. The dangerous false positives must appear as explicit negative evidence, not greenlight the old 2D critic. Conflicting observed outcomes are **FIRST RED**, never auto-adjust ground truth or 2D thresholds to fit.

Narrow source-only color markers and perfect pinhole intrinsics are NOT a real camera calibration, multi-object tracker, depth estimator, VLM, 3D rig, human tissue, gait/anatomy, protected character source or cinematic acceptance. The source scene contains the depths, while real footage does not; a future camera critic must require an admitted depth/3D source witness or return UNKNOWN when viewpoint/parallax cannot be excluded. No paid models, private Actions minutes, character media, product promotion, Cloudflare tunnel, merging or release. GHA receipt artifacts text only, 3-day TTL; first RED and exact runner/head to DLE.
