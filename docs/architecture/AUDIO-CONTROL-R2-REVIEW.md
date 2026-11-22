# Audio Control R2 — independent actor integration and evidence-quality review

Status: **source-only read-only audit, NO merge or release authority**. Owning [Audio Foundry DLE #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9), root `AGENTS.md` and [parallel workset](https://github.com/SemperSupra/stable-character-pipeline/blob/research/audio-capability-control-r0/docs/architecture/AUDIO-CONTROL-PARALLEL-WORKSET.md) remain authoritative.

## R2 and local actor source owners

| Owner | PR | Independent path ownership | Accepted only as |
|---|---|---|---|
| Local actor | [#738 host STOP conformance](https://github.com/SemperSupra/stable-character-pipeline/pull/738) | `audio-control/control/hostadmission/gate.go` + conformance test | Synthetic host STOP latch and failure semantics, **not** real OS authorization |
| Local actor | [#739 required command fields](https://github.com/SemperSupra/stable-character-pipeline/pull/739) | `audio-control/control/cmd/control-probe/**` | JSON CLI parse/required tests, not network auth |
| Local actor | [#740 process restart](https://github.com/SemperSupra/stable-character-pipeline/pull/740) | `audio-control/control/recoveryledger/process_restart_test.go` | Actual test subprocess exit and competing writer proof, not power loss |
| This session | [#743 SQLite outbox interview](https://github.com/SemperSupra/stable-character-pipeline/pull/743) | `audio-control/experiments/sqlite-outbox/**` + dedicated CI | Atomic on-disk SQL intent/outbox rows, not an actual effect consumer |
| This session | [#744 .NET 10 wire interview](https://github.com/SemperSupra/stable-character-pipeline/pull/744) | `audio-control/interop/dotnet-wire/**` + dedicated CI | Existing JSON contract subset/ingress fixture compatibility, not semantic/host equivalence |
| This session | [#745 bounded state exploration](https://github.com/SemperSupra/stable-character-pipeline/pull/745) | `audio-control/control/modelcheck/**` + dedicated CI | 32,768 five-event traces, not unbounded formal model proof |
| This session | [#747 SQLite failure falsifiers](https://github.com/SemperSupra/stable-character-pipeline/pull/747) | **Only new** `test_faults.py` and `FAULT-INJECTION.md` | Detect atomic rollback and emergency STOP persistence dependency |
| This review | R2 stack audit PR | Only `scripts/audio-control-audit/check_r2_graph.sh`, its CI, this review note | Current branch-tree feasibility; does not grant merge |

These roles are complementary. The existing `AuralObservatory.Core` C# DSP and native Aural trial state machine remain separate, authoritative, and untouched. No medical records, human/identity-bearing audio, microphone, sound output, or hardware-dependent tests are used.

## Read-only integration gate

The dedicated `check_r2_graph.sh` runner checks **eight exact current remote parent/child branch pairs** via `git merge-tree --write-tree`, including local-actor host/parser/process tests and all independent R2 siblings/children. Any missing ref or nonclean merge must fail this evidence gate. Clean trees are **necessary but not sufficient**: a logically unsafe union, duplicate method, missing untrusted boundary, or incompatible artifact schema can still compile/merge cleanly.

The critical semantic barrier is **external effect truth**: a committed DB operation or outbox row is never evidence that sound stopped, a host event is real, or a media stream was fully rendered. The real-time callback must remain free of SQLite, Go control locks, network, JSON and persistent writes. STOP requires a privileged native device/host fallback that does not wait for disk locks/full storage.

## Dependency order (no merges authorized here)

1. Accepted C0 `audio_control.r0` schema #722 and original Audio Foundry scene contracts #11; owner reviews current baselines and source licensing.
2. Existing R0 reducer #723 and replay ownership #735, CLI required-field fix #739, bounded model #745; independently admit contract wire #726/#729/#744.
3. R1-D ledger #731 and local actor subprocess #740, R1-H host mock #732 and actor STOP semantics #738. R2 SQLite #743 and its fault child #747 are **alternative/storage interviews**, not new product requirements.
4. Offline scene #727/#730 and real FFmpeg admission #734 (earlier media tests skipped and must be treated as unqualified; #734 executed them).
5. Only then consider conditional **small accepted API** integration in each owning project with native human authorization, durable outbox/effect reconciliation and physical STOP tests.
6. User-approved production merge, signing, publishing and clinical/hardware release remain separate.

**HOLD:** no authentication from JSON alone, no physical sound by an agent, no claim of exactly-once external media side effects, no claim that test-case success means measured headphone SPL or patient efficacy. The pilot must retain human highest-priority preemption and accessible UI/automation/agent projection from the same versioned authority, without granting every audience equal execution privileges.
