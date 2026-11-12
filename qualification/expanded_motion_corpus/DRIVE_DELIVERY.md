# Persistent iPhone-first media delivery and mathematical QA (2026-11-12)

Authority: [Visual QA DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150) and [Walking #84](https://github.com/SemperSupra/stable-character-pipeline/issues/84). Parent full-body 3D [draft PR #368](https://github.com/SemperSupra/stable-character-pipeline/pull/368). This is an independent research child; no main merge or CPE promotion.

## User-owned durable media

- [Google Drive — Stable Character Pipeline / Motion Corpus RDT&E](https://drive.google.com/drive/folders/1BpEFBGDpl6yMIVNZHUtmZInYCG9FLtkd).
- **[START HERE — iPhone PDF index](https://drive.google.com/file/d/1R6t6Im_Vq9uXuoii-mnlOWZUC0E4BucR/view?usp=drivesdk)**, 22 clickable per-file MP4 links, independent QA PASS/FAIL/UNKNOWN.
- [22 separately playable H.264 MP4s](https://drive.google.com/drive/folders/1k2IzHAfaV_5U6OJmEtg3zCrGdBLTj-RZ) (320x320, 40 frames, yuv420p); no ZIP required for iPhone.
- [22 animated glTF/GLB assets, 22 source joint/contact JSON labels and batch manifests](https://drive.google.com/drive/folders/1N6wiD84zUqkHHLZIpYDFZNlTZ2Q8gWgF).
- [Math research, original procedural generator and replayable audit source](https://drive.google.com/drive/folders/1DmeP_waHOv05IadTfyzPqQPb6sdQ6sp8).

User account access to these Drive items is governed by existing Drive permissions; no public/anyone links or altered sharing permissions have been granted. Google Drive may require video processing before preview on another device. iOS Drive supports H.264 MP4 previews; GLB requires a separate 3D-capable viewer, so provide MP4 first. For Git LFS, do not silently consume LFS quota or use it as the default video viewing surface; Git/GHA is for source and reproducible CI, Drive for long-lived media.

## Independent mathematical research and falsifier evidence

Parametric research in `MOTION_MATH_RESEARCH.md` covers Alexander/Jayes Froude/dynamic similarity, speed/cadence/duty factor, Flash-Hogan minimum jerk, exact law-of-cosines leg IK and unreachable targets, world stance-foot contact anchors, heel-dependent foot constraints, SLIP spring mass running/hopping, Laban expressive movement, DMPs for discrete/rhythmic gestures, and aquatic front-crawl coordination.

**Observed source-truth results on the original 22 procedural cases:** targeted 1 cm leg-length and 0.025 m/s labelled-stance foot speed checks give **10 PASS / 11 FAIL / 1 UNKNOWN**. Source-first audit correctly exposes original baseline false positives in jumping, idle, jumping jacks, cartwheel, dance, pinup/photoshoot, kata and diving. Swimming is UNKNOWN because ground-contact tests do not qualify aquatic movement. PASS means only this source geometry/contact oracle; not biomechanics, real-person likeness, balance, technique correctness, or native pixels.

An earlier local script labels male/female as two **morphology presets**. Future architecture must keep sex as optional annotation, and body shape, segment lengths, physiology, style, heel height, sole and contact geometry as explicit continuous parameters. Do not enforce sex stereotypes or invent innate quantitative gait laws. The authored cartwheel and kata motions are research placeholders, not expert instruction or validated technique.

## Disposable parallel executable verification

The `video-expanded-3d-motion-math-research` public path-scoped PR workflow uses four independent native public Ubuntu 24.04 matrix jobs, one per family: locomotion, exercise_pose, dance_combat, aquatic. Each generates original animated GLB, actual 40-frame H264 MP4 and source JSON inside a fresh VM, installs ffmpeg and pinned NumPy/OpenCV in a temporary venv, then validates codec/gltf/source counts; no credentials, real persons, paid hardware, persistent dependencies or Kaggle quota.

The dependency-free `independent-math-adjudication` job downloads each matrix result by artifact name, tests 14 independent numerical/negative controls, aggregates all 22 source labels, asserts exact 10/11/1 expected evidence and uploads the machine-readable audit. Failed/UNKNOWN cases remain preserved for corrective A/B, not silently rewritten to PASS.

The checked-in generator/math and tests were locally validated before PR; hosted results must be verified by exact job logs and receipts before claiming cloud qualification. After any corrective follow-on, keep the immutable defective corpus with separate SHA and new clean versions. No release or owner character identity promotion from this synthetic matrix.

## Next independent workcells

1. Fix the labelling and kinematic reachability defects; use exact world contact anchors and a strict two-link IK solver, first for standing/jumping and then dance/photoshoot.
2. Add shoe-specific contact and ankle ROM/heel-toe rolling constraints; do not treat a different color as a footwear biomechanical model.
3. Add a genuine authored hand-contact cartwheel and independently validated martial/swim motion templates, with actual body-axis dynamics; until then retain UNKNOWN/FAIL.
4. Use the same original Drive videos to test pretrained CoTracker3 and source-to-pixel QA (#364/#366/#367), with independent image-derived pose and explicit uncertainty.
5. Keep PDF iPhone index and Drive per-file video links reconciled with every new rendered artifact; use GitHub issue DLE as authority, not ephemeral chat links.
