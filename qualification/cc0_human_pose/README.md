# R1: Real CC0 exercise-video → derived still → motion landmarks

**Authority:** [public research DLE #36](https://github.com/SemperSupra/stable-character-pipeline/issues/36), private product DLE #2, shared public motion index #29. Candidate only; no merge, release, deployment, training, identity matching, or concept promotion.

## Original media, not generated input
Source: [Wikimedia Commons / Ej Exercise - ESP ICT.webm](https://commons.wikimedia.org/wiki/File:Ej_Exercise_-_ESP_ICT.webm), uploader EjSupra08, 2024-09-27. Rights on the Commons media page: **CC0-1.0**, source page checked 2026-10-27. Published original SHA1 **43e2cd38a7ebf75d10ed9ab76a0420b1391ecf8c**, exact original size **2,334,882 bytes**. The workflow fetches the original, verifies that SHA1 and size before decoding, and records its SHA256. Original is never committed to the repo. A correct license label on Commons does not establish separate model releases, publicity, or personality rights; this is bounded public research only.

The photographs in R1 are **frames of the video itself**, which ensures the same captured performer without inferring identity but is **NOT an independently acquired reference photograph**. Test R2 must independently source and substantiate a distinct photo/video pair rather than pretending a derived frame proves cross-source identity.

## Exact work to execute
On a public GitHub-hosted **ubuntu-24.04 standard CPU** runner, run the fixed source-bound adapter:
```bash
python -m unittest discover -v -s qualification/cc0_human_pose -p 'test_*.py'
python -m pip install --no-cache-dir 'mediapipe==0.10.21'
python qualification/cc0_human_pose/probe.py --out pose-probe-output
```
Runner has FFmpeg. Download only the two allowlisted source URLs: Commons original video and [official MediaPipe Pose Landmarker Lite float16 v1 model](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task). Model source/version and acquired SHA256 recorded; **model weight licensing/redistribution independent verification remains open**, so weights are not included in artifacts. No secrets, private assets, GPUs, premium runners, caches or additional arbitrary inputs.

The 6-second @ 2fps extraction yields 12 frames; temporal landmark inference and still-image inference on the **same exact frame** give 33 pose point estimates and a bounded still/video concordance. Estimated 3D world landmarks are **not ground truth**. This experiment neither makes a rig nor recovers body identity, clothing layers, skin weights, absolute scale, segment mass, joint constraints or physical contact. The still comparison is not an independent ground-truth oracle.

## Three-audience results
- **Human/iPhone:** `preview.mp4` (H.264/yuv420p), `contact_sheet.jpg`, `same_person_derived_still.png`, and overlay PNG frames in the GitHub Actions run artifact `cc0-photo-video-pose-r1`. The Actions artifact is a ZIP download and may require saving to Files first; this is not yet a durable streaming URL. The [original Commons video](https://commons.wikimedia.org/wiki/File:Ej_Exercise_-_ESP_ICT.webm) remains browser-viewable.
- **Automation:** `landmarks.json` (timestamped image/world coordinate estimates), `receipt.json` (rights, source/model hashes, first failure, coverage), nonzero exit on incorrect source hash, missing video frames or no pose.
- **Agents:** stable issue #36, named checks, terminal workflow run and exact head SHA; next proposed task is R2 cross-source paired imagery then UniRig/Blender rig qualification.

## Acceptance
A **successful GitHub job alone** does not mean full-body reconstruction. PASS for **R1 pose extraction only** requires native exact-head logs, correct source sha1 and model sha256, 12 decoded frames, nonzero frames with 33 landmarks, readable contact sheet and playable preview.mp4, and reported differences with no identity or 3D-truth claims. No benchmark accuracy without an independent reference. Record the first failure in #36 and keep this draft unmerged.
