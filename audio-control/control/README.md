# Audio Capability Control R0 (experimental)

Public synthetic **Go pure reducer** for common audio control lifecycle and idempotence semantics. This does **not** open audio devices, play tones, capture microphones, access a network, save private data or replace any production engine. It belongs to [Audio Foundry #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9); see [R0 research and cross-project contract](../../docs/architecture/AUDIO-CAPABILITY-CONTROL-R0.md).

Run from this directory: `go test -race -count=1 -v ./...` and `go vet ./...`. No third-party dependencies. Public GitHub Actions `.github/workflows/audio-control-r0.yml` runs synthetic proofs on Ubuntu/Windows/macOS standard hosted runners.

### Entrypoint semantics

- `NewMachine(sessionID, targetID)` creates a **process-local reference** state machine with a bounded deduplication ledger.
- `Submit(Command)` accepts the versioned `audio_control.r0` envelope with **host-bound `principal_id`**, session and target IDs; returns immutable `Receipt` and a separate `Dispatch` of *intent* effects. Exact duplicate operation ID/content returns the original Receipt but no new Dispatch. Operation ID collision, target mismatch, stale revision/epoch fail closed. STOP bypasses expected revision and dominates late start acknowledgments.
- `Snapshot()` is read-only and returns current phase/revision/epoch. `Digest(bytes)` hashes an immutable validated plan; this library does **not** validate actual signal plans.
- `ObserveHost(Command)` accepts `HostStarted/HostStopped/HostCompleted/HostFailed` only on a separately admitted **trusted OS adapter observation route**; `Submit` explicitly rejects them. These are never exposed to untrusted HTTP/UI/agent callers. The pure Go API has no authentication. Adapters must authenticate host origin and enforce OS permission, device lease, human physical playback authorization, timeout and actual STOP. An agent-requested start is only an intent pending host approval.
- This prototype has an in-memory 512-operation cap and no durable effect outbox. Overflow rejects new work, rather than forgetting keys. **Never use it for live audio**, because process failure could lose dedupe/effect state and a late host response must be reconciled against actual device state.
- Distinguish `start_pending` (desired) from `active` (host observed) and `stop_pending` from `stopped`. The host must treat all unknown statuses and errors conservatively, explicitly silence its own valid audio buffers, and fence stale epochs.

### Three-audience contract

Human: native accessible UI issues configured/authorized intents and observes actual stop. Automation: synthetic signed-offline plan/execute/verify with typed receipts. Agent: read-only discovery/plan and eligible actions only via host authorization; cannot forge `Host*` events. One versioned envelope; different presentation and rights per audience.

Real admission requires a stable protocol/schema, host effect outbox, actual OS adapter, crash/restart/replay, fuzz/property/formal tests, performance, ACL/lease verification and independent physical device tests. Passing this reference reducer does not authorize merging or deployment into Aural/WineBot/AgentWebCam.

The JSON schema is on parent research PR #722 under `audio-control/contract/audio_control.r0.schema.json`; integrate that exact schema and the isolated Go code together, not as divergent contract copies. In a production adapter, principal identity MUST be set from authenticated local authority, not trusted from a caller-supplied JSON property.
