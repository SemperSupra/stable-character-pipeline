# Audio control R1 — independent PR-stack and safety acceptance review

Status **REVIEW / NO MERGE AUTHORITY** (2026-11-22). Source: [Audio Foundry #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9); [R0 parallel DLE](https://github.com/SemperSupra/stable-character-pipeline/blob/research/audio-capability-control-r0/docs/architecture/AUDIO-CONTROL-PARALLEL-WORKSET.md) and canonical Way of Working. This note is a review projection, not new project governance or a new repository. Inspect exact current GitHub PR state again before using any branch SHAs listed here.

## Stack ownership and branches observed

| PR | Base | Owned paths (from actual GitHub changed-file inventory) | Qualification at review baseline |
| --- | --- | --- | --- |
| [#722](https://github.com/SemperSupra/stable-character-pipeline/pull/722) C0 | main | `AGENTS.md`, `README.md`, `docs/architecture/**`, `audio-control/contract/audio_control.r0.schema.json` | Draft architecture/schema, **not production admission** |
| [#723](https://github.com/SemperSupra/stable-character-pipeline/pull/723) C1 | C0 `research/audio-capability-control-r0` | `audio-control/control/**`, `audio-control-r0.yml` | [3-OS run 44974059696](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44974059696) PASS |
| [#725](https://github.com/SemperSupra/stable-character-pipeline/pull/725) C2 | C1 | Only `adversarial_test.go` and dedicated workflow | [44987062335](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44987062335) PASS |
| [#728](https://github.com/SemperSupra/stable-character-pipeline/pull/728) N1 | C2 | Only `recovery_trace_test.go` | [44987402500](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44987402500) PASS, negative power/crash proof |
| [#726](https://github.com/SemperSupra/stable-character-pipeline/pull/726) C3 | C0 | `audio-control/contract/vectors-r0.json`, `scripts/audio-control-contract/**`, schema CI | [44987065128](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44987065128) PASS |
| [#729](https://github.com/SemperSupra/stable-character-pipeline/pull/729) N2 | C3 | New host boundary doc/fixtures **and intended update to its parent script** | [44987402348](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44987402348) PASS |
| [#11](https://github.com/SemperSupra/stable-character-pipeline/pull/11) scene | Earlier multi-stem work | Existing Go scene/custody/FFmpeg original | Original owner; keep unchanged |
| [#727](https://github.com/SemperSupra/stable-character-pipeline/pull/727) C4 | #11 scene branch | Only `audio-foundry/offlinecontrol/**` and CI | [44987151332](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44987151332) PASS |
| [#730](https://github.com/SemperSupra/stable-character-pipeline/pull/730) N3 | C4 | Only new `recovery_test.go` and `recovery.md` | [44987405653](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/44987405653) PASS |

**Parallel write-hazard finding:** Current changed-file ownership across C2, C3 and C4 is independent, but N2 deliberately extends the parent C3 validation script, and child PR stacks must be reconciled in dependency order. Do not independently amend the same `check_vectors.py` in C3 and N2. Prefer waiting for C3 ownership transfer or a reviewed single change. DO NOT merge or cherry-pick child before reviewing inherited parent diffs and lockfile/license provenance.

**Potential mergeability gate:** On the inspected GitHub snapshots the parent C0 #722 became `mergeable=true`, while #723/#726 reported `mergeable=false` even though their displayed PR patches were disjoint from the parent paths. The field does not establish why a merge is unavailable. Treat reason as **UNKNOWN** until GitHub merge tree/conflict checks, current branch protection and base comparison are inspected; never bypass with force push or manual tree replacement. Current parent is an unfinished **draft** regardless of mergeability.

## Reversible R1 lanes while local actor works

- **R1-D immutable process-restart journal:** branch `experiment/audio-control-r1-recovery-ledger`, `audio-control/control/recoveryledger/**` and a dedicated public 3-OS CI. Separates stored immutable start intent and observed STOP receipt, classifies interrupted playback as unknown. Must not be mistaken for atomic SQLite WAL or a production transactional outbox; current host evidence is *not authenticated*.
- **R1-H trusted host-admission seam:** `experiment/audio-control-r1-host-admission`, `audio-control/control/hostadmission/**` and its own public 3-OS CI. Verifier is injected and test-only. Distinguishes requested/observed effect, STOP-preempts-START, lease/epoch fences, and recovery unknown. No actual OS security or physical audio.
- **R1-R integration review (this branch):** owns only `docs/architecture/AUDIO-CONTROL-STACK-REVIEW-R1.md`; no control-plane or DSP source mutation. Evidence only, no merge.

These lanes are file-disjoint, built from immutable C1 or C0 source snapshots. Their public jobs can execute concurrently, while a local actor proceeds independently on its own branch. No local actor execution should be claimed without an executor ID/receipt. No duplicate R0 branches or second policy.

## Critical safety counterexamples / STOP conditions

1. **Crash then fresh STOP does not stop a remote/device effect:** R0 in-memory reducer resets to `new` and returns stopped without producing host stop. [N1 PR #728](https://github.com/SemperSupra/stable-character-pipeline/pull/728) demonstrates the gap. The R1 journal and admission gate are *partial* negative proof/test harnesses, not the fix for an unsupervised physical device. Mandatory production adaptation: privileged host/device supervisor with independent watchdog and actual stop/lease reconciliation.
2. **An event named `host_stopped` is not host authentication.** Client-origin JSON, local test verifiers and hash-only evidence cannot grant device privilege or verify headphone silence. Keep input auth on OS interface and separate from schema.
3. **FFmpeg effect completion and object custody differ from command acceptance:** existing `scene_audio.v1` is authoritative; a produced WAV lacking a transactional receipt is an orphan/unknown, not automatically a replayed success.
4. **Exactly-once physical media cannot be promised:** at most idempotent admission + verified effect reconciliation with recovery. Sample delivery and physical playback remain time-dependent.
5. **Licensing, rights, privacy, acoustic safety and release:** real user/character voices, identity/medical recordings, hardware playback and signing require owner-controlled venues and acceptance; no public free-runner tests can prove physical calibrated output.
6. **Real-time callback:** never add Go/JSON/network/fsync/logging locks to a time-critical OS audio callback.

## Sequential acceptance plan and hygiene checks

After independent exact-head CI: review source/host threat model → verify actual branch graph and provenance → ensure JSON Schema and Go model version/principal fields agree → prove Aural `QuietSearch` phase behavior unchanged → choose a battle-tested durable/host solution (SQLite WAL and native OS supervisor preferred for qualification) or reject the new layer → only with authority, integrate parent then children on their true dependency edges. Do not merge or force-update refs now. Check branch protection and current PR mergeability each time.

Prior unused branch `experiment/audio-control-r0-offline-adapter` is empty per previous workset and should only be deleted with exact ref verification and an authorized branch deletion interface (not available in this review). The review branch is intentionally kept draft/unmerged.

**Evidence class:** GitHub PR changed-file inventories and previously passing public CI; no source-level full semantic acceptance, hardware tests or paid private runners.
