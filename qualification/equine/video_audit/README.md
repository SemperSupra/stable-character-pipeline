# Exported-GLB-only pony animation visual QA

Shetland DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/293
Candidate native articulated IK source frozen to `1b0a12da753ad662ec5b21f8d1aad73fba3224d9` ([draft #302](https://github.com/SemperSupra/stable-character-pipeline/pull/302)).

This independent public original workcell checks out the exact source and rebuilds one GLB per matrix runner (black, pinto, white) inside the Blender Foundation GHCR dependency image plus SHA-qualified Blender 4.5.15. It then **reimports the exported GLB** into a fresh native scene and renders every one of 48 animation frames at 24fps using CPU-compatible Workbench, encoding a silent two-second H264 MP4 and twelve-pose contact sheet with FFmpeg. Verifies video frame count and file digests. No protected reference photos, local v1, third-party pony mesh or recorded horse audio in the public runner.

Source qualification is not biological or visual acceptance. Rendered motion and joint deformation must be human/automated visually reviewed; full-body conformation and winter fur remain stylized. Source has real swing-clearance improvement but a conservative foot-gap proxy, and no measured contact forces or natural gait certification. Output video for human UX; hashes/JSON for automation; exact-SHA repeatable acquisition for agents. This branch is separate from source author and scientific auditor; no merges or promotion without owner DLE gate.
