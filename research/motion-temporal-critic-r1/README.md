# R1 Temporal Motion & Critic Evidence Grounding — Synthetic, Research Only

This isolated public source-safe workcell compares *two-dimensional projected tracks* on exact synthetic clocks and validates claims from a **simulated** VLM observer against immutable source/target track SHA-256. It is **not actual VLM inference**, 3D proof, MMD support, MakeHuman qualification, or natural-motion acceptance.

## Experiments / independent workflow

- **motion**: reject frozen targets, reversed directions, nonfinite trajectories, duplicate/shifted clocks, and too few frames; equal 2D trajectories are `MATCHED_PROJECTED_2D_ONLY`, never accepted 3D motion.
- **resample**: expose 60 Hz → 30 Hz temporal aliasing using a self-authored 5-frame high-frequency source whose odd-tick motion vanishes on downsampling. This is a *format-clock control*, not byte-accurate MMD/VMD conversion.
- **critic**: bind a source/target SHA, camera, first/last timestamp, finite confidence, model identity, and independently measured geometry. A simulated favorable visual judgment cannot override the measured mismatch; a modified target track invalidates the source hash.

Go 1.23 standard library only. No third-party data, weights, authentic human characters, private assets, model inference, GPU allocation, paid/private runners or secrets. Three truly independent `ubuntu-24.04` public Actions matrix jobs each with a 5-minute timeout. No merging, production adoption, release or R009 film acceptance.

This adds no new authority. Source and qualification owners: public [MMD #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), [Motion #29](https://github.com/SemperSupra/stable-character-pipeline/issues/29), [Visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), private [R009 #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23), [R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138) and [R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168).

Run from this directory: `go test -count=1 ./...`; `go vet ./...`. Report exact source commit, hosted job result and first failing invariant to the owning DLE. Next: integrate *existing* actual MMD Blender/VMD/BVH source and native MPFB/CMU workcells by explicitly admitted source compatibility, including source clocks and real render hashes; then blind, source-correct VLM inference at a separately admitted model.
