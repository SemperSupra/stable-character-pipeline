# R009 — Human-inspired corrective walking animation (fictional source only)

**Status: VISUAL/MECHANICAL RESEARCH CANDIDATE — NOT HUMAN-APPROVED OR RELEASE-READY.**

## Why the original walk failed

The original fictional-character generator animated the lower limb with independent sinusoidal knee rotation rather than computing the foot trajectory from pelvis, hip, knee, and ankle. Its knees were rotating in the wrong flexion direction, the foot was not planted during stance, its hip stayed effectively stiff, and its arm-elbow channel was too small or incorrectly phased. The heading-only correction fixed sideways facing but did not fix gait: 89/131 near-floor proxy pairs still moved >8 cm/frame. Those earlier pair counts were based on a broader near-floor heuristic and must not be compared as identical ground-truth stance windows with the new controller.

## Gait reference evidence and design

Human gait references (normal adult level walking, not a universal range applicable to all ages, speeds or contexts):

1. [Normal Gait, Atlas of Limb Prosthetics / O&P Virtual Library](https://www.oandplibrary.org/alp/chap13-01.asp) describes approximately **60% stance / 40% swing**, hip ~30° flexion around heel contact, progression into ~10° extension, knee early-stance loading flexion ~15°, midswing flexion ~60°, and ankle plantar/dorsiflexion through stance and swing.
2. [Gait Assessment and Intervention Tool, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9405699/) reports normal initial and midswing knee flexion in the ~40–60° and ~60° ranges, with near-neutral ankle by mid/terminal swing.
3. [Park et al., 2008, Synthesis of natural arm swing](https://pubmed.ncbi.nlm.nih.gov/18417138/) specifies arm swing paired with the **contralateral** advancing leg.
4. [Elbow load during arm swing, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10277704/) reports mean elbow flexion/extension ROM ~29.7°±10.2° in a 15-participant gait study. This informs a target, not an individual identity reference.

## Implemented corrective animation

- Exact owner-authored source-bound glTF input GLB: `r009-aster-juniper-original-heading-aligned-REVIEW.glb`, SHA-256 `837dbd91e5851072b7f4d5f31fdeb5517c19f85e913e829e5e488406f374f651`.
- Complete 72 frames at 12 fps (six-second H264), two characters, each 17 skin joints; 28 glTF animation channels (original 22 + animated ankle and pelvis channels). Geometry, original skin weights, materials, and upstream original binary are unchanged.
- Source-specific **two-link sagittal leg IK** solves the ankle world target for a bent knee. Stance foot is anchored in world space for 60% of each cycle with heel rise/foot roll near toe-off; swing lifts and advances the knee, ankle and shoe for 40%. Stride period 1.6 s, root advance 2.56 m / 6 s.
- Source-specific pelvis vertical bob and separate ankle pitch; no standing knee-only pivot. Contralateral right arm advances when left leg leads; shoulder and elbow both receive smoothly varying authored motion. Different cycle offset for the second character.
- Actual controller ranges measured: hip -7.3° to +26.9°, knee 5.5° to 60.0° flexion, ankle local rotation -9.4° to +31.5°, shoulder -18.3° to +18.3°, elbow ~5.2° to 33.8°. Ankle is not validated against a calibrated biomechanical coordinate convention.

## Independent verification (not producer-only output)

- 14/14 offline Python unittest source and adversarial tests PASS (NumPy/SciPy dependencies) (exact SHA pin; no source overwrite; source rights class; missing bones/skins, malformed GLB, multiple clips, nonphysical IK reach).
- 32/32 additional input, skin, pose, foot, strain, and media checks PASS. Genuine weighted glTF mesh, inverse bind matrices, all 72 frames and all four shoes independently reevaluated.
- Full-body actual skinned sole centroid movement in the **bounded interior stance** (excluding heel strike and toe off), combined 81 adjacent same-foot frame-pairs: 0 exceed 20 mm; maximum observed 0.273 mm/frame. Boot bottom minimum near y=7.1 mm aligns within ~0.4 mm of the renderer walkway top at y=7.5 mm; this is a stylized geometry proxy, not physical force/contact.
- Four independent H.264 videos (side, oblique, Aster close annotated joints, Juniper close annotated joints) each ffprobe-validated **72 frames**, 12 fps, 960×540, decoded without FFmpeg errors. Two-camera actual rendered visual sheets manually examined; foreground occluders removed in oblique camera.
- Topology unchanged and deforming skin observed; sampled per-triangle edge stretch p99 worst ~37.5% (ochre trousers). This is material deformation that still needs authoring/skin smoothing, not a full skin-quality acceptance.

## Limitations and holds

The original fictional models are **stylized 17-joint figures**: no forefoot/toe joint, foot-pressure sensor, balance dynamics, inertial feedback, independently motion-captured marker trajectories, facial realism, natural clothing dynamics, or detailed biomechanical joint coordinate systems. Current standing/stance estimates, sole motion and sampled edge strain do not guarantee natural gait. Human review of leg posture, hip extension, elbow swing, knees and feet is mandatory. **MVP natural motion, motion-training admission, release/merge and all original private Naomi/Alison rights and source-runner holds remain unchanged.**

### Storage and audiences

- Git/authoritative DLE: scripts, tests, operator notes, source SHA, falsification results, link/index and exact next executable baton.
- Owner Google Drive: original-derived GLB, complete videos, side/oblique/close-up review sheets, joint trajectory chart, scientific receipt.
- Human: view videos and reference joints; automation: deterministic CLI + machine JSON exit status; agent: inspect the same schema without hidden source or unrestricted media authority.

Next READY: independently calibrate joint axes and skin ROM against genuine rights-cleared motion capture, author actual foot heel/ball/toe and dynamic roll, reduce pants edge strain, add gait initiation/termination transitions and physically measured stance oracle. Run actual native Blender and camera/source parity as independently authorized; the current CPU mesh renderer is not a substitute for a Blender-native acceptance packet.

## Developer reproduction

The source GLB is a private owner Drive artifact, not vendored into public Git. In an authorized local workcell, supply the original owner-controlled GLB path as `R009_GAIT_SOURCE`, then run:

```sh
export R009_GAIT_SOURCE=/path/to/r009-aster-juniper-original-heading-aligned-REVIEW.glb
python -m unittest -v test_gait_v2
python gait_v2.py --source "$R009_GAIT_SOURCE" --out ./aster-juniper-anatomical-v2.glb --receipt ./gait-v2-initial-receipt.json --sha256 837dbd91e5851072b7f4d5f31fdeb5517c19f85e913e829e5e488406f374f651
python render_v2.py --glb ./aster-juniper-anatomical-v2.glb --out . --width 960 --height 540
python qualify_v2.py
```

Requires Python 3 with `numpy`, `scipy`, `VTK`, `Pillow`, `matplotlib` plus an installed `ffmpeg` and `ffprobe`. A full native Blender operation has *not* been performed in this particular corrective batch. Do not run unreviewed vendor character sources on a public runner; do not mistake the skeleton-driven prototype for motion capture.
