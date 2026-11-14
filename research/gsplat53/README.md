# R0: public synthetic Gaussian-splat representation qualification (Blender 5.3.0)

**Purpose:** A real, bounded cloud CPU smoke of Blender 5.3's new 3D Gaussian PLY importer, renderer, and object-level rigid edit against a native mesh control. This is not a generative reconstruction, mesh-extraction, soft-tissue, articulated-body, or photorealistic-human bakeoff. All input code and data are authored original synthetic fixtures and safe to run in free public standard GitHub Actions.

## Command / prerequisites
Run `python3 research/gsplat53/fixture.py --self-test --output out/synthetic_gaussians.ply`.
Use official Blender 5.3.0 binary (release archive from download.blender.org, validated against its published `.sha256`), then:
`BAKEOFF_OUT=out/gsplat53 BAKEOFF_PLY=out/synthetic_gaussians.ply blender --background --factory-startup --threads 4 --python-exit-code 1 --python research/gsplat53/smoke.py`

The checked workflow is `.github/workflows/gsplat53-cpu.yml` with standard `ubuntu-24.04`, 18-minute hard timeout, `contents: read`, 3-day tiny artifact retention, no secrets or paid/private worker. No scheduled cadence.

## Acceptance and falsifiers
- Verify deterministic generator, all 17 synthetic 3DGS PLY scalar attributes, shape, finite numbers, unit quaternions, reject missing attribute, truncated payload, wrong encoding.
- Verify actual Blender 5.3 version, PLY imports exactly one `POINTCLOUD` with `GAUSSIAN_SPLAT` type; separately create mesh control.
- Match fixed camera/lighting/background/resolution/Cycles CPU settings. Render origin and 0.6096m X-translated variants; use decoded alpha-pixel centroid movement, not just transformation parameters. Native type, fixture SHA, four actual PNG hashes, render latency, alpha count and displacement are captured in `receipt.json`. Structural edit must be exact and rendered displacement nonzero/rightwards; opaque image, missing importer, incorrect type, or empty image is RED. A red first run prompts root-cause corrective changes on the branch, not a PASS.
- No static PSNR comparison between geometry of cube and gaussian plate; these are **not matched surfaces**. No claim of deformation, geometry reconstruction, learning, relighting quality, realtime performance, cross-platform support, source rights, or user-quality acceptance.

## R1/R2 next candidates (no GPU admission yet)
- **R1-a:** Blender 5.3 GAUSSIAN_SPLAT imported PLY/SPZ source-safe fixture; render/move/rotate/relight and camera sweep, then compare to analytically matched source mesh.
- **R1-b:** SuGaR surface-aligned splats + bound connected mesh, only after checking third-party gaussian-splatting noncommercial license and training/source dependencies.
- **R1-c:** MeshSplatting connected opaque mesh extraction, CUDA 12.6/PyTorch 2.7.1 build and upstream submodule licenses; on eligible Kaggle free GPU using original synthetic, source-safe fixtures. Separately qualify GPU build, training, export, watertight/manifold and distortion.
- **R1-d:** HumanGS SMPL-X Gaussian-bound avatar, only after independent rights/weights/SMPL-X/THuman/AvatarReX admission; use original synthetic adult baselines without copying restricted data or relying on native-MHR compatibility.
- **R2 challengers:** Triangle Splatting, Universal Beta Splatting, Gaussian Point Splatting; test source feasibility first. The point-splat renderer requires simultaneous NVIDIA CUDA+OpenGL, not generic free notebook GPU. Never represent a source-only inspection as trained output.

Per-candidate receipt fields: source URL/license/commit + third-party dependency and checkpoint IDs/hashes, execution venue, actual GPU/driver/CUDA/VRAM and wall time, source scene/camera/colorspace/rig/topology/rights/timebase, import/compile/train/render cost, mesh/rig/soft-tissue/contact/semantic edits and negative controls, image metrics and geometry metrics, evidence artifact SHA. Hold out edit interventions and no automatic canonical-CPE promotion. Repo tracks generic source-safe code and receipts; private character data remain private and on approved hardware only.

**DLE:** Stable Character private R033 #168 (science owner), public #150 (visual QA), Model Mechanisms private #1 (generic DOE/replay contract); no conflicting DLE authority or new runner orchestration. User does not manually review routine work; independent technical acceptance is still required for merge. R0 has no dependency on private Product P0 #167 and does not replace that gate.
