# Audio Control R0 — parallel execution workset and cold-start baton

State: WORKING / 2026-11-22; source authority [Audio Foundry #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9), canonical portfolio [Way of Working](https://github.com/SemperSupra/engineering-governance-private/blob/main/WAY_OF_WORKING.md). This is a **project-local executable workset projection**, not a new scheduler, registry, delegation grant or another product. The original public scene/voice/spatial workcells and Aural R9–R11 retain their owners. Never promote or merge a draft without applicable existing authority and independent qualification.

## Batch controller for all actors (including weaker local models)

At each wake:
1. Read root `AGENTS.md`, owning [issue #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9), and this workset. Read current PR/commit/run evidence; preserve accepted results. Do **not** make the human transport a transcript, paste a prompt wall, or repeat already accepted research.
2. Form **all READY tasks with no cross-file or effect dependency**. Prefer 3–4 small workcells per round when feasible, each with one branch/PR, explicit path ownership, one measurable deliverable, source/CI command, synthetic data only, and terminal receipt. Launch the eligible workcells concurrently using **separate branches and public standard GHA**, not sequentially in one actor. One interactive assistant issuing 3 independent GitHub writes is *batched orchestration*, not proof of three simultaneously running LLM actors. Treat actual CI job concurrency and runner/job receipts separately.
3. Each cell: Discover → verify baseline → change ONLY owned paths → test → publish exact SHA, run/job URL, pass/fail and next blocker to owning issue. Fix locally if tests fail; record first failures instead of burying them. Weak actors receive a bounded task, exact file names and exact command, **not** vague 'finish architecture', 'scan all repositories' or unsupported "autonomy". Don't start a new coordinator, backend, repository, profile or extra DLE to coordinate this.
4. Integrator may compare disjoint cells and plan a merge **only after** each source SHA has accepted qualification and conflicts/overlap have been explicitly reconciled. Output artifact correctness is independent of CI status. Consequential merge, acoustic device access, credential use, clinical or private user data, production service, public release and paid/private runner use remain separate owner gates.
5. Keep enough independent READY work queued to hide runner latency. If only one cell is feasible, state the dependency and continue, rather than feigning parallelism. If an external actor is unavailable, do independent repository research/tests/hygiene while its lane remains READY; do not wait idle. Stop when authorization/resource/safety gates require human intent.

## Live disjoint batch matrix

| Cell | Authority, source / base | Owned paths / precise deliverable | Acceptance/evidence and dependency | Allowed venue |
| --- | --- | --- | --- | --- |
| C0 contract and parent DLE | [PR #722](https://github.com/SemperSupra/stable-character-pipeline/pull/722), base `main` | `docs/architecture/**`, `AGENTS.md`, `audio-control/contract/audio_control.r0.schema.json`; publish schema, ownership, invariants and current workset | Human-/host-authorized events remain separate; no expanded permissions; draft until review | GitHub connector, public review |
| C1 reducer | [PR #723](https://github.com/SemperSupra/stable-character-pipeline/pull/723), stacked on C0 | `audio-control/control/reducer.go`, `capability.go`, `cmd/control-probe/**`, existing unit tests | Source exact-head [3-OS green run 44974059696](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44974059696) at `04dc32d...`; no new unsupported effects. No merge | Public standard GHA |
| C2 adversarial falsifiers | `test/audio-control-r0-adversarial-fuzz`, stacked on #723 | **Only** `audio-control/control/adversarial_test.go` and `.github/workflows/audio-control-r0-adversarial.yml` | Seeded/short mutational traces prove no STOP resurrection, no forged host ingress, replay/no redispatch. Independent public GHA; fix exact SHA if red | Public standard GHA |
| C3 portable protocol validation | `test/audio-control-r0-protocol-vectors`, stacked on #722 | **Only** `audio-control/contract/vectors-r0.json`, `scripts/audio-control-contract/**`, `.github/workflows/audio-control-r0-schema.yml` | JSON-Schema 2020-12 positive/negative 13-row suite, principal scope, host-only semantics. Valid host schema != trusted caller | Public standard GHA |
| C4 actual offline media adapter | `experiment/audio-control-r0-scene-bridge`, stacked on [existing scene PR #11](https://github.com/SemperSupra/stable-character-pipeline/pull/11) | **Only** `audio-foundry/offlinecontrol/**` and `.github/workflows/audio-offline-control-r0.yml` | Reuse existing `scene.Manifest.Plan/Render/VerifyWave`, synthetic WAV, no overwrite, tamper rejection, honest retry-not-equal-idempotency; real FFmpeg on public CPU | Public standard GHA |
| C5 Aural consumer review | [Aural convergence #5](https://github.com/SemperSupra/aural-observatory/issues/5), R11 draft workcells | Aural issue/DLE only; no Aural source mutation from this workset | Confirm QuietSearch phase, patient device human permission, stop lifecycle. No automatic Go embedding | GitHub issue review |
| C6 red/blue acceptance | AFTER C1–C4 are individually green | No implementation paths; review PR diffs, schema/effects conflict, crash/saturation boundary and precise CI receipts | Gate to integration, not permission for merge/release/device tests | Separate reviewer |

**Parallel:** C2, C3, C4, and read-only C5 can run simultaneously on disjoint branches; their CI jobs can run concurrently. C0 and C1 are already existing base contracts, not work to reinvent; C2 depends *logically* on the frozen C1 source snapshot and C3 on C0 schema, but they can proceed in parallel after those snapshots. C4 uses the existing PR #11, so it does not need to wait for C1's Go reducer. Source merges/integration must be **sequential** to respect stacked base branches. An R0 experimental schema/draft cannot be promoted to universal portfolio policy without each owner's acceptance.

## Constraints, safety, and housekeeping

No direct `main` writes. Keep PRs draft, document tested versus unknown, no private Actions quota, no protected voice/medical data, no live input/capture/physical audio, no hardware claims from CI. Distinguish accepted command from observed effect. STOP must work under full dedupe ledger; receipts may be degraded, but not falsely replay-safe. An agent/voice transcript cannot forge a host event. Preserve resource/time budget; avoid repeated one-at-a-time work when other READY tasks have disjoint paths.

One unused branch `experiment/audio-control-r0-offline-adapter` was created from R0 doc head without edits. **Hygiene:** it has no PR or source changes. Leave it inert; delete after the current actor verifies its exact ref and uses an authorized branch deletion capability. Do not repurpose a branch non-fast-forward or force-reset without explicit lease and review.

## Local actor cold start — minimal

```text
Resume SemperSupra/stable-character-pipeline from root AGENTS.md, Audio Foundry issue #9, and docs/architecture/AUDIO-CONTROL-PARALLEL-WORKSET.md. Execute all READY disjoint workcells concurrently using their owned paths and public free-tier CI; verify exact SHA/run receipts, preserve safety/merge gates, and update #9. No human copy/paste baton.
```

## Closing rules for an iteration

Report number of **independent cells ready / actually launched / source complete / CI green / blocked / merged**, never substitute PR count for true concurrent execution. Batch critical path is C1/C0 frozen contracts → parallel C2/C3/C4 → independent acceptance C6 → *owner-governed* sequential adoption. When a cell turns red, repair its own branch while other green cells continue. If a cell is blocked by missing host/credential authority, record a bounded blocker and continue other cells.
