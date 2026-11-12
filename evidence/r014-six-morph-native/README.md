# R014 / R015 — Actual source-native six-body morphology, rig and cinematic-readiness bakeoff (2026-11-12)

**Disposition:** `PASS_SOURCE_NATIVE_MORPH_RIG_AND_GEOMETRIC_DIVERSITY_STRUCTURAL_ONLY`; `HOLD_PHOTOREAL_CINEMATIC_FULL_ANATOMY`. This report contains only source and numeric evidence, not model binaries. Release/merge **not authorized**.

## Proven independent free-tier cloud execution

**Batch A:** [public GHA run 43286258004](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43286258004), two independent matrix jobs both **PASS**, [source draft PR #444](https://github.com/SemperSupra/stable-character-pipeline/pull/444) stacked on corrected pinned [MPFB foundation PR #402](https://github.com/SemperSupra/stable-character-pipeline/pull/402). Source pinned `makehumancommunity/mpfb2@6ff1eb358f6c1959ced77e79e6dd2406d9a71f49`, official Blender 4.5.16 release sha256, disposable Ubuntu runners, no protected data. Corrected machine-readable MPFB morphology macro convention retained (0.0 female-associated, 1.0 male-associated); age macro 0.65 means one body shape control, **not** a chronological adult certificate.

Each shard created **three actual MPFB source and helper-free skin meshes**, 163-bone native rig per actor, 13,380 exported/clean body vertices, 139 weighted deforming bones, native editable Blender scene, an individual animated skin-bearing GLB per character, six source Cycles stills per shard, and one **16-frame H.264 256×340, 12fps, 1.333s** technical motion clip per shard. Actual upper arm and leg joint rotations displaced evaluated skin by 0.102–0.154 Blender units and returned to exact rest within float receipt precision at frame 16. Both shards successfully completed **independent fresh-Blender-process source file reopening, skin evaluation and joint articulation verification**.

- [Shard 0 artifact](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43286258004/artifacts/13975056475) `r014-real-six-morph-shard-0` contains native source, 3 animated GLBs, 6 view images, H.264 and receipts.
- [Shard 1 artifact](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43286258004/artifacts/13975465875) `r014-real-six-morph-shard-1` contains analogous sources.
- Artifacts have seven-day retention, **do not rely on them as durable model custody**.

**Crucial geometry falsifier:** the raw Basis mesh bounds were *identical for all six designs*. In pinned MPFB source, `TargetService.reapply_macro_details` applies macro influences as shape keys. The static raw vertex array therefore cannot establish actual variation. We refused to infer geometry diversity from six different numeric macro vectors and dispatched a **separate real saved-source independent geometry test**.

**Batch B:** [public GHA run 43287728426](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43287728426), PASS, [stacked PR #448](https://github.com/SemperSupra/stable-character-pipeline/pull/448). Downloaded *both exact prior source .blend scenes*, independently reopened each in Blender 4.5.16, computed **true evaluated 13,380-vertex skin mesh after shape keys at rest**, SHA256 hashed quantized XYZ coordinates, captured active macro key weights and verified **6 / 6 distinct evaluated meshes** versus only **1 / 6 distinct raw Basis arrays**. These are actual generated-body differences, not textual shape parameter settings or differing skeleton poses. The six observed evaluated XYZ extents are:

| Native adult design probe | Evaluated X extent | Y extent | Z extent |
| --- | ---: | ---: | ---: |
| feminine-associated short/light | 0.8860 | 0.3592 | 1.4103 |
| feminine-associated tall/strong | 1.2050 | 0.4982 | 1.9763 |
| feminine-associated medium/full | 0.9666 | 0.4181 | 1.5838 |
| masculine-associated short/broad | 1.0711 | 0.4335 | 1.5878 |
| masculine-associated tall/slim | 1.3897 | 0.5687 | 2.1640 |
| masculine-associated medium/strong | 1.1229 | 0.4637 | 1.7299 |

Values are **unqualified Blender object-local units**; no height in centimeters, body girth, anthropometric calibration or adult identity is claimed. Native author model is an anatomical design control, **not a person's actual body**. Distinct mathematical geometry qualifies **coverage feasibility**, not visual realism, face/hand skin, reproductive anatomy, or physical plausibility.

- [Source-derived shape-metric receipt](https://github.com/SemperSupra/stable-character-pipeline/blob/research/r014-six-morph-actual-evaluated-geometry-oracle-20261112/evidence/r014-six-morph-native/43287728426-cross-shard.json).
- [Shard 0 detailed shape-key and geometric receipt](https://github.com/SemperSupra/stable-character-pipeline/blob/research/r014-six-morph-actual-evaluated-geometry-oracle-20261112/evidence/r014-six-morph-native/43287728426-shard0-evaluated.json).
- [Shard 1 detailed receipt](https://github.com/SemperSupra/stable-character-pipeline/blob/research/r014-six-morph-actual-evaluated-geometry-oracle-20261112/evidence/r014-six-morph-native/43287728426-shard1-evaluated.json).

## Parallel related authentic prior tests, independently owned

- [MHR native 45-axis shape-response PR #441](https://github.com/SemperSupra/stable-character-pipeline/pull/441) already has a successful source-pinned CPU geometry study ([run 43264812084](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43264812084)); this is **opaque native latent response**, not a named cm or waist/height mapping.
- [MHR native arm+face subdivision PR #442](https://github.com/SemperSupra/stable-character-pipeline/pull/442) has two successful independent public CPU jobs [run 43283569870](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43283569870), status `PASS_REAL_NATIVE_MOTION_EVIDENCE_ONLY`; MHR rig animation/mesh evidence not a photoreal facial/muscle/eye acceptance.
- [MPFB official CC0 skin/hair/eye lookdev PR #412](https://github.com/SemperSupra/stable-character-pipeline/pull/412) [run 43207658801](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43207658801) passed source asset attachment/reopen rendering.
- [MPFB CC0 textured 72-frame 3-second actual rig-motion PR #427](https://github.com/SemperSupra/stable-character-pipeline/pull/427) [run 43229574927](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43229574927) successfully rendered both original actor motion previews with source official materials; actual garment/hair collisions, foot contact and photoreal performance still unqualified.
- [Further **textured source macro propagation** PR #447](https://github.com/SemperSupra/stable-character-pipeline/pull/447) tests real shape changes on the original packed CC0 material/eye/hair scene and actual rig-motion replay, independent of six neutral morph bodies. Treat in-flight/failed shaders/downloads as blocking until checked; no implicit success.

## Corrective technical findings and next implementation gates

1. **Never measure just raw Basis vertices.** MPFB source morphs use shape-key weights; geometry oracle must sample evaluated mesh and record macro/pose state. The original six control vectors were not enough to establish body diversity, resolved by independent fresh-source evaluated SHA and object-space extents.
2. **Source-native rig video actual H.264 verification.** Initial six-morph GHA runs rejected videos using a naive minimum compressed-byte threshold (>5000 bytes). Neutral 16-frame renders were actually valid but only ~4KB. Fixed failure gate uses **ffprobe codec=h264, dimensions 256×340, exactly 16 frames, duration=1.333s**, not a misleading size heuristic. Retain initial negatives as evidence.
3. **Cinematic readiness remains HOLD**: separate qualified high-resolution skin/microgeometry and displacement; eyes/cornea, lashes, eyebrows, hair and non-penetrating attached garments; full anatomy topology and region-specific body morph testing; realistic bone/IK contact and temporal cloth/tissue/face physics, emotional expressions; pose/motion retargeting; lighting, surface subsurface scattering, LoDs, formats, 4K 24fps motion, independent visual review.
4. **Semantic-to-native integration:** CPE R015 [private #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141) remains the concept authority; subsequent text/typed adult morph spec → native MPFB/MHR adapter requires a larger source-native measured DoE train/test set. Six shapes are a functional variability smoke, not sufficient training supervision. R014 owns 3D asset qualification, R009 #23 owns production video.
5. **Deploy/O&M:** reproducible Blender 4.5.16 and MPFB SHA, disposable public GHA CPU, Go orchestration and native Python worker; authoritative model/source/rights hashes, export and fresh-reopen QC, failed-run archives, short-lived proof artifacts, no persistent unreviewed cache or private media on public runners. Export glTF skin animation *alone* does not demonstrate close photoreal or full character readiness.

**No main merge, release, model-parameter promotion, source data leakage, cinematic quality claim or licensed asset redistribution authorized.** This is actual proven structural/morphology progress toward the target.
