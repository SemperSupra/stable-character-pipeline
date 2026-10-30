# Autonomous visual QA V1 — original synthetic public qualification

Authority: [DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), walking #84, private product owner #2 (no private media here).

This independently runs a source-original W16-C2 Blender scene through two different observers on **public standard GitHub Actions CPU**:

- **L1 actual rendered pixels**: FFprobe verifies real H.264 stream settings; FFmpeg decodes *every actual image frame*, records decoded-image framemd5 count and unique images, checks black/freeze spans, and creates a 4×3 full-output contact sheet. Reports `scp.visualqa.l1_video.v1` and exact SHA256. A media file existing is NOT the same as visually qualifying it.
- **L2 independently evaluated Blender bone geometry**: `probe_blend.py` reads the **saved .blend**, evaluates two original actors and left/right upper/lower bone head/tail locations at seven source time indices, then `main.go` independently checks input source SHA256, exact clocks/coverage, finite positions, preserved bone lengths, signed *declared* knee pole direction and excessive flexion. Reports `scp.visualqa.l2_knee_result.v1`. Deliberately reversed-knee, no-pole, straight-only, tampered SHA/clock, rights and missing-leg negative tests.

Reproduce source tests:

```sh
cd qualification/visualqa
go test -race -count=1 ./...
go vet ./...
```

The workflow `.github/workflows/visualqa-v1.yml` automatically executes **both** independent original synthetic W16-C2 profile renders when this workcell is changed on a PR. It is a draft-only bounded CPU qualification, not a production deployment.

## Important safety limits

**L1 PASS is NOT anatomy PASS. L2 PASS is NOT image-derived visual/anatomical PASS.**
The synthetic rest-pole is a *source-authored reference* (not independently approved biological anatomy); that geometry test can detect reversing the bend relative to that reference, but it cannot tell whether the declared bend direction is anatomically natural. The preview has low-detail abstract weighted geometry. No independently inferred anatomical joints are read from the pixels yet, nor are image-to-projected-rig parity, foot contact, gait, physics, intentional occlusions, skin deformation, real character, whole-body anatomy, identity, subjective quality, lip sync or A/V correctness established. Blank/black/freeze heuristics can have legitimate artistic exceptions, requiring independent review instead of threshold weakening.

**Next independent vision workcell (L3):** pin CPU MediaPipe Lite model and exact artifact SHA/terms, run on per-frame RGB derived from H.264 and 3-view orthographic re-renders, separately compare image-inferred landmarks and source scene projections with confidence and occlusion labels. A machine-vision model may abstain on abstract procedural avatars; never turn missing detections into green. Condition on natural-human capture only when rights-admitted.

**Next visual-critic workcell (L4):** compare limited-frame results from an actually callable, $0 rights-admitted VLM; do not assume any ChatGPT subscription includes an unattended API or external media disclosure permission. Prefer local CPU/open weights on standard public runners if bounded. A model rating cannot override hard geometric FAIL.

**Acceptance:** current outputs are only L1 and L2 gate results. Overall visual anatomical quality must remain **UNKNOWN** until independent L3 and approved rest/anatomy basis are actually qualified. No green numerical or file tests shall be advertised as realistic walking.

## Three audiences and custody

Humans: contact sheet, error location/frame and original H.264. Automation: command-line exit 0 pass / 2 fail / 3 unknown and JSON. Agents: deterministic program/schema/falsifier list and exact-head CI receipt. Public draft Git stores small source/tests and safe receipts; ephemeral 3-day CI media may be retained in private owner Google Drive only after AAR/CDR verified full-byte SHA rehydration, with private locator only in private product DLE. Do not commit private character imagery, source meshes, sovereign node/machine/IP details or proprietary assets to public Git. Standard public runners only, no secret/cloud paid API/merge/release/deploy/CPE promotion.
