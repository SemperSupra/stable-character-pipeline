# R2 — Independent NASA official photo and workout video

Authority: [R2 public DLE #40](https://github.com/SemperSupra/stable-character-pipeline/issues/40); the R1 source- and pose-admission workcell is draft [PR #38](https://github.com/SemperSupra/stable-character-pipeline/pull/38). This is a **stacked research candidate**, not an accepted character or reconstruction.

## Genuine independent capture pair
- [NASA Johnson official workout video](https://commons.wikimedia.org/wiki/File:Astronaut_Mike_Hopkins-_Workout_in_Space_2.webm): original size **10,680,037 bytes**, SHA1 `dfc000088cfff728b57fe0c8ae38a7266410caeb`, 2014-02-19, U.S. public domain NASA.
- [NASA/Bill Stafford independently photographed portrait](https://commons.wikimedia.org/wiki/File:Michael_S._Hopkins,_official_portrait.jpg): original size **3,001,066 bytes**, SHA1 `e9e88122157dd60bc314d57754c02844954eaa00`, 2016-12-29, JSC ID `JSC2017-E-005228`, U.S. public domain NASA.
- **Same subject provenance** rests exclusively on NASA's *independent source captions* both naming Michael S. Hopkins, not an algorithmically deduced identity; no images are used for face-recognition or matching scores.
- US-government public domain concerns copyright in the United States, **not** releases, personality/publicity rights, NASA logo/insignia or global jurisdiction rights. No endorsement claim.

## Source-bound test
The standard free public Ubuntu CPU Actions workflow downloads the two unchanged originals from allowlisted Wikimedia upload origins, independently verifies published exact SHA1 and byte counts, downloads the same R1 MediaPipe Lite v1 task with its **observed pinned SHA256**, samples 30 frames at 1fps across source seconds 11–41 (first trial 3–9s hit opening titles, recorded as a failed R2 receipt), detects 2D landmarks per video frame, then separately runs image-mode pose on the independently captured portrait. Build `video_landmarks.json`, `portrait_landmarks.json`, `receipt.json`, annotated `video_pose_preview.mp4`, `contact_sheet.jpg`, `portrait_overlay.jpg`, and a small reference copy. Never treat two different poses as a 3D pose-concordance oracle.

No 3D rig, skin weights, cameras/intrinsics, true world 3D, retargeted motion or learned identity model is produced. The video and portrait were captured in different settings, postures and clothing. Failure to detect the 3/4-body spacesuit portrait is **an explicit finding**. R2 passes media provenance and video pose extraction independently of full-body photograph coverage; labels `OBSERVED_VIDEO_POSE_PHOTO_POSE_UNAVAILABLE` if the photo has zero 33-point skeletons.

## Three audiences & safeguards
Human: annotated 30-second iPhone-compatible H.264 MP4 at one observed frame per second, portrait overlay and contact sheet in GitHub Actions artifact, which expires after 3 days (not a streaming archive). Automation: no interactive input, fixed URLs, bounded bytes/time, checksum and model invariants, negative unit tests, structured JSON receipts and nonzero exit on genuine source/video failure. Agents: exact PR/commit/run, source SHA hashes, first failure and next baton in issue #40. No secrets, paid runners, raw image/model redistribution in repo, release/merge/deployment, CPE policy promotion or private asset ingress. Independent visual/kinematic correctness review remains mandatory.
