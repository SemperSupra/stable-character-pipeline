# G11 evidence-first multilingual prior-art sweep: motion / MMD / rigging / IK / morph QA

**Date:** 2026-10-27. **Status:** RESEARCH / CANDIDATE, not policy, CPE promotion, or claims of production qualification.
**Scope:** public Stable Character Pipeline MMD gates G1-G10, adjacent human/animal/mechanical motion, $0 public cloud.
**Authority:** [public MMD DLE issue #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), [unmerged draft PR #20](https://github.com/SemperSupra/stable-character-pipeline/pull/20).
**Boundaries:** zero-dollar public GHA, no merges/releases/deploys, no unauthorized copies of third-party model/motion/music/texture/identity data.

## Executive finding

**Reuse mature conformance, generated fixtures, evaluator baselines, kinematics, scene schemas and provenance.** Our existing custom Python glTF byte validators are narrow, useful adversarial probes but should not become a competing glTF-spec parser. The residual novel work is *MMD-native semantics crossing engine boundaries* (source bone behavior, PMX extras, append/grant, IK vs FK, physics, morph categories, VMD timing and rights), and a Go-led evidence orchestration layer.

G10 is evidence of this distinction. **Blender MMD Tools** with `fix_ik_links=False` imported a legitimate IK constraint but made the knee/hip tail lengths differ from the source joint-to-joint distances; Blender ankle errors were 1.985 / 1.894 / 1.820 at frames0/15/30. Upstream `fix_ik_links=True` restored bone chain rest lengths and Blender errors became approximately 2.4e-7 / 3.4e-7 / 1.45e-6 units; independent `mmd2gltf` end-effector errors were 0 / .0157 / .0334. Real independent cross-engine G10d [red](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456565154) was preserved, then [green](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456784554) after the upstream option. Even this green result does **not** qualify native MikuMikuDance CCD or collision.

## Frozen research methodology and actual execution boundary

**Track A / independent direct discovery:** native-language and English search across the fixed concept set below, upstream official documentation, GitHub source/license inspection, academic benchmarks and counterexamples. This track was carried out in this ChatGPT research session, outside CPE, with source anchors below.

**Track B / blind CPE + concept-search-adapters + SearXNG:** must use *the same sealed questions*, pre-research CPE snapshot and equal search budgets, with no Track A result leakage; persist raw search results and normalized concept assessments in separately sealed evidence, then compare. **NOT EXECUTED here**: in this session the expected CPE/search-adapter private repository paths were inaccessible via the available GitHub connector, and no live SearXNG/CPE executor was established. Do not conflate direct web search with executing the independent SearXNG engine; do not declare a dual-track quantitative PASS. Prepare a bounded independent G11B workset under its own CPE authority rather than modifying CPE or assuming zero results mean concept absence.

Proposed held-out cluster seeds, scope frozen before any B execution:

1. MMD native PMX/VMD physics and IK solver parity; 2. glTF animation/skin/morph compliance; 3. foot-slide/contact verification; 4. binary skinning and quaternion conformance; 5. group/bone/material/UV morph mapping; 6. retargeting and shape/rig separation; 7. MMD training data rights; 8. intermediate scene/animation schemas; 9. source provenance and proof bundles; 10. MMD runtime engines/independent oracles.
Use ≤12 search questions per bounded rep, two independent engines/question, ≤5 leads per engine, explicit search time/config and raw native source lineage. Repeat with a held-out different set after promotion decisions.

## Native terminology/lexicalization and ambiguity notes

| Locale | Source-native term(s) | Observed source / evidence | Main ambiguity |
|---|---|---|---|
| EN | skinning, IK contact, glTF conformance, foot skating | Khronos, Pinocchio, Drake, Kimodo | MMD often means *maximum mean discrepancy* or *PKU-MMD*, not MikuMikuDance |
| JA | モーション, 逆運動学, 足滑り, 標準ボーン, VMDサイジング | MMD Tools bilingual docs; miu200521358/vmd_sizing; babylon-mmd MMD behavior docs | IK goals vs ground contact not equivalent; standard vs semi-standard bones |
| ZH | 反向运动学, 骨骼权重, 物理骨骼, 脚部穿模 | masaka1024/mmd2gltf-gui; yyc-git/VMDPhysicsBake; MMDMC rights in original Chinese | Software MIT does not convey attached character model permission |
| KO | 역운동학, 모션, 발 미끄러짐, 골격 | Korean MMD community motion-transfer problems | Mostly user anecdote from these searches, not conformance spec |
| DE | inverse Kinematik, Fußrutschen, Skelettanimation | Mainly underlying English project docs | No independent new authoritative source validated |
| FR | cinématique inverse, glissement des pieds | Same | No independent new authoritative source validated |
| ES | cinemática inversa, deslizamiento de pies | Same | No independent new authoritative source validated |
| PT | cinemática inversa, deslizamento dos pés | Same | No independent new authoritative source validated |
| RU | обратная кинематика, скольжение стоп | Same | No independent new authoritative source validated |
| TH | การเคลื่อนไหว, จลนศาสตร์ผกผัน, การลื่นของเท้า | Thai MMD user forum lead | Limited targeted evidence; no inference of technical absence |

These are *query lexicalizations*, not accepted CPE concepts. No one-to-one translations or implied source independence. The Japanese/Chinese native software projects plus anglophone specification/robotics standards gave the strongest verified leads. Missing indexed results are classified **SOURCE_COVERAGE_UNKNOWN**, not conceptual negatives. Deduplicate mirrors, articles quoting README files, forks and package mirrors by original upstream repository.

## Existing reusable software and how to compose it

| Primitive / tool | Origin and scope | Decision | First concrete experiment |
|---|---|---|---|
| glTF 2.0 specification + Khronos glTF-Validator | Khronos; file/schema/buffer/accessor/animation/numerical checks; emits JSON | **ADOPT** as independent standards gate | Validate our exact G7/G9/G10 GLBs, report diagnostics as PASS/FAIL/NOT_TESTED |
| glTF-Asset-Generator + glTF-Sample-Assets | Khronos positive/negative conformance fixtures | **ADOPT / RIGHTS-GATE ASSETS** | Generate tests for sparse morphs, multi-skins, nonfinite/corrupt animation |
| Khronos glTF-Blender-IO CI method | Roundtrip export + validator and comparison | **COPY METHODOLOGY, not reimplement** | Reimport our GLBs and compare geometry, action channels, validation deltas |
| Khronos gltf-asset-auditor | JSON profiles, CLI or browser; pass/fail/not-tested for geometry/UV/material traits | **ADAPT** | Separate authoring quality/fidelity profiles from format validity |
| MMD-Blender/blender_mmd_tools | PMX/VMD/VPD real importer, `fix_ik_links`, bone/morph/physics UI | **ADOPT existing** | Quantify source/native IK links; preserve pre-/post-fix evidence |
| masaka1024/mmd2gltf-gui | MIT, headless stdlib CLI PMX/VMD→glTF with `extras.mmd` | **ADOPT second evaluator** | Extend G8-10 to metadata, 3D evaluated skin and morph groups |
| noname0310/babylon-mmd | MIT, PMX/VMD, morphs, append transform, IK and Bullet WASM runtime | **PRIORITY third MMD-specific engine** | License-clean synthetic PMX/VMD input; compare local joint/world transforms per frame |
| yohawing/mmd-anim | MIT, Rust runtime/C ABI/WASM, PMX/VMD/IK/morph, tests; pre-1.0 | **OPTIONAL fourth oracle** | Use C ABI or CLI sidecar rather than Rust deployable |
| miu200521358/vmd_sizing | MIT motion/model size retarget; test directory, Japanese ecosystem | **EVALUATE** | Compare retarget transforms; capture semantic bone and foot-lock errors |
| yyc-git/VMDPhysicsBake | MIT Node + Ammo, offline physics baking | **EVALUATE source only** | Generated hair/spring/cloth fixture, avoid demo characters |
| Pinocchio | BSD, articulated rigid-body FK/Jacobians/contact solvers | **ADOPT robotics oracle for generic kinematics** | Compare exactly source joint transform conventions on mechanical/human legs |
| Drake | Constraint-based IK/multibody dynamics | **TARGETED INDEPENDENT ORACLE** | Hard contact and joint-limit constraints with explicit tolerances |
| OpenUSD UsdSkel | Skeletal joints, animations, blend shapes; semantic authoring/interchange | **ADOPT scene adapter** | Roundtrip hierarchies, sparse targets and sampled motion to USD for editable scenes |
| ML motion evaluators: NVIDIA Kimodo | Foot skate/contact consistency + end-effector constraints | **ADAPT METRIC DEFINITIONS** | Walking contact intervals + velocity threshold + goal error as separate reports |
| MLCommons Croissant; RO-Crate; W3C PROV-O | Dataset schema and structured resource/experiment provenance | **REUSE** | Rights/observation datasets in Croissant; proof-bundle as RO-Crate; PROV edges |
| MMDMC | ECCV 2024 MMD body/apparel motion research dataset | **RESEARCH ONLY / RIGHTS RESTRICTED** | Read methods; source includes no-redistribution and no-commercial model terms |
| AIST++ | 3D dance data and keypoints, annotations CC BY 4.0; third-party motion/music layers to verify | **CANDIDATE METRICS/DATA** | Keep annotations rights separate from music/videos and underlying body model |
| AMASS / BABEL | Human motion and temporal action labels; AMASS restricted noncommercial research | **CATALOG ONLY unless separately authorized** | Benchmark concepts and evaluation splits; never auto-publish gated files |
| Ubisoft LaFAN1 | 30fps motion BVH and transition benchmarks; CC BY-NC-ND 4.0 | **RESEARCH BENCHMARK, restrict transformations/public redistribution** | Learn transition/contact protocol, use own synthetic sequences for public reps |

Evidence anchors / primary source URLs:
- https://github.com/KhronosGroup/glTF-Validator
- https://github.com/KhronosGroup/glTF-Asset-Generator
- https://github.com/KhronosGroup/glTF-Sample-Assets
- https://github.com/KhronosGroup/glTF-Blender-IO
- https://github.com/KhronosGroup/gltf-asset-auditor
- https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- https://github.com/MMD-Blender/blender_mmd_tools
- https://github.com/masaka1024/mmd2gltf-gui
- https://github.com/noname0310/babylon-mmd
- https://noname0310.github.io/babylon-mmd/docs/reference/runtime/
- https://github.com/yohawing/mmd-anim
- https://github.com/miu200521358/vmd_sizing
- https://github.com/yyc-git/VMDPhysicsBake
- https://github.com/stack-of-tasks/pinocchio
- https://github.com/RobotLocomotion/drake
- https://openusd.org/release/api/usd_skel_page_front.html
- https://research.nvidia.com/labs/sil/projects/kimodo/docs/benchmark/metrics.html
- https://docs.mlcommons.org/croissant/
- https://www.researchobject.org/ro-crate/specification/1.2/introduction.html
- https://www.w3.org/TR/prov-o/
- https://github.com/rongakowang/MMDMC
- https://google.github.io/aistplusplus_dataset/factsfigures.html
- https://amass.is.tue.mpg.de/license.html
- https://babel.is.tue.mpg.de/
- https://github.com/ubisoft/ubisoft-laforge-animation-dataset
- https://github.com/MaSiRoProjectOSS/VMDtoJSON

## Where real novel primitives remain

**No new quaternion library, kinematic solver, glTF spec checker or model-license dictionary.** These duplicate better-maintained ecosystems. Build only the following:
1. **SourceSemanticsManifest**: raw PMX/VMD native names/senses, source FPS, transform order, left/right handedness, Y/Z-up, root relation, units, model time-state, interpolation, skin mode BDEF/SDEF/QDEF, morph type, physics flag/IK and grant chain. Never flatten native features to generic glTF features without a `lost/approximated/preserved` classification.
2. **FixtureSpec / AdversarialMutation**: self-authored bytes with fixed seed/SHA, exact expected source motions, negative mutations (broken IK target, nonfinite quaternion, vertex-weight corruption, frame shift, missing sparse morph, bone axis flips); property-based/metamorphic assertions rather than many hand-written fixtures.
3. **EngineObservation / Trajectory**: sample engine-specific evaluated local/world transforms and skinned vertices at source times; do not assume independent exporters share internal node wrapping, coordinate handedness or bone naming; explicitly normalize before compare.
4. **MetricEvidence**: sourced metric definition/version, coordinate basis, units, tolerance, sample frame/contact interval, status PASS/FAIL/NOT_TESTED/UNKNOWN and strength; distinguish structural validity, animation equivalent, native reference, visually plausible and rights permitted.
5. **QualifiedCapabilityMatrix**: engine × primitive × output form × source rights × proof id; no automatic inference from one synthetic scene to general character-quality capability.
6. **ResearchObservation/ConceptDiscoveryProposal**: native phrase, source-language, source date/url/hash/ancestry, confidence, competing meanings, lexicalization vs real capability vs gap/defect; **proposal only to CPE** with no automatic ontology mutation.
7. **ProofBundle**: small RO-Crate-style JSON-LD manifest + content SHA + CI run/commit + tool exact SHA + evaluator versions + optional human contact-sheet/MP4, machine JSON/JSON Schema, source files and editable BLEND/USD.

Minimal proposed typed envelope:
```json
{
  "schema": "scp.motion.qual.v1",
  "fixture": {"id": "ik-four-bone-v1", "sha256": "sha256:<verified>", "rights": "self-authored"},
  "engine": {"id": "blender-mmd", "version": "4.5.0", "upstream_sha": "<pin>", "options": {"fix_ik_links": true}},
  "basis": {"source_fps": 30, "time_origin_seconds": 0.0, "up_axis": "Z", "unit_scale": 1.0},
  "metric": {"id": "world_ankle_to_goal_l2", "definition": "Euclidean 3D distance", "unit": "source_units", "threshold": 0.05, "samples": [0, 15, 30]},
  "result": {"status": "NOT_TESTED", "reason": "illustrative contract; not a run receipt"},
  "provenance": {"run_id": null, "artifact_sha256": null},
  "source_semantics": {"ik": "retained", "rigid_body_physics": "not_evaluated"}
}
```

## Blue / red team and latent space

**Blue reuse:** Khronos pipeline is the obvious G11 standards checker; Babylon MMD is MMD-native independent engine; Pinocchio/Drake is generic mathematical cross-check; Kimodo-type motion-quality metrics; RO-Crate for transparent proofs; MMD source-native data catalog and Go orchestrator.

**Red false positives:** valid glTF ≠ correct VMD motion; `extras.mmd` retained ≠ a generic viewer executes MMD IK; 2 exporters agreeing ≠ native MMD reference; IK target tracking ≠ planted-foot friction/contact; rig hierarchy and bone name ≠ weight fidelity; matching target endpoint ≠ same trajectory; average frame image drift ≠ physically plausible; legal-to-read ≠ legal-to-republish or train.

**Latent opportunities:**
- Differential tri-oracle **MMD-specific (Blender corrected vs direct MMD converter vs Babylon MMD)** vs robotics Pinocchio 4th engine, and classify consensus vs reference truth separately.
- Semantic metamorphic tests: globally translate/rotate model and target together (equivariance); scale model + IK goal, compare normalized error (scale invariance); time-shift uniformly and compare rel-time motion; reorder internal nonsemantic nodes; rename outer armature wrapper; reverse keyframe sequence; toggle IK only where corresponding constraints are defined.
- DLE assurance metrics: adversarial defects injected, killed/survived by every validator (mutation score); no PASS based on lack of test or absence of errors.
- Contact trajectories need *contact-state labels*: stance-phase ground tangent velocity and penetration/impulse, not just controller tracking. Record support region and plausible ground collision for animals/robots.
- Physics engine version/build/solver timestep and warm-up are first-class test parameters, not one `physics=true` boolean.
- Source rights should gate **each asset+derivative+distribution**, while software dependencies are recorded separately.
- Multilingual names are not just tags: preserve Japanese standard/semi-standard bone conventions, aliases and hierarchy as assertions; unknown Korean/Thai/native phrase findings are not inferred absence.
- Distinguish test-level CPU GHA from model-training GPU/TPU/MLX work. Standards, temporal, kinematic and conformance tests need CPU; data-heavy learned perceptual evaluation needs separately scoped compute and training licences.

## Next READY work plan

1. **G11A** implement a small isolated zero-cost public GitHub Actions job to run the genuine Khronos `gltf-validator` on immutable exact G7/G9/G10 output artifacts, preserve raw JSON diagnostic levels; do not uninstall existing independent semantics/mutation checks. Record false-positive or spec errors as normal evidence.
2. **G11B** create sealed blind research workset through authorized CPE/search-adapters SearXNG plane, two engines, fixed source-native seeds; preserve observations/ancestry and reconciliation; **not executed** until verified sidecar/workset or other authorized access exists.
3. **G12** bring one bounded Babylon MMD runtime test on original 4-bone and 2-morph PMX/VMD, inspect actual APIs and renderer/physics requirements before claiming CLI/headless; no imported community characters or packaged demos.
4. **G13** introduce shared Go-run `FixtureSpec` and `EngineObservation` normalizer and two-engine+metamorphic oracles; keep upstream Python/JS tools isolated as adapters.
5. **G14** add OpenUSD/UsdSkel interoperability and neutral sample glTF-Asset-Generator features (morph/interpolation/skin), with license-specific model admission.
6. **G15** learn from AIST++/Kimodo-style foot-slide metrics and create original planted-foot/stair/landing pose suites; explicit native MMD or physical sensor ground truth needed for claims beyond synthetic solver goal distance.

**Decision boundary:** This report is Track A research evidence and an executable candidate roadmap. It does not claim a completed blinded CPE/SearXNG comparison, a comprehensive survey of all languages, or tested adoption of the listed tools beyond our existing G1-G10 executions.
