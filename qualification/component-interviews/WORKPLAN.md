# Component and Pipeline Qualification Interviews — Three-Audience DOE Work Plan

**Version:** \`scp.component-interview-workplan.v1\` (2026-10-27)  
**Disposition:** Owner-endorsed *work plan*, **not implemented/qualified**. Source changes are confined to a separate public **draft** planning branch.  
**Owning DLE:** [Stable Character Pipeline public Flora/Fauna #5](https://github.com/SemperSupra/stable-character-pipeline/issues/5); architecture rationale [#6436027698](https://github.com/SemperSupra/stable-character-pipeline/issues/5#issuecomment-6436027698).  
**Execution and interview prior art:** [Model Spelunker #54](https://github.com/SemperSupra/model-spelunker/issues/54) (task/actor/experiment/receipt), [Agent Dispatch #104](https://github.com/SemperSupra/agent-dispatch-private/issues/104) (actor qualification) and [#96](https://github.com/SemperSupra/agent-dispatch-private/issues/96) (bounded heterogeneous workcells). Their authority and private state **do not transfer** to this public repository.  
**Baseline:** public tropical PR #4 at \`6e894c30dac98c0398339f39419a482508b1b041\`. Flora #13 / Fauna #26 remain independent draft, unmerged experiments; existing v0.1 public preview must not be modified.

## Decision / objective

Build a **single logical interview protocol** that qualifies providers **in a design- and task-conditioned context** and proves compatibility of *composed* stage graphs. All three audiences—human operators, deterministic automation, and AI agents—must be able to discover candidates, submit a proposal, compare, execute **within authority**, inspect evidence, challenge a claim and continue a DLE baton.

**Do not build a second scheduler, worker registry, DB, dashboard, authorization plane, scientific DOE solver or replacement for Model Spelunker.** Reuse science (not copy private records), place through authorized Agent Dispatch/workcells, use existing GitHub DLE and receipt/artifact storage. Write deployable contracts/CLI in Go; use existing Python numerical/Blender adapters where appropriate. Only standard public-safe $0 GitHub Actions CPU is authorized as the default pilot venue.

## Ten non-negotiable design invariants

1. **One semantic state, three interfaces.** UI, CLI and bounded agent tools use the same canonical serialization, validator, authority result, receipt identity and event log; no special agent shortcuts or UI-only mutable state.
2. **Task-conditioned candidate binding.** Unit is \`design_class × frozen task+fixture+verifier × stage typed IO × provider version/config/build × upstream data rights × adjacent adapters × substrate × budget × authority\`; a tool's brand name is not an empirical result.
3. **Type-safe substitution.** No implicit conversion across \`MTG graph\`, \`rigid articulation\`, \`skinned skeleton\`, \`triangle mesh\`, \`ecology trace\`, \`motion series\`. Enforce units, axes, topology, ID semantics, timebase, interpolation, capability constraints and exact adapter hashes.
4. **Independent verification.** Every consequential verifier has known-good and known-bad controls. Generator self-report cannot accept a claim; human subjective annotation is separate from objective measurements. Preserve inconclusive states.
5. **Experiment science.** Freeze factors; use matched crossovers, blocks, seeds and independent replicates, negative controls, falsifiable claims, an explicit stop rule and uncertainty. Do not collapse results to a universal leaderboard.
6. **Public/private rights boundary.** Public fixture and provider/code/data always public-safe *from birth*; no real-person human/identity data, credentials, private actor profiles or rights-uncleared assets in public workcells. External model or dataset admission never inferred from a URL.
7. **Bounded placement.** Default public CPU $0; no paid GPU, Kaggle TPU, private hosted runners or external downloads without a separate, explicit authority decision. Protect existing scarce actors and quotas.
8. **Immutable evidence.** Each run receives distinct append-only observation ID; exact code/version, source/fixture digests, execution profile, failures, resource use and artifact hashes survive replacement and retry. Derived summaries are reproducible and revocable.
9. **Fidelity honesty.** \`illustrative/synthetic\`, \`constrained\`, \`independently measured\` are disjoint evidence classes; interchange pass is not scientific accuracy; renderer pixel equality is not anatomical validity.
10. **No change to release authority.** Research plans/tests/PRs do not merge, publish previews, release, deploy or promote accepted assets.

## Borrow directly from established interviews

| Existing Model Spelunker concept | Component/graph extension | Reuse policy |
| --- | --- | --- |
| \`task-profile.schema.json\`: frozen task, fixture, verifier, limits, success | \`DesignSpec\` + \`TaskPackage\`: design class, representation, fidelity, source/rights, oracle | Map semantics, do not fork authority or copy private fixtures |
| \`experiment.schema.json\` v2: decision question, role, frozen/variable factors, replication, stop/exclusion and responses | \`InterviewPlan\`: controls, discrete provider treatment or numeric factor, seed and conditional DAG selection | Reuse experiment vocabulary/claimed effects, extend through thin adapter |
| \`actor-profile.schema.json\` | \`CandidateBinding\`: provider/version/config/build/data and typed ports (separate from actor which executes it) | Don't confuse model/actor qualification with engine/modeling accuracy |
| \`run-receipt.schema.json\` | \`RunObservation\`: object/model fidelity, numeric metrics, independent test result, source/renderer custody and first failure | Immutable events and derived envelopes, no aggregate winner |
| Workcell placement / authority from Agent Dispatch | Placement reference and projected permissions, immutable workcell receipt, independent validator | Agent Dispatch places/observes, never self-promotes product claims |
| Model Spelunker trusted-local adjudication UI pattern | Blind source comparison, reveal ledger, human signed/attributed review without automatic promotion | Reuse human review method; preserve source identity separation |

## Planned contract objects

- \`DesignSpec\` — design class \`flora|fauna|mechanica|human|environment|audio|generic\`; public pilot excludes private human assets. States purpose, target behavior, fidelity, units, constraints, allowed venues and authority.
- \`StageContract\` — typed inputs/outputs with semantic kind, unit, handedness, local/world transform, timebase and interpolation, identity, loss tolerance, and expected invariant.
- \`CandidateBinding\` — provider tag/source commit/build digest, dependencies, model/data rights, supported headless tools and adapter interfaces; CAPABILITY CLAIM is distinct from VERIFIED CAPABILITY.
- \`PipelineGraph\` — typed DAG with nodes, explicit adapters and edges; topological sort, cycle rejection, port mismatch with exact reasons; stages can be branches/fan-in, not a forced linear conveyor.
- \`InterviewPlan\` — frozen fixture, source digests, decision/hypothesis, factor/treatments/controls, blocked and randomized replicates, hard eligibility, response metrics, limits/stopping/exclusion.
- \`RunObservation\` — original source and candidate digests, executor/venue, start/end, artifacts, first failing stage, classifier (infra/model/adapter/verifier/authority), measured metrics + uncertainty.
- \`IndependentVerdict\` — oracle version, known-good/bad preflight, deterministic checks vs human judgments, rejection reasons, conflict and confidence.
- \`QualificationEnvelope\` — **derived** \`QUALIFIED|RESTRICTED|REJECTED|INCONCLUSIVE|NOT_TESTED\` per design class × task × platform × input region; never global rank.
- \`ParticipationEvent\` — submit/edit/propose/observe/challenge/review/reveal/stop decision with principal type, role, scoped authority, prior version and evidence refs; append-only, not a parallel task DB.

**API action vocabulary for every audience:** \`discover\`, \`describe\`, \`propose\`, \`validate\`, \`plan\`, \`execute\`, \`observe\`, \`compare\`, \`challenge\`, \`review\`, \`export\`. Some operations may be read-only, gated, or deferred; unavailable actions must surface a typed reason, never silently succeed.

## Dependency-ordered implementation and acceptance plan

Machine-readable mirror: [\`workplan.v1.json\`](workplan.v1.json). The JSON is a *planning DAG*, **not an executor queue**; READY is advisory and DLE/workcell authority always controls placement. Everything below is open except **P0 planning reconciliation** initiated by this document.

| ID / phase | What to build | Dependencies | Objective acceptance / exit gate |
| --- | --- | --- | --- |
| **P0 Authority and contract mapping** — **READY** | Map existing public/private-safe *schema semantics* and DLE states. Inventory current Go source, Flora F1g, Fauna F2a and Mechanica known fixture references without importing their private data. Define exact user operations and threat model. | None | Crosswalk existing Model Spelunker fields; map states to owning DLE without creating another authority; inventory public-safe source digests; explicit rejected private-data paths; 3-audience journey tests described. |
| **P1 Go semantic core** | Add \`tropical-fauna-flora/cmd/componentinterview\` or \`internal/componentinterview\` (stdlib-first) strict bounded JSON schemas and deterministic canonical receipts. Validate DAG and typed semantic ports, absence of cycles, dimensions, units, timebase, authorizations/provenance. | P0 | One known-good and >=8 negative cases: cycles, duplicate semantic IDs, rigid-vs-skinned masquerade, mismatched axis/unit/timebase, rights-uncleared input, unauthorized venue, missing independent verifier, resource budget overflow, trailing/unknown fields. \`go test -race\`, \`go vet\`, exact fixture/digest replay. |
| **P2 Candidate/source primitive interviews** | Record pinned source versions, algorithm, data structures, pre/post invariants, CLI/headless support, cost and source rights for Go GLB, Blender Workbench, PlantGL/MTG/L-Py, VTK, original fauna graph and renderer. | P0,P1 | >=2 source-qualified provider bindings with honest capability gaps; first failing API/input trace; no claim that incomparable original Go banana vs synthetic L-Py branching are same species. |
| **P3 Minimum DOE planner** | Implement paired single-variable crossover and matched replication over compatible typed graphs; no full Cartesian enumeration. Capture frozen factors, design blocks, seeds, random order, effect/interaction hypotheses, stop rules, per-run budget. | P1,P2 | One same-fixture/same-oracle crossover or explicit \`INCOMPATIBLE\` finding; independent known-good and known-bad oracle; immutable separate runs and conditional envelope; difference in provider cannot change scope/rights. |
| **P4 Hosted execution adapter** | Generate bounded public-safe GHA workcell packets, idempotent dispatch/resume through existing GitHub/Agent Dispatch surfaces, read back independent outputs; annotate first failure. No new scheduler. | P1,P3 | Exact-head public CPU runs on approved source, zero non-public inputs, step and artifact SHA readback, concurrency-safe attempt IDs, no false-green on missing render/receipt, preflight failure classified as infrastructure. |
| **P5 Three-audience *authoring and review* slice** | Human accessible mobile-friendly GUI: discover, DAG manipulate, factor/controls proposal, validate, submit, observe, blind A/B, challenge/review. Automation Go CLI and JSON API adapter. Agent discoverable typed tool/descriptor through existing bounded control plane. Common append-only participation ledger. | P1,P3,P4 | **All three** can submit the *same* meaningful experiment and challenge a result; serialized digest and validator/authority verdict match exactly. Screen-reader/keyboard, status not color-only, English/German/Thai display-ready. Agent cannot bypass human disclosure/approval. Static report by itself FAILS P5. |
| **P6 Domain composition interviews** | Execute Flora geometry & lineage, Fauna root-joint/contact, Mechanica articulation and ecological time/resource traces through typed adapters; per-domain independent oracles. Human/identity remains separate protected lane. | P2,P3,P4,P5 | At least one valid 2-stage composition and one deliberate port mismatch per included domain; no false species/anatomy/physics claims; source-preserving native artifacts for human editors and structured evidence for agents. |
| **P7 Optimization and platform DOE** | Qualify external OpenMDAO/OpenTURNS/Optuna/BoTorch or Go-compatible adapters **only** when screening data demonstrates informative factor interaction or expensive objective. Evaluate CPU vs CUDA, MLX, TPU as *platform treatments* with same frozen semantics/rights. | P3,P6 | Blocked sparse design, repeated seeds, confidence and Pareto frontier; adaptation never spends outside grants. Unsupported/expensive platforms stay \`NOT_TESTED\`, not \`FAIL\`. |
| **P8 Hardening, operations and federation** | Schema migration/replay, source-license refresh and revoked candidate handling, supply-chain pinning, numeric tolerance and drift sentinels, backup/export, incident/first-failure record and cold-start DLE baton; cross-project reuse via adapters, not copying authority. | P4,P5,P6 | Controlled failing/fake receipts rejected; revalidation triggered by model/provider/version/ABI/rights drift; no secrets in output; same human/automation/agent views from one evidence source; no forbidden release action. |

### Milestone sequence / no circular dependencies

\`\`\`text
P0 [READY] -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7
                   \-------> P3 --/
P4 + P5 + P6 ---------------------------> P8
\`\`\`

Do **not** regard stage numbers as calendar deadlines. Within P2, adapters may run independently once P1 contracts exist; within P5, read-only views can be demonstrated early, but milestone acceptance requires full human creation/review and agent/automation parity. A novel provider only enters the qualification campaign when there's a concrete task-conditioned hypothesis.

## Three-audience journey acceptance matrix

| Journey | Human/UI | Automation/DX | Agent/DX | Must be common |
| --- | --- | --- | --- | --- |
| Inspect existing candidate | searchable evidence, topology/units shown, model explanation | \`describe --json\` | \`capabilities/describe\` | Same candidate ID, source hash, rights and limits |
| Create candidate graph | visual connect/substitute, preview invalid port in accessible plain text | \`propose --spec\` + \`validate --dry-run\` | \`propose/validate\` under scoped delegation | Same normalized DAG digest, reasons and validation code |
| DOE configuration | interactive hypotheses/factors/budget/controls | versioned plan and dry-run matrix | formulate, freeze and propose trial | Frozen factors, samples, control IDs and budget |
| Execute and observe | authorized start/stop, progress/first-failure timeline, side-by-side outputs | \`execute/observe/export\` with immutable receipts | same without expanded permissions | Same workcell and result IDs; no ghost success |
| Review/adjudicate | blind sources, controlled reveal, human annotations, explicit authority | independent \`verify\`, reviewer event | challenge/counterexample and evidence event | Append-only event history; no executor self-acceptance |
| Resume | view READY baton, issue/PR and native artifacts | idempotent \`resume/status\` | DLE baton, exact issue and immutable context | State reconciled with GitHub and existing controller |

Accessibility: keyboard/screen reader, contrast and text labels, responsive iPhone width, and no significance conveyed only by color. Display labels can be EN/DE/TH; machine enums/IDs never translated. Keep all artifacts editable where their medium permits (\`.blend\`, procedural source, CSV/JSON, GLB plus origin/provenance), not images-only.

## First pilot: what exactly to execute

**Public source only:** Go \`tropical-fauna-flora\` low-poly scene, 3-source synthetic vegetation comparison from Flora F1g, and F2a buffalo/egret source joint inventory. The human QA baseline is the independently replicated five-image RGBA digest—not biological ground truth. Preserve F2b real hoof/toe contact sampling as a separate Fauna workset.

1. Frozen public task A: inspect same source GLB and its semantic topology, including adversarial duplicate display names and distinct immutable IDs.
2. Candidate treatment A: original Go source graph/geometry and render adapter. Candidate B: OpenAlea/Blender provider adapter **only if semantic input/output ports match**; otherwise emit an explicit incompatibility receipt and choose a narrower, honestly compatible render/export A/B.
3. Keep same source asset, seed, camera, SI units, renderer setting and verifier when swapping one provider. For PNG, record both file and decoded RGBA hashes; compare numeric geometry and topology separately.
4. Independent controls: known-good same-source replay; known-bad altered joint ancestry; fake species claim; swapped units; corrupted PNG or manifest; impossible budget. Validator is independently preflighted before comparing candidates.
5. Three participation reps: a human composes and submits a trial via GUI, deterministic automation via CLI, and an agent proposes, queries and challenges via typed tools with **the same** authority. Derived results are diffable, show first failure, keep negative observations.
6. Success is a task-conditioned capability envelope stating \`QUALIFIED / INCOMPATIBLE / INCONCLUSIVE / RESTRICTED\` with sample size and limitations, not a winner banner.

## Operational ownership and security

- Product design and public science claims: **Stable Character Pipeline #5**.
- Reusable model/actor interview semantics: **Model Spelunker #54; Agent Dispatch #104** respectively, accessed via public-safe *contract mapping*, not import of their private records.
- Worker execution and sealed/private placement: **Agent Dispatch existing authority**, not a new scheduler or project-local unilateral delegation.
- Protected human/identity data: remain under their own private project authority, **never** public Flora/Fauna DOE.
- Source/model/data rights: must be explicitly checked for each candidate and artifact; a public webpage isn't a transferable license.
- Scientific realism decisions, external publication/promotion, merge/release/deploy and authorization widening: **explicit human/owner gates**; no new permission follows from this work plan.

## Falsification and red/blue controls

- Untrusted logs, web content, model outputs or tool descriptions cannot mutate the DLE/authority, override a verifier, or confer promotion.
- Mismatched glTF Y-up vs source Z-up, centimetres vs metres, MTG vs rigid node graph, and different frame rates must not pass as compatible just because file suffixes match.
- Publishing raw human, third-party rights-uncleared source, model API keys or private profiles to public Actions must be refused before dispatch.
- Candidate \`exit=0\` without required artifacts, valid SHA/receipts and independently corroborated expected state is a **failure**.
- Setup failures (apt timeout, unavailable library, missing GPU) are execution/environment observations, not automatically evidence of bad scientific algorithms.
- UI-only bypass, agent-only unreviewed execution or color-only failure disclosure means **three-audience acceptance FAILS**.
- Repeated stochastic trials must append observations; an idempotent retry of *the same execution request* must not silently create extra billed/authorized work.

## Immediate READY baton (P0)

**Discover:** read exact approved task/experiment/receipt vocabulary from Model Spelunker public implementation and existing bounded Agent Dispatch role/placement semantics; current Stable Character DLE #5 / PR #4/#13/#26.

**Observe:** list representation differences (glTF rigid nodes vs \`skins\`, MTG vertex IDs, source unit/axis, random seed/timebase, public/private provenance) and gaps in human/automation/agent proposal/review.

**Plan:** define minimal schema crosswalk, candidate-port type taxonomy, deterministic Go test vectors and shared permission outcomes; decide stage adapters, not parallel workflow infrastructure.

**Apply:** create a separate scoped Go-first P1 candidate workcell *after* P0 crosswalk, with strictly synthetic inputs, no merge, all change sets in draft PR; keep this plan file and machine mirror versioned.

**Verify:** P0 exits when mapping proves one common canonical proposal/validation response for all three audience adapters, an explicit invalid type case and a denied unauthorized operation; source links plus next workcell/receipt recorded in issue #5. If any missing tool/authority blocks an audience, record \`BLOCKED/INCONCLUSIVE\` rather than quietly replacing participation with read-only mock data.

**No action in this planning PR** changes runtime source, workflows, admission policy or publication. This is a ready-to-execute work plan; implementation status remains **OPEN**.
