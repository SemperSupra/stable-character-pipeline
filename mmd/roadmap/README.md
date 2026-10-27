# Motion qualification work plan — active DLE-backed execution

**Authority:** [SCP public issue #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19).
**Working change set:** [unmerged draft PR #20](https://github.com/SemperSupra/stable-character-pipeline/pull/20), branch `qualification/mmd-public-20261027`.
**Canonical state:** [workplan.v1.json](workplan.v1.json); this document is the **human view and explanatory contract**, never a second task database.
**Research:** [2026-10-27 multilingual sweep](../research/2026-10-27-dual-track-motion-qa-prior-art.md); [frozen blind-seed matrix](../research/g11-blinded-concept-sweep-seeds.json).
**Status:** research-only public synthetic test qualification; no merge, publication, deployment or candidate policy promotion.

## Prior proven foundation

- G1–G8: source-native PMX/VMD/VPD, Blender import, animated GLB, weighted rig, second converter and glTF temporal alignment.
- G9: genuine native VMD eye/mouth vertex morphs; source vs Blender glTF parity [run 40455150395](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455150395).
- G10a–d: original two-link IK; independent goal tracking, genuine Blender IK-link alignment and fail-closed two-engine goal-error gate [run 40456784554](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456784554). The initial genuine red G10d is still preserved in the DLE.
- G11A: official Khronos validator on five original GLBs, zero format errors, two non-root skinned-mesh warnings, corrupted GLB deliberately rejected [run 40458065375](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40458065375).

These do **not** prove native MMD CCD/physics, joint-trajectory equality, foot-ground friction, photorealistic faces, model identity, humanoid retarget, arbitrary skin fidelity or any external model license.

## Execution rules and stage gates

1. **Discover:** discover existing code, standards, licenses and primitive semantics before writing custom algorithms. Keep native Japanese/Chinese terms as aliases with provenance rather than silently translating technical facts.
2. **Observe:** reconcile issue #19, draft PR #20, immutable source pins, last *terminal* GHA run, source rights and concrete first failure. `NOT_TESTED`, `UNKNOWN` and `BLOCKED` cannot become `PASS`.
3. **Plan:** read the machine-readable dependency graph; execute the lowest-numbered READY task with satisfied prerequisites, respecting budget/rights/candidate admission. Independent tasks may execute concurrently only when they do not share mutable refs or confidential state.
4. **Apply:** add source in the public branch as *candidate* only. Favor existing upstream algorithms and Go stdlib orchestration; use Blender Python or WASM/JS narrowly where upstream requires. Keep CI jobs $0, bounded, source-only/rights-clean and separately triggered.
5. **Verify:** assert real artifact bytes, behavioral traces, failure-injection controls, cost ceiling, exact SHA/run and optional human media. Keep the failed gate; don't reduce thresholds because red. Commit evidence and a next baton in DLE, then promote task to DONE only with an exact verified source.
6. **Boundary:** never merge, deploy, release, publish restricted assets, expose source/private identities, or automatically mutate CPE policy. Research from public gets a candidate-only handoff to an authorized private workcell when needed.

### Definition of DONE, independent outcome states

A work item can be DONE only when its dependency gates are DONE, tests or specified acceptance conditions were actually observed, and a verifiable evidence URI is recorded. A run's green status alone does **not** confer general animation correctness. Research exploratory tasks may complete with falsified candidate claims if the hypothesis was tested and documented, but the candidate capability itself must remain FAIL/NOT_TESTED as appropriate. The workplan status means *work executed and verified*, whereas individual artifact/engine evidence may be PASS, FAIL, NOT_TESTED, UNKNOWN or BLOCKED. Artifacts expire after approximately 14 days: source + pinned workflow, not temporary ZIP URLs, are the durable reproducibility anchor.

### Audience contract

| Audience | What it must be able to do | Representation |
|---|---|---|
| Human | See workstream, live readiness, why a gate failed, contact sheets/short phone-playable previews, genuine capability limits and source-rights status | This document, generated `plancheck -format=markdown`, DLE and portable media |
| Automation | Reproduce/validate public source artifacts, run tests, apply filters, parse a stable summary and fail closed | Go `plancheck -format=json`, JSON Schema/evidence, $0 GHA and versioned commands |
| Agent | Discover ready assignments, understand requirements/inputs, observe and propose the next bounded action without bypassing approval | Same JSON and DLE, explicit statuses/dependencies/authorization and evidence refs |

No independently mutable human/automation/agent copies of task status. The Go CLI is **read-only** and cannot dispatch or make GitHub policy/release changes.

## Phased dependency plan

| Phase | Work items and outcome | Exit / risks |
|---|---|---|
| **P0 Authority/contracts** | W01 Go DAG/readiness verifier; W02 typed fixture/evidence/semantics; W15 source-rights/provenance; W21 $0 runner guards | One source of truth; source rights and machine/human parity; no paid paths |
| **P1 Independent engines** | W03 investigate Khronos warning; W04 babylon-mmd headless smoke/pin; W05 three-engine G7/G9/G10; W07 official generated conformance corpus | 3 genuine observations **or explicitly NOT_TESTED**; standards vs behavior kept separate |
| **P2 Motion and dynamics** | W06 metamorphic invariants; W08 independent math frame graph; W09 full motion curves; W10 foot contact/slide; W11 physics/cloth/hair | No more quaternion sign, time-origin or IK-length false positives; state confidence explicit |
| **P3 Scene and rig semantics** | W12 PMX morph/material/UV; W13 retarget human/animal/mechanical; W14 USD/UsdSkel; W18 editable original interactive scene | MMD-to-generic semantic losses known; rights-clean portable/editable demonstration |
| **P4 Experimentation, UX, global research** | W16 factorized experiments/model+actor qualification; W17 three-audience operations; W19 blind independent multilingual CPE/SearXNG; W20 independent reconciliation | Compare candidates fairly, control false discovery and never grant CPE policy from public findings |

The full 21-task manifest includes explicit per-task dependencies, budget and executor, first action, evidence requirement, testable acceptance, risk and audience coverage. Use it for precise READY counts rather than manually inferring dates.

### The first high-value action sequence

**Now (parallel, isolated)**:
- W01 validate/go-test this roadmap, W03 reproduce the `NODE_SKINNED_MESH_NON_ROOT` warnings in a second glTF reader before touching exporter code, W04 inspect/execute pinned babylon-mmd headless on original assets only.
- W06 start seeded metamorphic failures (time shift; scale; transform; broken IK and weights), W07 reuse Khronos' asset-generator suite, W21 verify scopes, pins, immutable artifacts and public $0 budgets.

**After Go contract W01 passes:** W02 becomes READY; implement `FixtureSpec`, `SourceSemantics`, `EngineObservation`, `MetricEvidence`, and `ProofBundle` v1. Do not duplicate Khronos glTF parser, Pinocchio dynamics or a native MMD solver.

**Then:** W05 third-engine exact sample comparison; W08–W10 true 31-frame joint and planted-foot/ground metric tests, replacing endpoint-only conclusions. W11 and W12 remain separate physical vs morph branches.

**Only after adequate evidence:** expand to retarget, USD and interactive composition. Public work remains original synthetic; private human identity and source rights require their own admission boundary.

**Independent language track:** W19 is **BLOCKED on verified authorized CPE/search-adapter runtime and frozen snapshot**, not blocked on invention or lack of search terms. W20 cannot run until W19 and rights/provenance W15 are complete. Track A results are not used to contaminate blind Track B inputs; proposals are not policy changes.

## Reproduction for all audiences

From `mmd/roadmap`:

```bash
go test ./...
go vet ./...
go run ./cmd/plancheck -input workplan.v1.json -format=json
go run ./cmd/plancheck -input workplan.v1.json -format=markdown
```

The isolated workflow `.github/workflows/mmd-workplan-validation.yml` runs these commands on public Ubuntu without paid dependencies, emits a JSON projection and human Markdown, and uploads both as a 14-day Actions artifact. Workflow evidence, commit SHA and next baton go into the authoritative DLE, not an untrusted chat attachment.

## Red/blue adversarial checklist

- **Reference substitution:** All independent comparators must pin the exact source PMX/VMD asset hash and CI run/artifact SHA. An expired ZIP cannot accidentally become a newly qualified input.
- **Conformance != semantics:** Khronos output errors/warnings are distinct from morph trajectory, physics validity, contact correctness and license readiness.
- **Independent oracle:** Correct quaternion matrix/axis/unit conventions against a separate implementation, reject wrong graph ancestry and frame0 shifts, never waive actual bone parentage.
- **Metamorphic tests:** Move world/goal together, normalize scale, shift temporal origin, rename only non-semantic wrapper, flip incorrect handedness as a negative; track mutation kill and survivors.
- **Rights:** Open-source code licenses do not authorize models, textures, dances, voice or music. Training/viewing, local derivative, redistribution and commercial usage are independently gated by source.
- **CPE isolation:** Track A may suggest concepts; Track B uses immutable same questions with blinded evidence; authority for CPE policy remains elsewhere.
- **Cost:** No billed GPU, secret/private runner or contingent services; no unbounded workflow fanout. Preserve failed evidence and do not rewrite historical statuses.
- **Audience fidelity:** The same task should be legible and controllable through the human presentation, automation CLI and agent-visible JSON. All share the same underlying DLE authority.

## Verified execution state and next baton (2026-10-27)

**W01 DONE:** the machine-readable plan and read-only Go DAG readiness checker passed in [public run 40467605178](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40467605178). A deliberate regression surfaced after updating the plan to W01 DONE/W02 READY: [run 40467719885](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40467719885) failed because the *cycle negative test* had temporarily changed W01 to PLANNED while leaving W02 READY. The test was isolated by setting W02 PLANNED during that intentional cycle mutation, without relaxing any production readiness rule. Full Go tests/vet and identical machine-readable JSON + human Markdown projections then [passed in run 40467817048](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40467817048); proof artifact 12717685547, ZIP SHA256 `e60e30995e92390e3d4452fd26b2f3787f7eadc94b140e6fddaa3ad3c809dfb2`.

**Canonical status:** 21 tasks; **1 DONE, 6 READY, 12 PLANNED, 2 BLOCKED**. Verified READY tasks: W02 Go typed fixture/evidence/source semantics contract; W03 Khronos non-root skinned-mesh warning reproduction; W04 babylon-mmd source-pin/headless execution; W06 original metamorphic tests; W07 glTF Asset Generator corpus; W21 $0 runner/privacy/source SHA hardening.

**Highest READY next baton: W02**, supported by completed W01. Build Go typed v1 `FixtureSpec/SourceSemantics/EngineObservation/MetricEvidence/ProofBundle` contracts, golden JSON, unknown-rights/time/axis failure cases, and an isolated $0 public CPU proof. Rely on Khronos for general glTF, established robotics for mathematics and existing MMD engines for runtime, rather than rewriting each. W03/W04/W06/W07/W21 can run independently if files/workcells do not conflict.

W19/W20 remain BLOCKED on verified authorized blinded CPE/SearXNG access and approval conditions. Do not leak private source or present Track A as an independent dual-track comparison. Continue Discover → Observe → Plan → Apply → Verify with true failures and DLE baton, and **no merge, release or deployment**.
