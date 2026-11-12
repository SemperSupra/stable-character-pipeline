# R015 — Existing technique bake-off (source-pinned, public research)

This branch runs independent **BodyShapeGPT** and **Semantify** workcells on public, disposable GitHub Actions CPU runners. The harness intentionally excludes all protected media, identity data, production configuration, CPE private concepts, commercial SMPL-X assets and credentials. Public upstreams are source pinned:

- BodyShapeGPT: `baldoarbol/BodyShapeGPT@758bf5a1b3dbd12984de6f68ad4d3bf8c95ef409`
- Semantify: `Omergral/Semantify@78b001d3dc4ea4efa428e3aff1213cefddf6ebd8`

## Execution and receipt contract

`.github/workflows/r015-prior-art-bakeoff.yml` provides two independent parallel jobs, fixed CPU execution limits, no private secret permissions and JSON artifacts. `research/r015_prior_art/bakeoff.py` emits source hashes, upstream commits, method classification, quality/error metrics, dependency gates and explicit evidence scope. Job process exit zero means *tests ran*, **not** that published models were successfully reconstructed or production suitability accepted.

### Workcell A — BodyShapeGPT
- Exercise the *original upstream* `parse_betas` via isolated AST, including invalid numerical text and integer edge cases.
- Inspect the full published JSONL paired prompt/10-SMPL-X-beta dataset and calculate parse counts and SHA256; do not upload raw description rows.
- Train CPU sklearn TF-IDF+Ridge and nearest-neighbor regression on deterministic duplicate-disjoint held-out descriptions, against a mean-vector baseline. **These are research proxies, not BodyShapeGPT LoRA inference.**
- Confirm the original base Llama-3 and LoRA/OneDrive requirements. The public repo currently contains only `weights/adapter_config.json`, not the safetensors. No gated model authentication or private GPU use is attempted.

### Workcell B — Semantify
- Execute the exact upstream PyTorch `C2M` model class in a constrained AST-only source import, performing a deterministic CPU training smoke against analytic synthetic descriptors and shape coefficients.
- Verify descriptor dimensionality, gradient convergence and output numerical finiteness. This is an **architecture smoke**, not true CLIP descriptor inversion or published checkpoint inference.
- Identify checkpoint download and SMPL-X model-asset licensing prereqs. Do not execute the upstream `get_mappers.sh` because it disables TLS verification and does not pin model archive hashes.
- Until separately licensed/retrieved SMPL-X model and source-verifiable mapper weights exist, native geometry and publication-quality evaluations remain **BLOCKED**, not simulated.

## Evaluation gates

1. **PASS_SOURCE_CONTRACT**: upstream source pin is matched and source/readme/assets obligations identified.
2. **PASS_DATA_DERIVED_PROXY**: independent prompt-to-native-coefficient training/evaluation completed with held-out data, baseline comparison and no claims about original model.
3. **PASS_NATIVE_ARCH_SMOKE**: exact upstream mapper module was trained and evaluated on synthetic data.
4. **PASS_NATIVE_PRETRAINED**: original published weights actually executed (not claimed until obtained, pinned, legally usable).
5. **PASS_NATIVE_GEOMETRY**: output instantiated using native licensed 3DMM and independently measured. Currently **HOLD**.
6. **PASS_ADULT_PHOTOREAL_RIG**: requires separate R014, rig/visual QA gates. Currently **HOLD**.

## Replication and O&M

- Execute the GitHub workflow on the isolated research branch; use immutable upstream SHA pins.
- Respect restrictive 15-minute cloud job timeouts and one-run-at-a-time per branch; no self-hosted or private runner.
- Review GHA JSON artifacts and job logs; reconcile summary+checkpoints to private [R015 #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141), the sole project-native research authority. Keep source repo and model legal/rights receipts.
- For deployment, implement each approach as a separately versioned stateless service or one-shot batch job with typed input/output schema and no managed persistent installation. The native demonstration scripts are not currently shippable services.
- Measure cold-start, RAM, disk/cache, image/model download time, inference throughput, allowed licenses, CPU/GPU requirements, failure mode, retraining drift, backup, rollback and artifact custody before production design.
- **No merge/release or acceptance implied.** Do not stage child-coded sexualized generative target vectors; read-only CPE recognition semantics are independent of asset generation permission checks.

### Benchmarks are not interchangeable

BodyShapeGPT is a direct language-to-SMPL-X model; Semantify inverts CLIP-based semantic descriptor ratings to parameters. A TF-IDF regression of BodyShapeGPT's dataset and a Semantify architecture smoke are partial feasibility checks **not a native head-to-head accuracy ranking**. An apples-to-apples outcome requires common adult descriptions, actual pretrained source models, licensed SMPL-X geometry, dimensions measured after native mesh creation, runtime profiles, and confidence intervals.
