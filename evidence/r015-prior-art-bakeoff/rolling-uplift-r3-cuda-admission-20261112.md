# R015 rolling uplift R3 — initial modern framework bakeoff / CUDA admission
Date: 2026-11-12 | Ownership: Stable Character R015 private #141 | Disposition: **RESEARCH / HOLD**

## Goal and continuity
This is a **stacked draft** on the original source-pinned [PR #440](https://github.com/SemperSupra/stable-character-pipeline/pull/440), not a replacement for original-method evaluation. Run a continual sequence of **baseline → uplift → cross-version replay → robustness/quality → new model challenger → modernized head-to-head**. Preserve original source results so new versions cannot be promoted solely because they are newer. Human/automation/agent contracts must all use the same typed recipe and provenance records.

## Completed zero-cost original-pretrained-model Python/PyTorch 2.5 to 2.14/2.15 uplift
[Free public GHA CPU run #43283058478](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43283058478) **both matrix jobs PASS**.

Original pinned Semantify 8→800→500→10 network source SHA `78b001d3dc4ea4efa428e3aff1213cefddf6ebd8`, original author SMPL-X neutral checkpoint SHA256 `7bb79747504919656ecacb120b5be70b51b6faac1535d1cfd7f46b1401a3ed7b`, original source-pinned CLIP 8-score/10-beta fixture from [run #43278119546](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43278119546) with CLIP model SHA `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`.

**Observed failure in direct current framework load (retain negative evidence):** earlier [run #43282492312](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43282492312) passed torch2.5.1 but the legacy OmegaConf `collections.defaultdict` object was rejected by torch2.14 and torch2.15 restricted `torch.load(weights_only=True)`. Never used `weights_only=False`.

**Correction and actual execution:** in an isolated ephemeral environment, torch2.5.1 first loaded the exact hash-pinned original author checkpoint through previously audited OmegaConf-only allowlist with `weights_only=True`, then wrote **only its six state_dict tensor arrays** to ephemeral `safetensors` (1,651,336 bytes, SHA256 `82b2c8bf00cbec99a12935a6a89a3aa6b17b63352f83c78ca1e54b49a108f939`). The original checkpoint and converted trained weights **were not committed or redistributed**. A completely separate Python environment loaded that SafeTensors file using original source `C2M` under each new torch version.

| Source-native modern runtime | Status | Max absolute error vs actual author CLIP→mapper 3×10 benchmark | Deterministic replay |
|---|---|---:|---:|
| Torch 2.5.1 restricted importer | PASS, known baseline | Prior raw-CLIP reference | PASS |
| Torch 2.14.0+cpu + SafeTensors | **PASS** | **0.00000298** | 0 |
| Torch 2.15.0+cpu + SafeTensors | **PASS** | **0.00000298** | 0 |

Threshold predeclared `max_abs_delta <= 0.0003`; both passed with >100× margin. Actual benchmark inputs were source CLIP logits on three synthetic adult silhouette images, replayed from immutable original-source reference; modern target framework jobs did not rerun CLIP to conserve GHA time. These are genuine author pretrained weights and original author network architecture, NOT new training, licensed SMPL-X meshes, full production geometry, photoreal rig quality or GPU results. Exact per-job receipts are next to this report.

## CUDA 12 / CUDA 13 TrueNAS conditional host assessment
Owner reports CUDA 12.x on TrueNAS; **do not assume unsupported GPU hardware**. NVIDIA RTX A5000 is Ampere SM86 supported by CUDA13. Ordinary CUDA13 native applications require NVIDIA Linux driver **R580 or newer**; host CUDA toolkit can remain 12.x if runtime is provided in a properly isolated CUDA13 container, **but the host NVIDIA kernel driver must support it**. A displayed `nvidia-smi CUDA Version: 12.x` usually indicates an older driver that does not satisfy the general CUDA13 requirement. Read-only check:
```bash
nvidia-smi
nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv
```
Before admission, record installed TrueNAS SCALE release, NVIDIA driver, GPU name, GPU capabilities and container runtime without writing anything to persistent hosts. No manual host driver upgrade permitted; TrueNAS-supported update/compatibility path requires separate owner approval. NVIDIA forward-compat packages are scoped to supported data-center/select NGC-server-ready RTX systems and must not be assumed to cover the A5000 in this configuration; no unqualified compatibility hacks.

If current driver <580, train CPU torch2.15 in public disposable GHA, and train GPU torch2.14 **CUDA12.6** on TrueNAS only if driver/runtime checks qualify. Do not let the CUDA13 hardware policy stall the body-shape bakeoff. A GHA CPU pass cannot establish CUDA12 or CUDA13 execution on TrueNAS.

NVIDIA sources: https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html , https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html , https://developer.nvidia.com/cuda/gpus .
PyTorch source: https://github.com/pytorch/pytorch/blob/main/RELEASE.md , releases 2.14 CUDA 12.6 profile / 2.15 CUDA13-only binaries.

## Next independently gated workcells
- **Parities:** Torch modern CPU+saved checkpoint, optional ONNX/MLX tensor port without model weights escaping isolated environment; FP32/FP16/BF16 and batch N=1,4,8 benchmarks with strict error tolerances.
- **Representation:** Versioned intermediate anthropometric/constraint vector, independent from SMPL-X/MPFB/MHR; CPE semantic source tags remain unpromoted.
- **Encoder:** Original OpenAI CLIP vs OpenCLIP/SigLIP2 (a new encoder requires retraining corresponding mapper; cannot reuse old 8-logit checkpoint directly).
- **Description:** TF-IDF/Ridge and original BodyShapeGPT as historic baselines; modern small Qwen LoRA when admitted free GPU and model rights resolve; project cannot claim published original Llama fine-tune ran.
- **Native geometry:** Licensed and documented actual 3DMM/MPFB/MHR geometry measurements with stratified holdouts; R014 full rig, hair/skin and motion QA separate and currently HOLD.
- **Deployment and O&M:** Source/model/weight hashes and rights, cold start, p95, CPU RAM / GPU VRAM, batch tensor equivalence, concept provenance, uncertainty and abstentions, safe model format, rollback and immutable receipts.

No merge, release, model promotion, unlicensed assets, private media on public cloud, or host upgrades. 
