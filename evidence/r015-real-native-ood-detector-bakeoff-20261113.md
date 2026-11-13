# R015 rolling morphology build-up / bake-off — 40 truly novel native 3D bodies and OOD detector family

**Date**: 2026-11-13; source-verified free public GHA, **DRAFT/RESEARCH** only. R015 [private DLE #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141), R014 true geometry [#138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138), CPE separate lossless concept-authority and policy membrane. **No merge/release/model promotion.**

## A. True 40-source-native-body predictive error, not recycled holdout

- [Actual source-native run 43364022773](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43364022773), [draft PR #470](https://github.com/SemperSupra/stable-character-pipeline/pull/470). Two independently executable free Ubuntu CPU Blender 4.5.16 runners generated **20 newly evaluated native MPFB shape meshes each**, original pinned MPFB `6ff1eb358f6c1959ced77e79e6dd2406d9a71f49`; **zero duplicate control tuples or evaluated mesh hashes with 72 original shapes**.
- Each cohort: 8 novel interior controlled adult-body shapes and 12 deliberately extreme configurations outside original 0.15–0.85 source control sample support. Reference source training 54, separate withheld calibration 18 (macro grouping disjoint across source gender-class cohorts), no target-case tuning.
- Native target slider MAE (normalized 0..1): female-associated bbox 0.118251 vs richer 5-cross-section Ridge **0.0951433**; male-associated bbox 0.1141323 vs slices **0.0798799**. Extreme interaction errors female **0.132027**, male **0.1213071**, greater than in-range novel interior **0.053847 / 0.058614**. Claims do not transfer to actual physical cm or unrestricted body population.
- Initial 95th-percentile nearest-feature calibration threshold flagged only **2/12 female** and **3/12 male** deliberately extreme examples, an insufficiently sensitive fail-closed gate. Initial conformal-style marginal per-control intervals had empirical test coverage **93.75% / 92.5%** on just 20 synthetic designs per cohort; no production 90% coverage guarantee.

## B. Independently executed four modern unsupervised novelty models

- [Actual source-native GHA run 43365749260](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43365749260), [stacked draft PR #473](https://github.com/SemperSupra/stable-character-pipeline/pull/473). Both separate public CPU source-native MPFB jobs **SUCCESS**, reran 20 *new real* evaluated mesh geometries per cohort and preserved source geometry feature vectors in immutable receipts; no private media or licensed body weights distributed.
- Fit each anomaly detector solely to the **54 previously created real native meshes** and threshold against **18 disjoint original native calibration meshes** at observed 95th percentile; the 20 new body-shape test geometries and their known designer-extreme labels were **never fitted or threshold-selected**.
- Model families: shrinkage Mahalanobis/Ledoit-Wolf, IsolationForest, fifth-nearest neighbor, PCA rank-three reconstruction, separately on bounding-box-only 4 features and 14 geometry cross-section features. Original finite controlled GHA SHA receipts `evidence/r015-ood-detector-family-43365749260-shard-0.json` and `...-shard-1.json` include exact per-case anomaly scores/flags and source model digests.

| Method | Female designed extremes flagged / 12 | Female novel interior false alarms / 8 | Male designed extremes flagged / 12 | Male novel interior false alarms / 8 |
|---|---:|---:|---:|---:|
| Original nearest-feature / richer slices | 2 | 0 | 2 | 0 |
| Fifth nearest / slices | 2 | 0 | 2 | 0 |
| IsolationForest / slices | 4 | 0 | 3 | 0 |
| PCA reconstruction / slices | 7 | 0 | 8 | 0 |
| **Ledoit-Wolf shrinkage Mahalanobis / slices** | **8** | **0** | **10** | **0** |
| Predeclared combined OR (Mahalanobis/IsolationForest) / slices, descriptive only | 9 | 0 | 10 | 0 |

**Adjudication**: shrinkage Mahalanobis is the *leading synthetic OOD detector candidate for this narrow experiment*; baseline OOD gate is falsified. It still missed **4/12 female** and **2/12 male** deliberately extreme shapes. No fail-closed real morphology detector can be claimed. The OR combination is a **post-hoc exploratory check**, not an independently heldout qualification/promotion result. Calibration 1/18 alert per method and novel interior 0/8 per cohort cannot establish population false-positive rates.

## C. Critical next gate and repository hygiene

- Source MHR/MPFB native geometry must be calibrated to actual known physical units, measured anthropometric circumference using proper mesh-plane intersection loops (not width/depth sampling), anatomy/soft-tissue fit, and many more *independent held-out families* including extreme interactions, cross-shape motion, poser-driven geometry.
- When accepted, candidate uncertainty/OOD envelopes become a *typed guard/abstention* of the future composed prompt→CPE recognized concepts→adult-eligible morphology→native actor chain, never a replacement for CPE source-concept recognition or the separate generation membrane.
- Distinguish `PASS_TEST_EXECUTION` from `FAIL_OR_UNKNOWN_PRODUCTION_SAFETY`. This work produces no fully rigged cinematic human and does not qualify the final R009 video.
- Original method/historical bakeoff PRs #440/#443 stay draft. New source PRs #470/#473 are stacked draft/unmerged, no persistent host modifications, private GitHub Actions minutes, forced branch updates, releases or public protected source data.
