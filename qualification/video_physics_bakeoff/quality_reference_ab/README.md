# Reference-based video A/B — synthetic CPU RDT&E
This is an independent *sibling* of the hardened-oracle (#357) and kinematic-correction (#358) workcells, subordinate to the public QA DLE #150 and root bakeoff #356. It modifies no other workcell.

## Replay
On a fresh disposable Linux worker with FFmpeg 5+ (libx264 and ffv1 encoders), FFprobe and Python 3 standard library:

```bash
OUT_DIR="$(mktemp -d)" bash qualification/video_physics_bakeoff/quality_reference_ab/qualify.sh
```

The workflow runs the same operation on a standard public `ubuntu-24.04` GitHub Actions runner. All evidence is temporary, and only the compact JSON receipt is uploaded. No models, caches, secrets, private assets, licensed media, paid services, persistent user installations or external Python packages.

## Experiment
Generate a fully synthetic 36-frame 160x120 12fps lossless reference. Make a deliberately low-resolution/low-quality baseline. Re-render a bounded improved candidate from that *same* reference source, not by hallucinating data. Decode the actual H.264 output and compare all 36 time-aligned frames against the independently retained reference using FFmpeg PSNR and SSIM. Record SHA256 for each video and strict frame count/shape. The reviewer must distinguish this valid source re-render from learned video restoration.

**First RED and correction:** without `-frames:v 36 -fps_mode passthrough`, the FFmpeg filter pipeline delivered 37 score records for 36 decoded reference frames, despite input files each being 36 frames. The output now explicitly sets the frame count; the scoring tool refuses missing or extra records.

**Observed initial local replay (not hosted CI):** baseline 23.6058 dB / SSIM 0.8567; candidate 33.8647 dB / SSIM 0.9304. Differences +10.2589 dB / +0.0737. Hostile test cases for missing score frames, duplicate scores and nonfinite scores reject as intended.

The provisional positive verdict demonstrates a basic reference-based *rendering fidelity* improvement. It does not establish general physical realism, human walking naturalness, identity, causality, an actual generated-video restoration method, production acceptance or AI model efficacy.

## Three-audience consumer contract
Human: plain text explanation and JSON receipt, accessible keyboard-and-screen-reader interpretation through the existing QA tool. Automation: nonzero exit on inconsistent evidence and exact source SHA receipts. Agents: read-only finding interpretation and candidate proposal only; no direct product or DLE status promotion.

## Next rep
Benchmark on more realistic public-original camera/motion renders and apply the same strict frame-index alignment. Separate reference-free visual metrics and anatomical/physical checks must corroborate any release quality claim. Keep all source rights, protected person, production, merge and CPE gates independent.
