# Standalone Kaggle Video-QA Capsule (Research Candidate)

This is the **consumer payload**, not a second Kaggle controller, scheduler, provider secret workflow or permanent installation. It is an independent child of public Visual QA [DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), based on research root #356 and existing CPU/GPU/TPU probe [draft #362](https://github.com/SemperSupra/stable-character-pipeline/pull/362). It is intended for the standalone direct Kaggle controller in [latent-reasoning draft #45](https://github.com/SemperSupra/latent-reasoning/pull/45), strengthened by its separate evidence-hardening draft #50. Both remain **draft/unmerged** until owner review.

## Why this exists

We already built a **direct** research pathway with a protected main-only `kaggle-research` GitHub Actions environment; it avoids Agent Dispatch admission while its eventual unified admission is incomplete. That controller currently has two fixed GPU/TPU workloads **for Latent Reasoning**, not these Stable Character video-QA experiments. Do not treat code/capsule availability as credential, provider or GPU/TPU admission.

The Video QA probe is now a single executable Python source file that can be copied **verbatim** to Kaggle `run.py` by an extended, separately reviewed fixed allowlist; it requires no CLI arguments when used in a notebook. With no CLI options, it selects TPU only after an eight-device JAX TPU observation or NVIDIA GPU only after an observed two-T4 CUDA runtime; **no CPU fallback**. The explicit `--backend cpu` remains available for public hosted GHA validation. No assets, weights, network or external model code are required; existing Kaggle GPU PyTorch / TPU JAX packages are still subject to native runtime qualification.

## Fixed capsule identity and evidence

- Original 8×32 synthetic planted-foot traces; input SHA256 `f40ded92073bc8ee9d8680b47cdd4da3a92f270ab218224e8f252e3b99639f20`.
- Four clean 0 m/s and four deliberately skidding 0.2 m/s; evaluator checks each with 0.002 m/s tolerance.
- Scientific receipt filename `videoqa_probe_receipt.json`, schema `scp.videoqa.kaggle-motion-receipt.v1`, with distinct `source_sha256` for fixture and `executed_source_sha256` for actual notebook script bytes.
- Separate `verify_direct_receipt.py` checks exact fixture hash, executable SHA, backend, eight measurements, expected verdicts, device count/models and arithmetic witness, while explicitly marking `provider_status=NOT_VERIFIED_BY_THIS_TOOL`.
- **Provider-native status, exact version, quota/rights and downloaded receipt SHA must still be verified by the trusted standalone Kaggle controller**. Self-reported device text or a synthetic receipt alone is never a native acceleration PASS.
- GPU/TPU native jobs have not been run; 12 source-capsule and 12 independent receipt tests are bounded source/CPU checks on the fresh public GitHub Actions worker, not actual TPU/CUDA tests.

## Required reviewed controller extension before real Kaggle experimentation

Prepare two fixed source-SHA-allowlisted workloads, e.g. `videoqa-gpu-t4x2-motion-v1` and `videoqa-tpu-v5e8-motion-v1`, in the existing *direct* workflow. The approved GitHub Actions controller must stage this exact repository source via pinned SHA/byte digest and refuse unreviewed branches/URLs/embedded code. For these exact workloads only, permit the known `videoqa_probe_receipt.json` schema and independent oracle; do not widen the historic Latent Reasoning workload contract or accept arbitrary file names. No dynamic command field.

- Review the existing direct PR #45 and its hardened child #50 first; no self-merge or protection bypass.
- Confirm `kaggle-research` environment and token in the **executing repo** (not inherited); only verified main-branch workflow dispatch may access the secret.
- Observe prior `ad-rdte-gpu-t4x2-20261014-080203` version 1 via its own admitted authority before submitting duplicative hardware proofs.
- Confirm real user-specific Kaggle free quota, one-active-kernel policy, fixed runtime and rights, then submit one GPU **or** TPU job and retrieve its exact-version native receipt. Do not schedule endless retries.
- Benchmark real physics/pose quality only after these numerical and hardware gates, and separately license/checkpoint-admit the chosen learned model.

## How to replay CPU-only checks

```bash
cd qualification/video_physics_bakeoff/kaggle_accelerators
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 videoqa_kaggle_probe.py --backend cpu --out /tmp/videoqa-cpu-receipt.json
python3 verify_direct_receipt.py --receipt /tmp/videoqa-cpu-receipt.json --backend cpu --code-sha256 "$(sha256sum videoqa_kaggle_probe.py | cut -d' ' -f1)"
```

Use a disposable container or public Actions VM. No host pollution, permanent `~/.local`, secrets, local actors, real-person footage or model weights. No merge, release, CPE promotion or product acceptance from these synthetic controls.
