# R015 independent prior-art bake-off — first native execution & operating assessment
Date: 2026-11-12 | Authority: private Stable Character DLE #141 | Status: **RESEARCH / NO ACCEPTANCE / NO MERGE**

## Evidence and reproducibility

**Source branch / draft PR:** https://github.com/SemperSupra/stable-character-pipeline/pull/440

**Executable parallel source-pinned CPU run:** https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43261962857

**Durable per-lane JSON receipts:** 
- `43261962857-bodyshapegpt.json` in this folder.
- `43261962857-semantify.json` in this folder.

Original public upstream pins:
- BodyShapeGPT `758bf5a1b3dbd12984de6f68ad4d3bf8c95ef409`, paired dataset SHA256 `e093c965d58a44ddd499d19452d9a71d0ccf70863cd2a54d58c60f2de9a42e65`.
- Semantify `78b001d3dc4ea4efa428e3aff1213cefddf6ebd8`, native C2M architecture source SHA256 `3e48516d467ff0ea2b8fd426f7e5f554441c58424c382278bb23c5f24ea28147`.
- GitHub Actions `ubuntu-24.04` 4 detected CPUs, Python 3.12.3, disposable `$RUNNER_TEMP` venv. Code/test isolation via pinned git revision, source/class-only AST import, no third-party setup scripts run, no secrets supplied, checkout with non-persistent credentials.

## Follow-up — actual original Semantify checkpoint execution (2026-11-12)

**Run:** https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43264747293

**Immutable receipt:** `43264747293-semantify-actual-pretrained.json` in this directory; source commit `e777d4c9f037ef821f209243ed6a786fc7fa8d71`; original archive SHA256 `91682ac20d450f02c02f97e99ab5858fc12e0f15dbcedbd1e8d2bb4c244a72c2`; SMPL-X neutral checkpoint SHA256 `7bb79747504919656ecacb120b5be70b51b6faac1535d1cfd7f46b1401a3ed7b`.

The original author's published Google Drive archive was downloaded through verified TLS into a bounded disposable runner (23,264,694 bytes; 25 archive entries), validated for safe paths and file-size limits, and **never committed/uploaded**. Static Python pickle opcode inspection showed its Lightning checkpoint stores tensors along with legacy OmegaConf 2.3.0 metadata. The first `torch.load(weights_only=True)` correctly rejected the metadata. After exact archive/checkpoint SHA enforcement and an *explicit narrowly scoped allowlist limited to audited OmegaConf/Python metadata types*, the same **`weights_only=True`** loading mode succeeded. **Unrestricted `weights_only=False` was never used.** This still requires separate third-party model/checkpoint rights review for redistribution or service deployment.

The true pretrained SMPL-X neutral mapper (not a reconstructed toy MLP) has **8 semantic score inputs**, hidden layers `[800,500]`, and **10 shape beta outputs**. Its metadata descriptors are: `fat`, `masculine`, `long torso`, `hourglass`, `tall`, `rectangular`, `small`, `proportioned`. A fixed synthetic score vector of `0.25` per descriptor produced a finite ten-float coefficient vector; a repeated identical input matched exactly (`max_abs_delta=0`), and a +0.05 perturbation to the first descriptor produced a vector L2 delta of `0.01904796`. Observed forward pass **0.000601 s** on that one input; NOT a statistical latency service benchmark or CLIP-encoded natural-language prompt test. Neither a licensed SMPL-X 3D body mesh nor actual CLIP score extraction was invoked. No geometric output/body fidelity, physical age or photorealism has been qualified.

**Updated differential:** Semantify's original published *numeric mapper* now has actual reproducible CPU evidence. BodyShapeGPT's original 8B Llama+LoRA path remains blocked pending base/weights and authorized accelerator. The native end-to-end visual/metric comparison remains **HOLD**, as original techniques differ in input format and neither has rendered measured mesh evidence in this bakeoff. The Semantify numeric CPU result favors exploring compact trained mapper deployment, **not** selecting it on morphology quality.

---

## Observations

### A: BodyShapeGPT — actual public data, NOT pretrained LLM

Parsed **21,000/21,000** public pairs, zero parse errors; **19,429 unique case-folded description hashes**. Deduplicate normalized description *before* deterministic held-out split. Use bounded 6,000 train and 600 held-out samples. **Native unit:** ten gender-neutral SMPL-X shape betas, not metric cm or real-person identity.

| CPU baseline | Held-out MAE across 10 betas | Relative to mean |
| --- | ---: | ---: |
| Train-set mean beta vector | 1.140213 | 1.000 |
| TF-IDF(1–2 gram) + Ridge(10.0, lsqr) | **0.915750** | **0.80314** |
| TF-IDF nearest description cosine | 1.300534 | 1.14061 |

Model-fit+inference timing: **0.321 s** measured for this small capped task (not service cold start or native Llama inference). Ridge improves average beta MAE by **19.7%** relative to constant mean; this is **not** evidence of millimeter or centimeter mesh accuracy. No model output images/meshes were created.

**Native parser falsifiers confirmed:** original `demo.py::parse_betas` does NOT require exactly ten numbers, ignores integer-only output, and can include float values mentioned in the prompt before the model-generated result (example age/height numeric leakage). Source behavior is unsuitable as an accepted production contract; replace with strictly structured ten numeric fields, bounds, finiteness, token position and optional model-generated confidence.

**Native LLM status: BLOCKED.** Original model uses separately obtained base `meta-llama/Meta-Llama-3-8B`, separately hosted LoRA safetensors from OneDrive (repo provides only `weights/adapter_config.json`), and GPU CUDA with bitsandbytes 4-bit. The upstream demo sets `trust_remote_code=True`; this must be security-reviewed in disposable execution with code hashes and explicit permissions. No gated credentials, protected files or private GPU were used.

### B: Semantify — actual native C2M architecture, NOT published pretrained mapper

Executed exact upstream `C2M` neural module class from pinned source via isolated AST in modern torch `2.5.1+cpu` (without importing legacy render/Lightning stack). Trained a **6 descriptor -> 10 beta** nonlinear MLP for 175 deterministic Adam steps against an analytic synthetic target. Held-out mean-square error: **0.552177 -> 0.028206**; constant-mean target baseline **0.525216**. Reported train step time **0.106 s** (not environment provisioning, real CLIP extraction or geometry creation). Output shape [112,10], finite. This qualifies native architecture CPU viability *only*. Synthetic data has no claim to reproduce the paper's descriptor distribution or parameter quality.

**Initial native published mapper status: BLOCKED at first rep; later numeric-only checkpoint loading passed (details below).** Publisher's `get_mappers.sh` fetches an unpinned Google Drive zip using `wget --no-check-certificate`. Do not run as published. Registration/licensing separately required for SMPL/SMPL-X and other human mesh model weights; legacy `requirements.yml` pins Python 3.8.13, CUDA 11.1, PyTorch 1.9.1, PyTorch3D 0.6.1. Trainable current PyTorch class does not establish compatibility of older renderers/CLIP components, data-loading dependencies, pretrained checkpoint, or geometries. A PyTorch warning about absent NumPy in the minimal torch-only venv was nonfatal; a production dependency closure must explicitly pin/verify NumPy and compatible platform wheels.

## Differential readiness

| Dimension | BodyShapeGPT | Semantify |
| --- | --- | --- |
| Original task | Free natural language -> 10 neutral SMPL-X betas | CLIP descriptors -> native 3DMM coefficients |
| True prompt-to-params in released implementation | Yes, **when base+LoRA available** | Needs descriptor encoder / scores |
| Original artifact availability | Public 21k paired dataset; LoRA off-repo; base access gate | Mappers off-repo Google Drive; mesh models separately licensed |
| Actual free-tier tests this rep | All pairs parsed, held-out regression proxy, original parser negative controls | Exact original C2M network trained/evaluated CPU on synthetic function |
| Native published checkpoint executed | **No** | **Yes: after follow-up, safe-loaded actual published 8→10 neutral mapper; numeric-only** |
| 3D geometry/rig quality | **Not measured** | **Not measured** |
| Deployment footprint | Heavy 8B LLM + quant GPU; expensive cold start | Small mapper on CPU; CLIP+renderer heavier and separately versioned |
| Unlocked native mapping to MPFB/MHR | **Not demonstrated** | **Not demonstrated** |
| Qualification conclusion | Useful released supervision dataset; untrusted text parser; native inference blocked | Portable learnable architecture; published pretrained and geometry blocked |

These methods cannot be ranked on 3D human fidelity from the current outputs. The two loss scales are **different** (SMPL-X beta MAE vs synthetic descriptor-to-beta MSE), and direct numeric comparison is prohibited.

## Implement, build, deploy and O&M plans (conditional, not authorized release)

### Build
1. **Capture exact rights and supply-chain bill of materials:** authored code MIT; independently verify Llama use rights, LoRA ownership/availability, SMPL-X usage/redistribution, Semantify mapper weights, CLIP and third-party dependencies. Never silently imply code license covers model assets.
2. **Reproducible disposable builds:** pinned upstream source SHAs and dependency wheel lock+hashes; immutable OCI layers or GHA one-shot runners; least privileges, `contents: read`; no persistent host installations or third-party scripts with disabled TLS. Separate untrusted weight ingestion stage from executable model runtime. For PyTorch checkpoints require restricted `weights_only=True` handling where compatible and strict expected tensor structure.
3. **Typed service contract:** `{description, resolved_concepts, explicit_measurements, backend, backend_version, seed, constraints}` -> top-k `{parameter_vector, coefficient_units, uncertainty, provenance, reject_reason}`. Require exactly expected coefficient count, finite bounded floats, versioned schema, no numbers from unrelated prompt text.
4. **Reconstruct original pretrained pipelines before retraining**: native BodyShapeGPT LoRA/Meta base with authorized credentials on admitted free GPU if available; Semantify mapper with fixed hash+rights on CPU and CLIP descriptors; independently instantiate licensed SMPL-X mesh and measure actual shape. Keep pretrained weight acquisition and training distinct from native adapter development.
5. **Hold adapters until benchmark comparison**: separately design MPFB and MHR backend schemas and inverse fitting; do not copy SMPL-X coefficients into unrelated parameter spaces.

### Deployment
- **Research:** ephemeral GitHub public CPU runners for open-source/publicly reproducible work, limited to 15 min/job with receipts. Kaggle/Colab free GPU only via admitted one-shot jobs when model rights, public inputs, quotas, tokens and source isolation are solved. No assumption of permanently available free GPU. Never private data on public runners.
- **Production candidate:** stateless worker image for each adapter; worker cold-start fetches/pins artifacts by digest from permitted content-addressed storage, validates licenses and checksum, serves one bounded request or finite batch, writes only explicit approved outputs; no host pollution. Go scheduler/CLI + Python isolated ML backend if justified; never embed private CPE semantics in public image.
- **Human / automation / agent:** shared typed request+receipt, editor shows editable constraints/candidate variants, CLI JSON operation, agent protocol offers safe declared capabilities, fail-closed native asset gating and independent policy membrane.

### O&M controls
- Observe model+checkpoint hashes, input concept version, schema, source licenses, dependency CVEs, GPU RAM/CPU throughput, cold-start, memory/disk, queue admission, p50/p95 latency, inference failures, coefficient-validity errors, geometry residuals, bias/semantic drift, and rejected requests.
- Retain immutable provenance receipts; keep runtime model artifacts separate from repositories; preserve rights before any public mirroring; restore by exact digest/rollback. No external persistent training job loops on Kaggle/Colab.
- Backups: source/control state in Git/DLE; datasets in separately licensed versioned custody; generated candidates with reproducible seeds and independent audit metadata. Worker filesystem disposable.
- Promotion: require third-party checkpoints available and rights verified, hard-negative prompt/descriptor tests, true native mesh unit/landmark measurement results, holdout provenance, independently reviewed subjective morphology, skin/rig/animation R014 acceptance. **No merges/releases until owner gate.**

## Red-team / blue-team findings

- **Risk:** Cross-language/adjective mismatch, source parser prompt-number leakage, normalized duplicate descriptions, unregistered proprietary mesh assets, TLS-suppressed model downloads, pickle checkpoint code execution, model version drift, latent parameter non-identifiability, invalid body measurements, false confidence from synthetic losses.
- **Mitigation:** CPE canonical concept projection + explicit unit constraints; hard-negative and lexical-collision suite; group-aware holdout of paraphrases/shapes; strict schema parse; pinned TLS-verified artifacts with content digests and rights; safe tensor loading; independent mesh measurement and rejection; top-k uncertainty; exact-seed replay; independent external generation policy membrane.

## Research choice

**Keep both tracks for next gate.** BodyShapeGPT is the strongest direct language-to-parameter comparator and supplies high-value public paired data; Semantify offers the more straightforward template for retraining native MPFB/MHR backend-specific small mappers. No winner on geometry fidelity may be declared until native source weights, licensed 3DMM geometry and common held-out adult-description measurements are actually available. Source-only and architecture smoke results are evidence of feasibility, not readiness.

## Next bounded gates

1. Independently check distribution endpoints for published weights with TLS verification, **no code/weights execution**, no private tokens.
2. COMPLETED PARTIALLY for Semantify: archive/checkpoint SHA, safe-loader static audit and native numeric forward; NEXT obtain verified actual CLIP descriptor scores and licensed SMPL-X geometry, then evaluate meaningful held-out adult descriptions. BodyShapeGPT remains blocked without original base/LoRA rights/access.
3. On a *common*, independent adult morphology benchmark, compare coefficients, reconstructed mesh dimensions, throughput/VRAM, monotonic concept edits, semantic generalization across languages, reliability/abstention and operator effort.
4. Only after a qualified comparison, design CPE-to-MPFB/MHR mapping adapter DoE and minimum v0.0.1 build/deploy/O&M acceptance plan. Do not start that native adapter yet.
