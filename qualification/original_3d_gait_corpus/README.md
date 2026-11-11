# Rights-original articulated 3D gait video corpus — QA RDT&E

**Authority:** [Visual QA DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), [Walking DLE #84](https://github.com/SemperSupra/stable-character-pipeline/issues/84), parent [RDT&E root #356](https://github.com/SemperSupra/stable-character-pipeline/pull/356). This source-only research package creates actual **animated mesh 3D models** with independently decoded H.264 camera footage, not a still image, line-skeleton drawing, frame interpolation trick, real-person material, or unlicensed third-party character.

## What it produces

The full-body stylized 3D mannequin has **18 named animated mesh nodes, 54 glTF 2.0 animation channels and 48 frames**. It includes a head, torso, pelvis, arms, hands, two IK-generated legs with constant 0.53 m thigh and 0.52 m shin lengths, colored shoes, a ground plane and two independent 3D cameras (side and three-quarter). There are **three distinct original source animation sequences** and **six actual H.264 videos** (400×400, 24 fps, 2 seconds per clip):

| Original source | Ground truth | Expected outcome |
| --- | --- | --- |
| `clean` | 0.000000 m/s peak planted left foot, no reversed left knee | PASS on targeted synthetic contact/polarity controls |
| `knee_reverse` | 16 frames with reversed source-left knee bend; planted feet remain stable | FAIL knee-pole/anatomy constraint |
| `foot_slide` | 0.283333 m/s peak moving *planted* left ankle; no knee reversal | FAIL foot-skating constraint |

Each generated result includes `<case>.glb` animated 3D model, `<case>_ground_truth.json` with frame-level 3D hip/knee/ankle/toe/shoulder/elbow/hand positions and contact labels, `<case>_side.mp4` and `<case>_three_quarter.mp4`, and machine-readable `manifest.json` with GLB/video/labels SHA256, exact codec/frame/fps checks, limb-length and motion falsifiers. This is suitable for independent geometry, video tracking, model inference, video-quality, accessibility-friendly text comparison, automation and agent evaluation.

## Disposable generation and verification

The [source-exact path-scoped workflow](../../.github/workflows/original-3d-gait-corpus.yml) runs **three separate public free GitHub Actions jobs in parallel**, each in a fresh disposable Ubuntu 24.04 VM; no persistent host, `~/.local`, service, Kaggle quota, premium runner or protected content. Each VM installs FFmpeg and an ephemeral `runner.temp` Python venv with pinned NumPy 2.3.5 and OpenCV headless 4.13.0.92, then renders two H.264 camera views, verifies **48 decoded frames per clip**, checks glTF binary animation structure, tests physical and anatomical defects against 3D source geometry, hashes all evidence and uploads the small output artifact. No third-party character art, pretrained model weights, network-rendered images or credentials.

Reproduce in any **disposable** Linux environment that already has FFmpeg, NumPy and OpenCV:

```bash
python3 qualification/original_3d_gait_corpus/build_corpus.py --out /tmp/original_gait
python3 qualification/original_3d_gait_corpus/verify_corpus.py /tmp/original_gait
# Or independently:
python3 qualification/original_3d_gait_corpus/build_corpus.py --out /tmp/clean_only --variants clean
python3 qualification/original_3d_gait_corpus/verify_corpus.py /tmp/clean_only clean
```

The geometric data and 48-frame model animations are reproducible; encoded H.264 bytes may vary with platform FFmpeg/x264 version. Always use the result-local SHA256 manifest and source commit, not an assumed cross-platform hash.

## Rights, uncertainty and next experiments

All **newly generated** procedural model geometry, motion, rendered video and labels are placed under **CC0-1.0**. The dependency binaries remain subject to their own licenses. The assets do not resemble named actors or reproduce human scans, protected footage, commercial animation or identity data.

**Important:** The procedural figure is a simplified mannequin, with ellipsoidal mesh parts and IK, not anatomically photorealistic motion. “PASS” above means only that synthetic source-control oracles match their explicit expectations. It does **not** mean a person walks naturally, the model obeys forces/torques, learned image-pose models generalize, or a character is suitable for release. Product CPE, actual-person consent, licensed-model production, private visuals, and corrective-flywheel acceptance are separately held by their owning DLE.

**Next independent bakeoff:** feed `clean`, `knee_reverse`, `foot_slide` *same native H.264 clips and joint labels* to the independent #360 geometry, #361 temporal pixel, #364/#366 pretrained CoTracker3, and #365 modal adjudication workcells. Score true positives, false negatives, occlusions, temporal instability and source/pixel geometry custody rather than inferring science from green workflows.

**Lifecycle:** draft research artifact, no merger/release; durable Git source and CI artifact SHA, legible structured receipts for human/assistive-tech review, executable reproducible pure-source generation for automation and agents.
