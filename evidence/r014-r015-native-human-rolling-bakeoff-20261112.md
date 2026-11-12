# SupraHuman R014/R015 — continuous native morphology and inverse-model qualification

**UTC date:** 2026-11-12. **Authority:** private [R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138), [R015 #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141), independent [R009 #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). **Status:** research evidence, all acceptance/promotion/merge/release **HOLD**. Real-person identity/media never involved.

## Verified build-up / bake-off sequence

| Stage | Real execution | Result | Key limit |
|---|---|---|---|
| Correct native MPFB bodies | [six-morph GHA 43286258004](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43286258004), [draft PR #444](https://github.com/SemperSupra/stable-character-pipeline/pull/444) | Two shards PASS. Six source-native adult designs, 13,380 clean vertices and 163 bones per source actor, actual rigged animated GLBs, editable .blend, Cycles stills and 16f H.264; independent Blender reopen | Structural/motion only, neutral research surfaces |
| Distinct actual evaluated geometry | [R014 authoritative GHA 43287728426](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43287728426), [draft #448](https://github.com/SemperSupra/stable-character-pipeline/pull/448); independent reproduction [run 43288520592](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43288520592) [draft #450](https://github.com/SemperSupra/stable-character-pipeline/pull/450) | Six distinct evaluated mesh hashes; identical raw Basis extents were **not** real morphology. Z spans female-associated 1.4103/1.9763/1.5838, male-associated 1.5878/2.1640/1.7299 **Blender native units** | Not calibrated heights in meters. Duplicate #450 is independent reproduction, not another production source |
| Actual official CC0 skin/eyes/hair with source-native morph changes | [male GHA 43287691272](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43287691272), [female GHA 43288582735](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43288582735); [draft #447](https://github.com/SemperSupra/stable-character-pipeline/pull/447) | Male/female jobs each passed: 19,158 body source vertices, 163 bones, ten packed texture images, exact source-macro edits, real skinned pose changes, fresh-process reopen, Cycles front/back/posed PNGs, 16f verified H.264. Morph displacement 0.132658 / 0.387385 Blender units, pose displacement 0.094296 / 0.133557, return residual 0 | Packed/linked material does not prove surface correctness, accessory fit or photoreal quality. Original MAKESKIN has shader `GROUP`→`OUTPUT_MATERIAL`, not mandatory top-level Principled |
| DoE with actual native MPFB measured geometry | [GHA 43289442194](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43289442194), [draft #451](https://github.com/SemperSupra/stable-character-pipeline/pull/451) | Two independent 36-case shards PASS, **72 unique actual evaluated geometries**, all four MPFB macro inputs recorded. Each shard exact baseline reconstruction and 27-train/9 held-out inverse Ridge vs mean/nearest. Female-associated Ridge MAE 0.0977959 vs mean 0.1471333; male-associated Ridge 0.0535627 vs mean 0.1471333 | Geometry dimensions/cross-sections not anthropometric centimeter targets; 36 cases per cohort and one train/test split each insufficient for population coverage |
| Source-native geometry→control regressor family | [GHA 43290260471](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43290260471), [this draft #453](https://github.com/SemperSupra/stable-character-pipeline/pull/453) | Two parallel feature ablations (4 features bounding box; 14 features bounding box+five horizontal slices) × two macro-group-disjoint splits (54 train, 18 test). All jobs SUCCESS. Six comparator models, no input-label/shape duplicates across splits | Tiny controlled research data, native slider MAE only; no prompt/semantic generation, no mesh collision/pbr/anatomy acceptance |

### Two-split averaged normalized native-control MAE, lower is better

| Model | Bounds (4 features) | Bounds + slices (14 features) |
|---|---:|---:|
| Constant training mean | 0.173182 | 0.173182 |
| Ridge | **0.117499** | **0.078028** |
| 5-NN distance | 0.148569 | 0.136098 |
| Random forest | 0.159452 | 0.151651 |
| ExtraTrees | 0.150179 | 0.146110 |
| Small MLP | 0.165538 | 0.129269 |

**Interpretation:** Ridge with actual evaluated 3D body cross-section measurements wins this particular small, regularized, held-out control-inversion experiment. It reduces average absolute native slider error about 55% relative to mean. The separate MLP has not been sufficiently trained on diverse data to select for production. The inverse task is geometry→native controls, not natural language→3D meshes; use it as a ground-truth and identifiability/fitting component rather than a finished semantic generator.

**Technical caveat:** Profile/test performance can change substantially when moving to different body morphs, source releases, cross-backend MHR/MPFB geometry or real physical units; do not promote a model on 72 synthetic samples. Sex-associated body macro is a *controlled source modeling setting*, not inference of gender identity, sex, ethnicity or personal age. `age_macro=0.65` is only a shape knob, not proof of chronological adult age.

## Artifact custody and hygiene

All **eight** released research ZIPs were downloaded through the connected GitHub Actions connector and validated locally using ZIP CRC, no duplicate/path-traversal entries, relevant internal source SHA256, true Blender scene/GLB/MP4 checksums, DoE status and exact numeric shape counts. Validation result `PASS_ZIP_CRC_AND_EMBEDDED_SOURCE_RECEIPTS`; SHA-256 of independent machine-readable custody manifest `6dc17813d176be23a668d4906da8c04f9cdb3810a2594dd7e23e3efed2ec17ca`. Original author binary models were NOT redistributed and all public synthetic data and media only.

**Private Google Drive persistent custody (verified metadata/size after upload):**
- Research model source bundles, under [R014 SupraHuman RigLab](https://drive.google.com/drive/folders/19bzvrQ35DwIxdpftrDCjxezNLa2UQl-v):
  - Six real native shapes shard 0: [Drive](https://drive.google.com/file/d/15SILZqK_Z7hlHebsZMCF8Ni6z0HDUmSO/view)
  - Six real native shapes shard 1: [Drive](https://drive.google.com/file/d/1H8VH-2UNCYw6fmh53ze8oOoizymCQWy5/view)
  - CC0 fully source-packed textured male-associated design: [Drive](https://drive.google.com/file/d/1lkLNVOlvte1NeGBeAK-OTuH7Mrjl3B5S/view)
  - CC0 fully source-packed textured female-associated design: [Drive](https://drive.google.com/file/d/1_cTjUkrpUyiFQRxaSfvOoS1441Jyg0_O/view)
- Numeric research, under [Morphometry DOE folder](https://drive.google.com/drive/folders/1gTcyxwt4vyTS_nxb0JrJtK7RATke6Jvq):
  - 36 real MPFB shapes and measurements, shard 0: [Drive](https://drive.google.com/file/d/1Xv3hFoVAa0Loh8v0kogy_7vRW8F36tYe/view)
  - 36 real MPFB shapes and measurements, shard 1: [Drive](https://drive.google.com/file/d/1jR_g_Iy_sws1eTm5dXu5rP4lKckthKti/view)
  - Source-native regression bbox model-family receipts: [Drive](https://drive.google.com/file/d/1lgnKu1E8oJMY7PvdOQeTEl0aMyjsDokH/view)
  - Full-slice model-family receipts: [Drive](https://drive.google.com/file/d/1ujbCpNrZXSExWpev6wOdW3Aonh9j2uFO/view)

No private GH Actions minutes, no persistent host installs, no unsafe model pickle, no main branch mutations (main verified `1a6f58739c9b739ca3ac6671a67f2e0710751e6b`), all new public GitHub PRs are DRAFT and UNMERGED. Earlier failed races/Blender-CDN 403, MPEG4-size heuristic and false Principled shader-node assumption retained as negatives. All source-safe promotion gates explicitly HOLD.

## Next critical path, with independent owners

1. **R014 native morphology:** increase shape/age-independent torso/limb/bust/hip/shoulder measurements, real torso circumference from mesh triangle-plane sections (not naive point slice), source units/pose calibration, 45-axis MHR Jacobian and MPFB macro interactions. Independent train/test generated shapes and uncertainty/OOD.
2. **R014 realistic asset fit:** actual shape-specific packed CC0 skin/eyes/hair/eyebrow/teeth topology, per-face body material slots, garment/hair attachment, intersections, UV retention and 3-view native visual comparison. Neither matching macro nor packed textures constitutes accessory-fit acceptance.
3. **R014/R009 motion:** native MHR gait retarget evidence presently FAILS (foot ankle residual >0.6m) and face shape blend inversion still occurs on jaw/blinks; retain real-rig jaw alternative as limited candidate, redo bind-to-rest IK, foot contact, finger/face, tissue/hair dynamics with independent original frame pixel review.
4. **R014 cinematic lookdev:** high-resolution sculpt alignment, PBR skin/eyeball/cornea/hair, anatomy-complete optional adult variants, multi-light real Cycles 1080p review before expensive 4K, and six-camera/scene-motion QA.
5. **R015/CPE:** CPE owns lossless concept recognition and semantics; generation membrane/action policy separately governs eligible adult synthetic asset generation. Typed morphology prompt/measurement contract routes into versioned MPFB/MHR inverse adapters; compare original BodyShapeGPT/Semantify, modernized SigLIP/Qwen challengers only on **same measured native geometry and licensed source assets**. Human editor, Go CLI automation, and typed agent APIs all required.

**Not yet achieved:** photorealistic, anatomically complete, fully rigged poseable cinematic user-prompt-to-3D humans. This evidence advances the true native geometry/regression and textured rig structure only. Owner acceptance required for any merge/release or R009 production video.
