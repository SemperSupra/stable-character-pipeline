# R3 NASA documentary video → editable skinned camera-plane proxy

**Authority:** public [R3 DLE #43](https://github.com/SemperSupra/stable-character-pipeline/issues/43), stacked on unmerged [NASA source-pair PR #42](https://github.com/SemperSupra/stable-character-pipeline/pull/42), the product [private DLE #2](https://github.com/SemperSupra/stable-character-pipeline-private/issues/2), and public motion #29. Research-only, public $0 CPU; no merge, release, deploy, training, CPE promotion or identity assertions.

## What it actually is
The pin-verified official NASA source video and the official MediaPipe Lite model from R2 are independently downloaded in the public CPU runner and sampled at 1 Hz. The Go stdlib converter verifies the R2 source proof and strict exact-clock 30-frame model observations. It selects **only the longest continuous run** where all 33 model-estimated pose landmarks exist (no interpolation across missed video frames). It maps normalized image XY into an arbitrary-sized glTF camera plane with Z forced to zero and makes a **skinned procedural stick mannequin**, not a person's 3D body.

Outputs: `camera_plane_skinned_motion.glb` contains 33 named landmark nodes, one shared skeleton root, skin, inverse bind matrices, deformable weighted geometry, animations with source-linked time, and material. `rig_manifest.json` records source/sample input SHA256, original NASA video SHA1, GLB SHA256, missingness, source frame start/end and unknowns.

An **independent Blender GLB importer** checks native armature, skinning and motion deformation in evaluated geometry at different animation times, then renders a short 640×360 sequence. FFmpeg creates `camera_plane_rig_demo.mp4` with H264 + yuv420p + faststart for iPhone playback. `blender_independent_readback.json` holds actual Blender version, bone counts, skinned mesh counts, observed vertex-group weights, action count and measured proxy displacement. The PNGs can support human visual review; no generated scene can prove source-geometry recovery correctness without independent ground truth.

## Methods and falsifiers
- Go `main_test.go` rejects truncated joint arrays, NaN, out-of-range visibility, altered sample clocks, single-only pose runs, corrupt source SHA. Structural tests inspect glTF GLB magic/version/length plus declared skin, weights and animation.
- This mesh has skin weights and deforms, but its **proxy topology and stick thickness are hand specified**. Therefore it is not UniRig or other neural skinning inference. Bone lengths, contact, movement plausibility, depth, mesh likeness, texture, body profile, or appearance are **NOT validated**.
- A joint's `visibility` is source-model confidence metadata; Blender glTF proxy does not imply missing arms/feet were genuinely observed. Original all-frame masks remain in `rig_manifest.json`.
- Pixel XY and model-estimated z are not metric 3D. To avoid faking depth, z is flattened to zero and declared camera-plane projection.
- NASA imagery is U.S. public-domain material; publicity/endorsement/insignia conditions are not presumed cleared by that copyright status. The official pose task model is used from its source URL; weights are not published. No private subject data.

## Audiences
Human: simple actual generated skinned GLB and H264 video / PNG frames through public Actions artifact for iPhone, clearly labeled proxy. Automation: CLI `go run qualification/nasa_rig_r3/main.go -input ... -receipt ... -out ...` and deterministic JSON with fail-closed exit 4. Agents: issue #43, exact-head PR/run, source/GLB SHA and first-failure next baton.

**Future separate workcells:** model-estimated 3D world pose with uncertainty, independent anatomical oracle, joint-local rotations/IK/contact and topology retarget, then actual model-rigger experiments (UniRig, SAM 3D Body, MoCapAnything) subject to CPU/GPU and independent model license gates.
