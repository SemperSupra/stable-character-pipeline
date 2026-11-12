# R015 — Wave 2: group-safe language regression and original CLIP→mapper inference

**Date:** 2026-11-12. **Scope:** released pre-existing techniques only. **Authority:** Stable Character private DLE [#141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141). **Disposition:** research, no promotion/merge/release. All jobs public, disposable GitHub-hosted CPU, read-only checkout, synthetic adult controls only.

## Exact cloud receipts

- [BodyShapeGPT group-disjoint generalization run 43277657654](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43277657654), native released corpus at `758bf5a1b3dbd12984de6f68ad4d3bf8c95ef409`, script `research/r015_prior_art/bodyshapegpt_group_holdout.py`, JSON `43277657654-bodyshape-group-holdout.json` retained alongside this report. All jobs passed. This evaluates new TF-IDF+Ridge models on original public paired data, not the published 8B language model.
- [Actual original CLIP + actual published Semantify checkpoint run 43278119546](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43278119546), author Semantify source `78b001d3dc4ea4efa428e3aff1213cefddf6ebd8`, official CLIP source `d05afc436d78f1c48dc0dbf8e5980a9d471f35f6`, official ViT-B/32 weight SHA256 `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`, author neutral mapper SHA256 `7bb79747504919656ecacb120b5be70b51b6faac1535d1cfd7f46b1401a3ed7b`. JSON `43278119546-realclip-original-pretrained-mapper.json` retained alongside this report. This is original CLIP scorer and original pretrained mapper, with original CLIP runtime score domain, but synthetic images and no licensed SMPL-X geometry.
- Separate [real-CLIP background nuisance robustness run 43278754584](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43278754584): originally queued/in progress; see later reconciliation. No result assumed here.

## Corpus ambiguity, leakage, generalization

All 21,000 BodyShapeGPT JSONL lines parsed. 19,429 distinct normalized text descriptions correspond to 21,000 distinct numeric vectors when quantized to 1e-5. In particular **856 descriptions map to more than one distinct 10-beta vector**, so an exact natural-language descriptor does not uniquely identify parameters. A connected-component split links repeated descriptions and matching shape vectors (prevents both duplicate-prompt and duplicate-shape leakage). Six bounded 6,500-train/1,000-test CPU tests:

| Split / seed | Mean baseline MAE | TF-IDF word+Ridge MAE | TF-IDF character+Ridge MAE | Overlap |
|---|---:|---:|---:|---|
| Prompt-disjoint / 20261112 | 1.123357 | 0.907525 | 0.910143 | zero prompt, zero native vector |
| Prompt-disjoint / 20261113 | 1.109401 | 0.900540 | 0.906363 | zero prompt, zero native vector |
| Shape-disjoint / 20261112 | 1.136086 | 0.916363 | 0.918617 | **63 repeated prompts**; zero vector |
| Shape-disjoint / 20261113 | 1.118608 | 0.913304 | 0.917865 | **67 repeated prompts**; zero vector |
| Connected-component-disjoint / 20261112 | 1.123334 | 0.909572 | 0.911905 | zero prompt, zero vector |
| Connected-component-disjoint / 20261113 | 1.120851 | 0.916052 | 0.919880 | zero prompt, zero vector |

The word-Ridge baseline retains ~18–19% relative MAE improvement over the trivial constant-mean baseline on stricter connected-component splits, with variance across splits. This **does not** establish human body dimensions, identity, rig compatibility or the published LLM's accuracy. Distinct normalization/permutation and ambiguous descriptor supervision require top-k distribution/prediction intervals, not one point prediction. No body imagery generated in this lane.

## Source-native CLIP → neural shape coefficient pipeline

Semantify's released `generate_clip_scores` scores images with the *raw* official CLIP ViT-B/32 image–text logits: these are *not* probabilities and are neither normalized 0–1 nor identical to numerical word slider values. Its `semantifyDataset.labels_dict_to_tensor` passes these raw logits into the 8→800→500→10 mapper.

For three synthetic vector-drawn, age-neutral adult silhouettes — tall/narrow, short/broad, medium — the original pinned CLIP scorer produced descriptor values in **[23.85398, 28.73401]**; we fed those scores directly into the original published Semantify SMPL-X neutral mapper. The output had exactly ten finite coefficients per figure, identical repeat results (max delta zero). The original CLIP scorer + actual pretrained mapper operation took **7.443 seconds** for 3 images × 8 descriptors on the public CPU runner, excluding installation and initial downloads. The prior `[0.25]*8` smoke vector was **outside the observed real CLIP score range**, thus must not be cited for semantic relevance or coefficient distribution. The actual pretrained pipeline gave distinct shape vectors, but neither image-to-native geometry nor descriptive human shape fidelity is measured.

Directional sanity checks on the **stylized controls only**: the tall/narrow silhouette CLIP `tall` score is **27.84418**, short/broad **25.83774**; short/broad `fat` **27.28680** vs tall/narrow **25.61259**. These two expected directions are evidence the particular public synthetic silhouette controls affect CLIP scores, **not** human body parameter correctness.

## Differential operating conclusions

- **Language-only BodyShapeGPT:** viable for text-to-shape research, public supervision set demonstrated; native released trained Llama-3-8B/LoRA not executable from current public cloud permissions (gated Meta base + off-repo OneDrive weight). Original demo has unsafe parser that can include prompt numerics and lacks exact vector-length enforcement. CPU text regression substitutes cannot be called the original model. Production likely needs controlled GPU or smaller distilled mapper; exact weight rights, cold-start, memory and p95 remain unknown.
- **Semantify:** genuine original scorer+original published neural shape mapper now runs with SHA-pinned public CLIP+Mapper artifacts on Linux GitHub Actions CPU, using a modern isolated PyTorch environment and narrowly scoped `weights_only=True` checkpoint compatibility. Original SMPL-X mesh geometry/photoreal reconstruction remains **HOLD** pending source/license/user registration, not quietly replaced with surrogate geometry. Front/back multiview and actual 3D avatar renders remain untested. Architectural deployment choice: versioned CLIP scoring worker (heavier) plus independently deployable 8→10 CPU mapper; store exactly ordered descriptor vector, raw logit calibration stats, model hashes, checksum, and source image/render domain in every receipt.
- **Both:** no head-to-head accuracy ranking from unlike output spaces or unlike input tasks. For API design, expose explicit `modality=text|image|structured`, source concept IDs, native parameter kind/dimensionality, top-k with uncertainty, backend+weights digest, input age semantics kept separate from asset eligibility gates. Health, real identity, source licenses, and policy membrane remain external.
- **O&M:** immutable SHA-pinned weight download policy, bounded source/asset sizes, safe weights-only deserialization, no `--no-check-certificate`, refcounted cache inside disposable worker only, CPU/GPU admission and max wall clock, units and clamp checks, descriptor order/version monitoring, background/presentation drift; monitor full image scorer latency separately from tiny neural mapper forward latency. Capture cold-start and network bytes before deployment sizing; no use of public runners for private media.
- **Next gate:** quantitative background/camera/garment/texture robustness, actual licensed SMPL-X mesh measurement on common adult description/semantic fixtures, and full native Llama/LoRA comparator if accessible legally. Only after this existing-technique bakeoff may the independently owned MPFB/MHR adaptation be admitted.

## Original CLIP background sensitivity — completed

[Actual original CLIP/mapper background probe 43278754584](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43278754584) successfully scored six procedural adult silhouettes, three original neutral-background figures plus three **same-geometry**, warm-blue-background variants. Retained precise aggregate JSON `43278754584-clip-background-robustness.json`; no image/weight blobs redistributed.

- Tall/narrow vs short/broad on the original background changed the inferred ten-beta vector by **L2=1.755232**.
- **Same silhouette** with only the background changed caused ten-beta L2 deltas **[0.540358, 0.242561, 0.397386]**; mean background-vs-selected-shape-contrast ratio **0.22415** (22.4%).
- Raw CLIP eight-descriptor score L2 difference between base tall vs broad was 3.585924; same-silhouette background deltas **[0.951266, 0.665216, 1.323348]**, average ratio **0.273275**.
- Interpretation is restricted to *stylized programmatic controls and one selected shape contrast*. There is no real human-domain calibration, no assertion that 0.224 is an error rate or that the mapper fails production. It **does** refute an assumption that background alone never shifts the output: image normalization and input-domain drift need independent confidence/abstention controls.

## Follow-up execution gate

**Completed O&M qualification**: [Original source-native CLIP serial-vs-batched run 43279459776](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43279459776), receipt `43279459776-original-clip-batching-om.json`, **SUCCESS / PASS_NUMERIC_EQUIVALENCE**. On the *same six* public stylized controls and eight descriptor strings, official OpenAI CLIP performed two warm sequential rounds of 48 image-text scoring calls, median **6.756967 seconds**, versus five warm single-batch rounds (6×8 image-text logits), median **0.655090 seconds**: **10.3146× speedup**. Maximum absolute logit difference compared with the *actual original source scorer* and with the warm sequential control: **0.00001526**. Measured Python Linux process maxRSS **2,131,340 KiB (~2.03 GiB)**, including both original CLIP and mapper contexts; this is not steady-state CLIP-only memory. Neither strategy was judged on actual SMPL-X mesh fidelity.

**Implementation differential:** keep original Semantify score semantics and descriptor order, but build a vectorized stateless descriptor scorer rather than the author's one-image/one-label Python loop. This short CPU proof substantially reduces a likely production cost; still independently qualify cold-start/artifact download, full pipeline p50/p95 across a representative real mesh/render dataset, model rights and output bounds before deployment.

## Repository and DLE hygiene

PR [#440](https://github.com/SemperSupra/stable-character-pipeline/pull/440) is **DRAFT**. Artifacts are bounded public JSON text receipts committed in a dedicated research evidence folder. Public workflow jobs have `permissions: contents: read`, action SHA pins, disposable `$RUNNER_TEMP` installs and nonpersistent checkout credentials. Original model archives, CLIP weights, third-party restricted geometry and private CPE concepts are **not in Git**. All models/physical quality acceptance gates remain held.
