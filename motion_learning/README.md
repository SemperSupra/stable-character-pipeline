# Human and quadruped motion learning — synthetic TPU research

Research-only, original procedurally generated human and quadruped joints. No real-person media, third-party source assets, pretrained weights or biologically valid ground truth. This code is safe to qualify on public CPU runners; final identity-bearing character data must remain private. The human and fauna product authorities remain separate even though they share a technical test harness.

## Source and data

- Human: 18 stylized joints; walk, jog, wave, turn.
- Fauna: 17 stylized quadruped joints; walk, trot, gallop, turn.
- 128 distinct sequences × 48 frames at 24 FPS, each joint in XYZ coordinates. Split by entire sequence: 96 training / 32 validation. Four-frame input predicts the next pose.
- Original deterministic generator seed 20261027, NumPy float32. SHA256 is over raw contiguous tensor bytes, not the .npy or .npz container.
- Expected source digests: human 9af4d9679255fa604d471fcf5e415a6d5bd69ed141eead6da1ef085db8a86e5c; fauna 2fb6c34380dabcc176a66c735a3aedbbddf2a9381240cd379614d10c45a5cca3.

Generator source and dataset receipts belong to this public research branch. Durable data, manifests and CPU result/checkpoint bundles are on Drive under Stable Character Pipeline > Unsorted as motion-tpu-synthetic-human-fauna-20261027.zip. A Drive upload is NOT a Kaggle dataset.

## Reproduce without GPUs

Python 3.10+ with NumPy and JAX:

    cd motion_learning
    python3 -m unittest test_motion -v
    python3 synthetic.py human --output outputs/human-dataset --nseq 128
    python3 synthetic.py fauna --output outputs/fauna-dataset --nseq 128
    python3 train.py --domain human --backend cpu --steps 120 --output outputs/human-cpu
    python3 train.py --domain fauna --backend cpu --steps 120 --output outputs/fauna-cpu

This is one-step residual pose learning and 24-frame autoregressive prediction, not a realistic human/animal motion-diffusion model. The current independent CPU test shows it beats persistence at one-frame prediction, but still has substantial 24-frame rollout error. It does not prove correct contacts, stable skeletal lengths, or realistic locomotion.

## Kaggle and Agent Dispatch gates

The existing protected public Kaggle controller has only three reviewed workload choices: gpu-cuda-smoke-v1, tpu-v5e8-device-v1 and tpu-jax-bridge-v1. Do not overwrite or impersonate those identifiers. New tpu-human-motion-v1 and tpu-fauna-motion-v1 workload types need separate reviewed admission plus self-contained, source-pinned Kaggle packaging and trusted provider-native evidence.

The TPU learner requires eight real TPU devices; JAX pmap averages gradients across replicas. TPU and live Kaggle execution remain UNTESTED. One active or queued Kaggle job per account; observe the old GPU v1 before considering a duplicate. Generate data from exact source offline on Kaggle; do not import private character assets. Proposed Kaggle dataset slugs scp-human-motion-synthetic-v1 and scp-fauna-motion-synthetic-v1 do not yet exist as verified uploads.

Next: exact-head public free CPU CI, reviewed controller extension, eight-device TPU preflight, run separate human and fauna notebooks, retrieve/check native version and all hashes, prove 24-frame rollout and contact/bone-length quality, then evaluate a temporal transformer or motion-diffusion baseline.

Human authority: SemperSupra/stable-character-pipeline-private#35. Fauna authority: SemperSupra/stable-character-pipeline#5. Execution: SemperSupra/agent-dispatch-private#638. No merge/release/deployment or private hosted Actions.
