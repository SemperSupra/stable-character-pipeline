# R014 pinned shader-evidence replay (no CC0 re-download)

The previous MPFB `research/r014-mpfb-eye-shader-v1` matrix run [#43207664661](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43207664661) correctly acquired/pinned the 281 MB upstream source and generated two textured human pairs. Its **own unit-test regex was defective** and failed both jobs at the audit stage, even though the modes have different Blender node compatibility.

This independent audit-only public runner reuses the short-retention original **26MB research artifacts** using authenticated read-only GitHub Actions access, not another 281MB upstream download. It parses archived raw logs, confirms source phenotype/asset SHA evidence, and emits a machine decision. A node-service error gate is **not** proof of render optics, realism or camera-quality; no asset promotion, code merge or shader replacement of the underlying MPFB runtime occurs.

The corrected source pattern accepts MPFB's dotted log prefix. The original `MAKESKIN` mode has zero such errors; `PROCEDURAL_EYES` mode yields 20 errors on this pinned Blender4.5.16 setup. Both native models remain research only and incomplete anatomically.

Runs and artifacts are user-accessible on the public repo. Private authority [R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138).
