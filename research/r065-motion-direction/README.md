# R065 — independent numerical frame-direction critic

**Why:** R063 actual [GHA #43966713723](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43966713723) showed SmolVLM2-256M classified both reversed frame pairs as LEFT. R064 actual [GHA #43968175376](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43968175376) showed SmolVLM2-500M classified both as RIGHT. Both failed the inversion control, 1/2. Treat neither as a directional ground truth. No VLM can override geometry, provenance, timing or contact tests.

This standalone source-original research workcell implements a measurable **geometric witness** (not a general visual-language model): decode source-created red-square two-frame H.264 through actual FFmpeg, inspect the decoded PNG pixel channel, compute red connected-class centroid X, classify RIGHT/LEFT/STILL using fixed >10-pixel movement, refuse missing target/mismatched frame dimensions/severe pixel-area change, and record the *actual decoded frame* SHA256s and source head. This is a first control in the Visual QA layered oracle, not a human skeletal/motion/photorealism or body-identity critic.

## Independent 4-way public GHA qualification
- RIGHT positive (x 10→148) — geometric direction must be RIGHT.
- LEFT exact reverse (x 148→10) — geometric direction must be LEFT.
- STILL (x 74→74) — no false motion claim.
- OCCLUDED (second frame contains no red subject) — exact typed UNKNOWN/NO_RED_SUBJECT with nonzero exit, not a synthetic PASS.

Each job generates its *own* original source PNGs and encoded H.264, decodes its own video, compiles/tests source with `go test -race` and `go vet`, and runs the command against decoded frames only. No private Naomi/Alison scene, third-party dataset, prompt, weights, credentials, model provider, GPU, public binary artifact or paid/private CI. Four independent standard public Ubuntu 24.04 runners at most 5 minutes each. SHA/first-RED JSON and text-only GHA evidence retention 3 days.

### Use
```
cd research/r065-motion-direction
go test -race ./... && go vet ./...
go run . --make right --out /tmp/r065
ffmpeg -framerate 1 -i /tmp/r065/frame_%03d.png -frames:v 2 -pix_fmt yuv420p -c:v libx264 /tmp/r065/candidate.mp4
mkdir -p /tmp/r065/decoded
ffmpeg -i /tmp/r065/candidate.mp4 /tmp/r065/decoded/frame_%03d.png
go run . --first /tmp/r065/decoded/frame_001.png --second /tmp/r065/decoded/frame_002.png --expect RIGHT
```

### Boundaries & DLE
Owner public [Visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150) and private [R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168), R009 film [#23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23), adopted [Way of Working v0.0.4](https://github.com/SemperSupra/engineering-governance-private/blob/main/WAY_OF_WORKING.md), DLE = Durable, Legible, Executable. The target artifact is a small independent numerical comparator for frozen original synthetic patterns. It cannot recognize non-red humans, arbitrary subject masks, camera pans, optic flow, anatomical flexion, foot contact, activity, audio, actual photorealism or naturalness. Any change of target marker/scene/threshold requires a new qualified contract; not a drop-in universal video critic.

At PR creation, hosted acceptance is **NOT_RUN / NOT_OBSERVED** until source-pinned GHA jobs actually complete. No auto-merge/release or protected media admission. Future VLM critics must first pass this independent falsification class on held-out varied fixtures and compare projected 3D motion/occlusion references, not receive a pass from caption plausibility.
