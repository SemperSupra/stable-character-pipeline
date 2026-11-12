# R014 MHR native rig + face motion through live subdivision (research HOLD)

Purpose: advance a **real motion-ready native geometry family**, rather than claiming the incompatible 677k CC0 sculpt is successfully rigged. This research branch depends on the source-pinned MHR FBX/native baseline in draft PR #405. The exact model asset bundle is official MHR v1.0.1 and SHA-256 pinned.

Two independent $0 public disposable Blender jobs reuse the actual MHR LOD1 skinned armature and 117 non-Basis shape keys: (a) an anatomically named upper arm/shoulder bone driven in 24 frames; (b) source-proven face keys for blink, jaw and bilateral lip-corner control. Each job evaluates neutral and animated skinned meshes at native base plus Catmull–Clark subdivision levels 1 and 2, records exact vertex/triangle counts and all pose-induced inverted triangles, degenerate areas and collapses. It generates a saved editable .blend, base-LOD animated GLB, actual native H264 motion proof and independently framed neutral/pose images.

**Important quality boundary:** subdivision alone creates smoother geometry, not authored details/skin pores. MHR's nonlinear neural pose-corrective functions do not automatically survive Blender/glTF export. A source bone/shape-key moving and a valid MP4 do not establish human-like movement. No external reproductive morphology or physiological tissue physics is accepted.

- Original model/identity/rights boundaries remain pinned and research-only.
- Only public synthetic generic MHR is used; no private people or media.
- No existing branch/main merges, no protected data on public runners.
- GHA artifacts are short-lived staging, with private Drive archival required before release.
- Even if generated structural experiments are green, the R014/R009 status is **HOLD**.

Authority: [R014 private DLE #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138). The independent body-morphology sensitivity experiment is draft PR #441; R015 consumer semantics remain [private #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141). This branch is a proposal, not an approved canonical model selection.
