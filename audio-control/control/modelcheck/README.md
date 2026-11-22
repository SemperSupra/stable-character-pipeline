# Audio Control R2 — bounded exhaustive Go state explorer

This test-only workcell is based on the local actor's **frozen repaired reducer** [PR #735](https://github.com/SemperSupra/stable-character-pipeline/pull/735). It owns only `audio-control/control/modelcheck/**` and a dedicated public CI workflow; the local actor's `reducer.go`, command CLI, host semantics and process journal remain untouched.

The explorer systematically executes all **8^5 = 32,768** five-event sequences over the actual Go `control.Machine`, including configure, request-start, STOP, close, host-start, host-stop, completion and failure. It checks that the untrusted `Submit` path rejects host events, accepted START never fabricates active playback, STOP is not resurrected by delayed START, revision/epoch never decrease, host START after STOP emits corrective stop, and exact replay returns the original receipt with no repeated effect dispatch. Result logs report the set of reached states and STOP/pending traces.

This is **bounded model testing**, not a formal proof over arbitrary process restarts, unbounded concurrent principals, long queues or adversarial host drivers. The system has no audio device; physical STOP, real OS authorization, durable WAL effects, sample deadlines and acoustic output remain unqualified. Existing [C2 fuzz/trace PR #725](https://github.com/SemperSupra/stable-character-pipeline/pull/725) and [N1 crash negatives #728](https://github.com/SemperSupra/stable-character-pipeline/pull/728) remain distinct and should not be rerun solely because this bounded proof exists. Synthetic only, draft, no merge or release.

Reproduce in `audio-control/control`: `go test -race -count=1 -run '^TestBoundedExhaustiveFiveEventTraces$' -v ./modelcheck`.
