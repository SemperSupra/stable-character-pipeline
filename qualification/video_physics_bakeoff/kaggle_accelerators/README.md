# Video quality RDT&E — Kaggle CPU / GPU / TPU workload candidate

**Owning authority:** public video QA [DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), research root draft [PR #356](https://github.com/SemperSupra/stable-character-pipeline/pull/356), protected production DLE [private #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). **Executor authority:** [Agent Dispatch private Kaggle DLE #638](https://github.com/SemperSupra/agent-dispatch-private/issues/638) and the existing `SemperSupra/agent-dispatch` `kaggle-rdte-executor.yml`. No new repository, scheduler, shell gateway or privileged workflow.

## Candidate scientific payload, not yet a provider assignment

`videoqa_kaggle_probe.py` performs one fixed rights-original synthetic metric across three compute venues. It generates eight 32-frame 2D planted-foot traces: four stationary controls (expected speed 0 m/s) and four deliberate skates (expected mean speed 0.20 m/s). It tests a physically meaningful **measurement method**, not observed human motion or an automated video restoration system. Source and measurements have SHA256, explicit expected verdicts, no external assets, and fail-closed cross-backend numerical tolerance.

- **CPU:** Python standard library; genuine scalar position/time computation and numerical oracle.
- **GPU:** PyTorch CUDA on **both** requested NVIDIA T4 devices, independently activated and synchronized. A CPU-only PyTorch build or fewer/different devices fails.
- **TPU:** JAX/XLA `pmap` over **all eight** requested TPU devices, with `block_until_ready`; CPU JAX fallback fails.
- All backends return a JSON receipt with requested vs observed backend, source SHA256, per-case speed, verdict, device observations and scientific limitations. A successful Kaggle kernel upload is **not** a computational PASS without independent provider-native observation.

## Real execution in this source branch

On an isolated disposable CPU work directory:

```bash
cd qualification/video_physics_bakeoff/kaggle_accelerators
python3 -m unittest -v
python3 videoqa_kaggle_probe.py --backend cpu
```

Tested 2026-11-11: **7/7 independent unit controls PASS**. Same source executed on a CPU-only environment with `--backend gpu` and `--backend tpu`: both exited 2 without pretending that an accelerator was available. Exact committed Git blob SHA IDs: `videoqa_kaggle_probe.py` `d7c23c375170d1584c580d90961da5efb7d43e4b` and `test_videoqa_kaggle_probe.py` `f43992127f58bb2347ac89a008eb5250c63f3362`, matching the locally executed source bytes. **Actual Kaggle CPU/GPU/TPU runs are not performed or claimed.**

## Existing Agent Dispatch admission sequence

The existing protected launcher currently recognizes three **other** fixed workloads: `gpu-cuda-smoke-v1`, `tpu-v5e8-device-v1`, and `tpu-jax-bridge-v1`; it does not yet admit the video QA payload or a CPU variant. Propose three *reviewed typed* extensions (not arbitrary script selectors): `videoqa-cpu-motion-v1`, `videoqa-gpu-t4x2-motion-v1`, and `videoqa-tpu-v5e8-motion-v1`.

1. Reconcile previously submitted Kaggle GPU experiment `gpu-t4x2-20261014-080203` native version **1** and current quota **without duplicate submission**. First qualify the already reviewed CUDA two-device and TPU JAX eight-device hardware proofs; device success is not this science experiment's success.
2. In Agent Dispatch, add only exact source-SHA-bound fixed reviewed workload IDs and output-schema oracles to its existing typed workflow/Sidecar. No new credential, authority, dispatcher, cron, generic argument, dynamic URL or environment.
3. For CPU, add an explicit CPU quota/runtime admission branch rather than incorrectly treating CPU as TPU in the existing `quota_ok` helper. For GPU/TPU, verify *provider observed* remaining entitlement and reserve, one active assignment, no retry, short bounded execution and native notebook version.
4. When an explicitly authorized DLE delegation/assignment exists, the protected controller copies the fixed source into the ephemeral private Kaggle notebook, with Internet disabled and no protected data. Use pre-existing Kaggle runtime packages only if tested (GPU torch, TPU jax); any extra dependency is isolated to that notebook or its disposable build stage. Do not contaminate `~/.local`, `.local`, host VM or long-lived model caches.
5. Read back exact Kaggle account/kernel/version, actual device arithmetic, input SHA and JSON output digest; compare scientifically against the **independent standard-library CPU oracle**. Track walltime, compute quota delta and provider terminal result. Inconsistent/missing results fail closed.
6. Keep protected character media and model weights outside public Actions/Kaggle. A separate licensed/public-original rights gate is mandatory before replacing synthetic data with real decoded clips or an external model.

## Candidate next-wave placement

| RDT&E lane | Likely starting work | Current readiness |
| --- | --- | --- |
| Kaggle CPU | Deterministic geometry, timing, PSNR/SSIM, FFmpeg and frame extraction | Local proven methods; Kaggle CPU adapter not admitted |
| Kaggle GPU T4x2 | CoTracker3 small tracking, DOVER-Mobile, pose estimators, selected PVBench components | Source pinned; native CUDA receipt unverified; models/checkpoints not installed |
| Kaggle TPU v5e-8 | JAX/XLA motion-temporal arithmetic and larger batched spatiotemporal scoring; optional future JAX-native learned evaluator | JAX source candidate tested only on CPU negative; native TPU unverified |
| Not presumed feasible | Full HumanScore, PhysTrace, PVBench and RoboJudge 9B | Gated dependencies, CUDA kernels, 16GB-per-GPU/20GB saved workspace limits and model implementation differences require separate install/memory qualification |

**Exit status:** SOURCE_AND_CPU_ORACLE_LOCAL_PASS / KAGGLE_CPU_GPU_TPU_NOT_DISPATCHED / GPU_NATIVE_V1_UNKNOWN / QUOTA_UNKNOWN / ADMISSION_NOT_GRANTED / PRODUCT_RELEASE_HOLD. Reconcile in existing DLE rather than creating a new authority.
