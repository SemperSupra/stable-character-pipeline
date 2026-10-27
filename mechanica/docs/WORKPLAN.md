# Mechanica — Executable Work Plan (WoW/DLE)

**Plan revision:** MP-2026-10-27-r1 | **State:** PLAN APPROVED IN PRINCIPLE, EXECUTION NOT PROMOTED | **Date:** 2026-10-27 CET  
**Authority:** [Mechanica producer DLE on draft PR #6](https://github.com/SemperSupra/stable-character-pipeline/pull/6); **this file is the reproducible work-package specification**, not a competing authoritative state database. Always reconcile the latest DLE baton and GitHub before running.  
**Previous decision/evidence:** [red/blue audit](https://github.com/SemperSupra/stable-character-pipeline/pull/6#issuecomment-6435086714) · [multilingual prior art](https://github.com/SemperSupra/stable-character-pipeline/pull/6#issuecomment-6434947938) · [actual physics observations](https://github.com/SemperSupra/stable-character-pipeline/pull/6#issuecomment-6434824538).

## 0. Owner intent and definition of success

Build a composable, inspectable pipeline to **create, rig, control, test and exchange original synthetic machines**: SUV, twin-engine aircraft, orbital tug and Iron Atlas walker, then extend by qualification to further vehicles, aircraft, spacecraft and mechanisms. **All three audiences (human, automation, agent)** must be able to discover a machine's capabilities, command an actuator, inspect desired versus observed state, diagnose failure and retrieve reproducible evidence from one underlying contract.

**Optimize** for mechanical correctness, $0 authorized public execution, interoperability, low-dependency Go orchestration, fast offline regression and durable evidence. Do not optimize merely for visual plausibility, maximum simulator count or the number of exported formats.

### Immutable baseline for first experiments

| Fact | Verified baseline / authority |
|---|---|
| Producer draft PR #6 | `ee3f027a2d1e05b9a1b44dd5c5569a19b35dd4d1` (open, unmerged, unchanged as of plan) |
| Independent qualification draft PR #17 | `2fdd627f0cf895951695703cbda17ff259c64f99` (open, unmerged as of plan) |
| Input preview | `mechanica-previews@c43bab2560a42c8ad880e13f7c32926b9cf9b0ef`, GLB SHA-256 `19573f420f8c089842a04ec15664afb35829d587ed87a81c45ee00752c3a1aa8` |
| Existing positive evidence | 4 rigs, 135 meshes, 50 animated joints, 43 bounded revolute + 7 continuous, 670 authored keyframes; joint axes/limits inspected by Go; 9/9 Blender framing samples; independent source/model CI green |
| First **E0 source defect** | `mechanica/main.go` glTF `extras.rigs = 3` while manifest, builder and Blender observe **4** rigs; no parity test currently prevents it |
| First **E2 mechanical defects** | Iron Atlas both feet 0.535 m above inferred SUV support plane at neutral pose. Fixed -0.535 m root shift causes -0.13441 m penetration for one foot at sampled frames 48 and 96 |
| Collision evidence | 9 selected AABB candidates over five sampled poses; 7 confirmed triangle-*surface* intersections involving SUV tailgate/chassis and front tires/chassis (not a comprehensive collision solver) |
| Green pinned public evidence | [Go/source](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40457262240) · [Blender/media](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40457257432) · [physical observations](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40457257360) |

**Explicit boundaries:** original public synthetic art/data only; *completely separate* from human-character/Flora/Fauna/private branches and identity material. No licenses assumed for new CAD, MMD, external model files, learned datasets or executable third-party artifacts. **No merge, release, deployment, production gate promotion, private runner minutes, paid cloud, new authorization policy, or rights adjudication without explicit owner authority.** No automated shared-protocol promotion. Ordinary candidate writes may occur only to scoped independent draft workcells; immutable preview/producer branch remain untouched unless separately authorized.

## 1. Architecture: minimal vertical slice first

```text
Original geometry / source model (Go, Blender or CAD)
            │
Versioned **thin mechanism contract**: stable machine+part+joint IDs,
coordinate frames and units, local transforms, joints/limits,
actuators, collision groups, capabilities, provenance references
            │
ONE deterministic Go actuator evaluator/state machine
(validate → plan → apply to disposable target → observe → verify)
          /          |                \
Human GUI/UX      CLI/JSON          Agent capability/tool schema
          \          |                /
       Identical fixtures, commands, state/event semantics
            │
Optional adapters: glTF + KHR_interactivity viewer; Blender;
URDF/SDF/MJCF/USD; MuJoCo CPU; specialist domain simulators later
            │
Independent E0–E4 evidence and rights/owner gates
```

Do **not** implement a general physics engine, a mandatory ROS 2 runtime, a generic interchange superset, one-off per-audience actuator implementations, or implicit CPE enforcement in Mechanica. Adopt lessons from ROS 2 controller lifecycle and Khronos tests without shipping those heavy runtimes as an MVP dependency.

**Mechanism contract v0 is a hypothesis, not accepted schema.** First use only one SUV door/hinge and its parent frame; extend by *measured capability gaps*: steering + continuous wheel, aircraft surfaces, spacecraft yoke, closed-linkages, walking multi-joint chain. Represent closed kinematic loops as constraints in later versions; do not pretend a simple tree can encode them. Keep authored intent, actual observations, asset animation, simulation state and provenance distinct.

### Proposed minimum command/result behavior

- Discovery `list machines` → `list parts` → `inspect actuator` (limits, kind, units, available operations, source version and current state revision).
- Command `plan` then `execute` with machine and actuator IDs, target numeric value+unit, expected revision, idempotency key, explicit requested action/limit behavior. **Reject** unsupported/unbounded/out-of-limit operations by default; opt-in clamp only with observed requested versus applied value and reason. No silent application.
- Lifecycle: `rejected | accepted | running | succeeded | failed | canceled` with timestamps, revision, source SHA, desired and actual state, first failure and evidence digest. Replay same idempotency token returns same disposition; stale revision does not overwrite newer state; bounded operation timeout, cancellation and preemption.
- Simulator and viewer are **adapters**, not command authorities. Reject unsupported KHR_interactivity features; fall back to standard viewer controls. No model-authored graph may access host filesystem, credentials or network.
- JSON/Go types are versioned, machine-readable and language-neutral; user-facing labels can be English/German/Thai, but IDs, SI/radians/units and error taxonomy must not be locale dependent.

## 2. Dependency-aware work packages

WoW status values: `DONE` = confirmed in this plan, `READY` = prerequisites present, `BLOCKED` = missing input/owner gate, `WAIT` = dependent, `HOLD` = outside authorization. READINESS DOES NOT IMPLY EXECUTION RIGHTS. Executed tasks update DLE with evidence, first failures and next baton; this table is an initial snapshot, not live status.

| ID / order | Status | Dependencies | Work package / substantive output | Proof and exit criterion |
|---|---|---|---|---|
| M00 / baseline | **DONE** | none | Reconcile PR #6/#17, four original rigs, manifests, pinned previews, qualification CI, ground/BVH evidence and last DLE baton | Live reads and immutable SHA receipts retained |
| M01 / first RED | **READY** | M00 | **Independent E0 contract and count parity falsifier**: glTF JSON/GLB/Go manifest coherence, rig IDs/counts, roots/parents, units/frame wrappers, per-joint axes, unique links/tracks; add adversarial corrupted fixtures | Existing `extras.rigs=3` vs 4 **fails** with exact diagnostic; corrected candidate passes only after source change separately authorized; corruption tests fail |
| M02 / shared contract | **READY** | M00; use M01 baseline | Minimum Go stdlib typed actuator evaluator on *one* synthetic SUV door. Identity-free, in-memory, offline. Draft narrowly; do not prematurely freeze project-wide schemas | Table tests including valid endpoint, wrong units, limits, NaN, duplicate token, stale revision, unsupported joint, cancel/preempt and revision readback |
| M03 / UX/DX parity | **WAIT** | M02 | Three adapters for one actuator: human interactive 3D control, Go CLI/JSON, agent-readable capabilities/commands/state/errors. Same kernel and fixtures | Same set of command requests yields byte/field-equivalent logical outcomes, clear errors and accessible UI; browser CI pass, iPhone physical test still HOLD |
| M04 / interaction standard | **WAIT** | M02, M03 | Pin Khronos KHR_interactivity suite+runtime; run `prerequisites/Tests_required_operations`, minimal graph + invalid graph, then simulated hover/select; test export+runtime, support report and JS fallback | Actual runtime result and expected oracle match; skip unsupported with cause; invalid graphs rejected; do not label browser CI an iOS/Safari proof |
| M05 / experiment registry | **READY** | M00 | Candidate tool/model/algorithm catalog with source URL, revision, license/rights status, target architecture, expected primitives and qualification result; design-of-experiments schemas with substitutable stages | Registry validates deterministic JSON, provenance and alternative baseline; unresolved rights cannot enter production build |
| M06 / interchange | **WAIT** | M01, M02 | Loss-aware glTF ↔ one physics/interchange target (start URDF/SDF or MJCF), one hinged door; then steering+continuous wheel, solar yoke and leg. Track frames, angles and graph constraints | Numerical FK/joint-limit parity before/after conversion, strict `supported / approximated / lost / unsupported` report; no silent loss or “lossless” claim |
| M07 / Iron Atlas stance | **READY for independent candidate** | M00; E2 baseline | Deterministic stance/swing schedule, stance-foot target locking, root-height adjustment and analytical/damped-Jacobian IK; retain original source untouched | Across sampled+intermediate poses, grounded stance foot within declared tolerance, no >8 cm below-ground penetration, stable foot pose with visible swing; E3 remains HOLD |
| M08 / SUV geometry | **READY for independent candidate** | M00; E2 baseline | Diagnose front-tire/chassis at steered poses and tailgate/chassis at closed poses; collision categories and per-pair intentional/accidental rationale, pair-specific clearance | Triangle/distance tests and exact adversarial pose receipts; no blanket collision exclusion, no collision-free claim from sparse BVH |
| M09 / dynamic baseline | **WAIT** | M06, M07/M08 models sane | One pinned MuJoCo CPU disposable physical model with explicit masses/inertia/ground, gravity, contact forces, limits; compare with deterministic kinematic baseline | Positive and unstable negative-control scenes with reproducible full trajectory, contact impulses/forces and stability measures; gate E3 independently |
| M10 / specialist options | **HOLD** | M09, measurable unmet domain need | Qualify Project Chrono vehicle, JSBSim aircraft, Basilisk spacecraft, Pinocchio closed-chain/IK or Phobos CAD interchange as targeted alternatives | Comparative fidelity/cost/rights/risk win before admission; never simultaneously integrate all engines |
| M11 / learned/GPU/TPU | **HOLD** | M09 E3 baseline, rights+quota gates | Candidate physics batching on CUDA/MJX Warp and TPU/MJX JAX; optional learned gait conditioned on dynamic reference | Matched seeded scene, deterministic CPU truth, throughput/quality/error/confidence, license audit and explicit provider capability differences |
| M12 / true CPE/SearXNG dual track | **BLOCKED** | authorized live connectors/workcell | Equal-budget independent public-vs-CPE multilingual search with native terms and protected findings separated | Source/licensing/citation receipts, blinded relevance+overlap, documented unresolved concepts; *no CPE policy promotion* |
| M13 / CI/O&M | **READY** | M00; continuous | Minimize redundant GitHub Actions triggers and APT installations, run fast pure-Go fixtures first, pin dependencies/Actions by immutable SHAs, preserve short timeouts, provenance, DLE status and 7-day artifact expiry notices | $0 public runner only, read-only permissions, test for unavailable dependencies, no hidden fallback to private runner; reproductions work from exact SHAs |
| M14 / final acceptance | **WAIT + owner HOLD** | E0–E4, rights, device | Human visual and accessibility review, actual iPhone Safari interaction, creator workflow, repeatable agent/automation acceptance, source rights and authorizations | Signed/explicit acceptance per gate; no merge/release/deploy without separate owner authorization |

**Parallelism:** M01 + M02 + M05 + M13 can proceed in independently scoped public workcells with read-only source inputs; M07 and M08 can be planned/run in separate synthetic candidate branches and must not change producer baseline. Gate consumers M03/M04/M06/M09 await prerequisite receipts. Avoid simultaneous writes to same branch/file. PR #3 skeletal, PR #4 Flora/Fauna, private human character lanes strictly out of scope.

## 3. First executable batch — RED → GREEN, with clear commit boundaries

### M01: first to execute (P0)
1. **Discover:** Read current producer `mechanica/main.go`, original manifest/GLB, revision+SHA, #17 Go tooling, DLE. Verify current producer still has `doc.extras.rigs = 3` and actual rig count 4; if changed, stop and reconcile.
2. **Observe:** Add read-only offline Go 1.23 stdlib `mechanica/cmd/rigparity` in independent qualifier workcell. Verify JSON/GLB contents against manifest; compare glTF `extras.rigs`, rig names, root/node hierarchy, joint count/axis/limits and track count; verify immutable source inputs and finite values.
3. **Plan/Apply:** Write fixtures with matched 4-rig positive and mutated-count/duplicate-name/orphan-node/axis-mismatch negatives. **Run actual pinned GLB as expected RED** while preserving the original discrepancy as an explicit known open finding, not hiding it with an allowlist.
4. **GREEN candidate:** Make a one-line change to `extras.rigs` using derived `len(s.Rigs)` only on a separate approved producer candidate branch; regenerate GLB, rerun same verifier and old tests. **No modifications to producer PR #6 or pinned preview without explicit scoped authorization.**
5. **Verify/DLE:** Record both exact outcomes, SHAs, GLB receipts, first failures, regressions, missing authority and NEXT READY baton. Only after corrected candidate is independently green can metadata parity be considered technically resolved; merge/release remain HOLD.

### M02: minimal controller (P0)
1. Choose one original SUV hinged door: stable ID, parent frame, rotation axis, bounded angle limits; one logical state record, one command state machine.
2. Implement smallest Go stdlib `validate/plan/execute/observe` test double; no network, special plugins, ROS requirement or heavy simulators. Separate requested vs applied vs observed angles.
3. Property/fixture tests: exact limit, just outside limit, zero/NaN/Inf, wrong SI/degree unit, stale revision, repeated idempotency token with same or different payload, cancel, offline target unavailable and concurrent optimistic revision conflict.
4. Export stable provisional JSON contract with semantic version, error codes and known unimplemented capabilities. Evaluate future consumer fit before broadening to 50 joints.

### M03/M04: all three audiences as a single contract (P1)
- **Human:** visible door hinge control (mouse/touch/keyboard), highlighted selected part, target angle, allowed range, current/desired state, blocked reason, reset/replay, accessible labels and EN/DE/TH aliases. On-device Safari is a separately witnessed hold.
- **Automation:** `mechanica actuator list/inspect/plan/execute/observe` offline flags, JSON-lines/JSON output, documented exit codes, no GUI and no surprise downloads.
- **Agent:** capability manifest with typed inputs, discoverable constraints, named errors, side-effect boundary, goal IDs, cancellation/readback, deterministic replay. Cannot bypass controller validation by editing raw nodes.
- **Interop experiment:** KHR_interactivity graph on compatible runtime vs ordinary GUI wrapper. Compare the **same** canonical test vectors and observed machine revision. Do not claim Khronos interactivity works in generic glTF viewer without tested runtime.

## 4. Qualification / design-of-experiments discipline

Each substitution experiment **must** have: `experiment_id`, primitive, machine/sample, candidate revision+license, control/baseline revision, workload/seed, hardware/runtime, input hash, intended invariant, independent oracle, positive+negative fixtures, fixed cost/runtime budget, metrics, observed effect, first failure, decision `accept-for-next-test | reject | blocked | hold`, reviewer role and DLE link.

| Dimension | Initial options | Comparison metrics | Hard disqualifiers |
|---|---|---|---|
| Mechanism representation | Existing Go part tree / URDF / SDF / MJCF / USD Physics | topology fidelity, axis/frame error, constraint semantics, migration diff | silently lost degrees of freedom / cycles |
| Kinematic solver | direct FK / analytical 2-link IK / Jacobian DLS / Pinocchio | end-effector and stance error, singularity handling, deterministic performance | unbounded/NaN output, joint-limit violation |
| Geometric collision | imported actual-vertex AABB / Blender BVH / Coal distance | false alarm/rejected cases, minimum clearance, swept sampling | global pair exclusions, unclassified penetrations |
| Runtime interaction | web GUI bridge / KHR_interactivity on tested runtime | gesture-to-command equivalence, device support, timeout/errors, invalid graph rejection | unauthorized host effects or divergent machine state |
| Simulation | kinematic test double / MuJoCo CPU / specialist backend | trajectory/contact accuracy and performance, solver fidelity | fabricated physical evidence, missing mass/ground |
| Compute | public GitHub-hosted CPU first / permitted CUDA/TPU later | dollar cost, reproducibility, throughput, evidence retention | paid/private fallback, inconsistent input/rights |

Evidence ladder, independent and non-substitutable:

- **E0 Structure:** content hashes, rig/metadata/node coherence, valid glTF, provenance.
- **E1 Kinematics/control:** frame/axis/limit and interpolated trajectory tests, no stale/replayed effects, cross-audience semantic parity.
- **E2 Geometry:** support-plane conventions, stance contact at sampled/intermediate poses, collision broad+narrowphase + minimum clearance, justified intentional interfaces.
- **E3 Physics:** actual masses/inertias, gravity, reaction forces, friction/contact solver, physically stable trajectories and negative counterexamples.
- **E4 Interaction:** human accessibility, responsive viewer semantics, CLI+agent contract equivalence, actual device tests.
- **Cross-cutting gates:** source rights/provenance, privacy, owner authorization and release/deployment **separate** from E0–E4 success.

A green media or static GLB does not imply successful E2/E3/E4; a successful GHA job can record an intentionally failing model baseline if its measurement oracle succeeded. Be explicit with `PASS_INSTRUMENTATION / FAIL_MODEL / NOT_ASSESSED`.

## 5. Operational plan and WoW state machine

All execution is **Discover → Observe → Plan → Apply → Verify**, each in the smallest complete reversible workcell. Execution state belongs to latest PR #6 DLE, not chat descriptions or checkboxes in this file. Execute the highest READY action with explicit path/write permissions and evidence oracle; do not recursively start speculative dependent work.

**Start:** read newest DLE and PR status, confirm live producer/qualifier SHAs, preview GLB hash, current CI and concurrent actors. On drift, reconcile; do not apply an old baton.

**Run:** public synthetic jobs using GitHub-hosted public Ubuntu, normal repository free-tier capacity, `permissions: contents: read`, `persist-credentials: false`, SHA-pinned external actions/dependencies once vetted, bounded time/memory, no secrets. Never route work to private runner minutes or chargeable Kaggle/other cloud as fallback. Prefer stdlib Go and offline, headless tests. Separate file paths/branches for concurrent actors.

**Verify:** fresh checkout; prove positive and adversarial controls detect known faults; classify infrastructure/tool harness failure separately from model failure; inspect source-specific logs, structured JSON and hashes. Store **commit/asset SHA, workflow/job run IDs, exact artifact URI, expiry and reproduction command** in DLE. Seven-day GHA artifact is not a permanent human media repository; no automatic publishing as a workaround.

**Handoff:** durable record with exact `scope / prior SHA / current SHA / observed evidence / first failure / disposition / owner gates / highest READY next action`; after write, read back GitHub. Status transitions `READY → CLAIMED → RUNNING → VERIFY → PASS|FAIL|BLOCKED` with explicit next baton. Do not treat deployment, acceptance, or authorization as a natural result of PASS.

**Stop/fail closed:** ambiguous mechanical frames or units; leaked private inputs; external license unresolved; unsupported simulator feature; divergent CLI/UI/agent state; unbounded external dependency install; unauthorized write path; no deterministic test oracle; money/private Actions fallback; silent collision or conversion loss.

## 6. Decisions and criteria for moving the roadmap

| Decision gate | Minimum evidence | Authority |
|---|---|---|
| Admit mechanism v0 beyond one door | M01 parity, M02 state and negative tests, traceable loss report | Mechanica technical review in DLE, not automatic universal schema |
| Add Khronos graph runtime | M04 pinned prerequisite/invalid-case/runtime test and fallback | Technical adapter acceptance, no implication of iPhone support |
| Add collision/stance solver | M07/M08 repeatable model-specific improvements and negative countercases | Engineering qualification; no physics claim |
| Add MuJoCo or other simulator | M06 adequate frame/inertia conversion and independent E3 oracle | Separate engineering/source-rights gate |
| Train or import learned motion | E3 dynamic reference, source/dataset rights, GPU/TPU budget authorization | Owner CPE/rights/compute boundaries |
| Merge, release, deploy, publish non-ephemeral viewer | Accepted E0–E4 where applicable, explicit rights/device verdicts and **explicit owner action** | **Owner-only approval** |

**Plan is complete when:** work packages have executable proofs and DLE batons, not when all candidate tools have been installed. The project is *functionally complete* only when an original synthetic machine can be authored, rigged, controlled and independently verified through human, automation and agent interfaces, with transparent limitations and no unreviewed promotion.

## 7. Next baton for cold start

> Resume Mechanica from authoritative PR #6 DLE and derived `mechanica/docs/WORKPLAN.md` in draft qualifier PR #17. Reconcile source SHA and parallel actors. Execute **M01** on an isolated $0 public workcell: independent Go GLB/manifest/source rig-parity red test for the known three-versus-four metadata discrepancy, with mutated negative fixture; record exact run/evidence and next baton. Do not modify producer PR #6, published preview, or source-rights/merge/release/deploy gates without separate authority.

### Primary design references

- Khronos ratified glTF extension registry: https://github.com/KhronosGroup/glTF/blob/main/extensions/README.md
- Khronos KHR_interactivity tests and test-index procedures: https://github.com/KhronosGroup/glTF-Test-Assets-Interactivity/blob/main/Tests/Interactivity/README.md
- ROS 2 controller lifecycle and trajectory semantics: https://control.ros.org/master/doc/ros2_control/controller_manager/doc/userdoc.html ; https://control.ros.org/master/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html
- MuJoCo MJX cross-backend limitations: https://mujoco.readthedocs.io/en/latest/mjx.html
- Authoritative project evidence and more prior art: see DLE links at top.
