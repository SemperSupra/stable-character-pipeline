# R070 — 2D camera similarity critic with an independent third reference

**Existing authority:** [R065 draft #610](https://github.com/SemperSupra/stable-character-pipeline/pull/610), [R066 draft #611](https://github.com/SemperSupra/stable-character-pipeline/pull/611), public [Visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), private [R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168), private [MVP R009 #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). This source-clean draft stacks on R066 HEAD `093fd1473256da2b7fae8e8776a19f972f07ec09`; none of those branches are edited.

R066 compensated only camera translation using one static green marker. That **cannot distinguish** rotation, scale, mirror reflection, or a false-moving fiducial from subject movement. R070 uses three independent color-coded synthetic static references (green, blue, yellow); green+blue solve a bounded 2D similarity transform (translation, rotation, scale), yellow independently falsifies that transform via residual. Red subject displacement is inverse-mapped into source-world 2D coordinates. Missing reference/subject or out-of-domain transformations explicitly return UNKNOWN and nonzero CLI. This is a source-only numerical comparator, not VLM.

### Pre-registered nine independent public CPU GHA experiment lanes

| Lane | Independent expected oracle |
|---|---|
| translation-only | STILL, no relative subject motion |
| zoom-only | STILL under camera scaling |
| rotation-only | STILL under camera rotation |
| right-under-zoom | RIGHT after inverse projection |
| left-under-rotation | LEFT after inverse projection |
| corrupted-third-anchor | UNKNOWN, third anchor residual exceeds bound |
| mirror-reflection | UNKNOWN, similarity estimated rotation out of domain |
| lost-third-anchor | UNKNOWN, missing independently verifying reference |
| lost-subject | UNKNOWN, missing subject evidence |

Every lane creates original 320×320 synthetic color PNGs with independently defined camera parameters, **actually encodes H264 and decodes the video**, measures decoded color centroids and counts, computes source and decoded SHA256 receipts, Go race/vet, validates positive and falsifying negative controls. Seven? Nine jobs, each <=8 min on standard free-tier public GitHub Actions, no private Actions minutes, assets, secrets or model weights. Retain only text evidence for 3 days; never upload output video.

**Qualification limits:** A 2D similarity homography of this restricted form is not perspective, depth, zoom-dependent blur, camera calibration, multi-body tracking, articulated nonrigid human motion, anatomy, photorealism or final character review. Reference colors and anchor identities are perfect synthetic inputs; multi-object identity and occlusion remain open. Third anchor tests consistency only under this model and can fail under perspective/parallax without implying bad video. Do NOT promote to source/native film or product acceptance. Next held-out DoE adds perspective/parallax, occlusion, lighting, variable color, and 3D source camera truth under a separately admitted contract. No additional orchestration/control plane, merging, protected source transfer, license/admission bypass, or release.

Reproduce `go test -race ./... && go vet ./...` within [module](./main.go), with real video conversion in [GHA workflow](../../.github/workflows/r070-similarity-camera.yml). DLE=Durable, Legible, Executable; statuses NOT OBSERVED until exact hosted job receipts.
