# Audio control R1 — host-admission adapter test double

**A contract test, NOT host authentication and NOT a device driver.** The source isolates the request path from local-host observations using a caller-supplied `Verifier` interface. The current fake verifier in tests represents a hypothetical OS user-gesture/lease authority. It does not implement permissions, network identity, OS authentication, cryptographic signatures, microphone capture, playback, Bluetooth or headphone STOP.

`RequestStart` can emit a *host_start intent* only when the injected verifier admits a human/selected device; `Observe` accepts only matching session/target/device/lease/epoch and positive verifier proof; `Stop` emits stop intents and retains `stop_pending` until verified host response. `RecoverUnknown` requires a separately verified durable binding—**not** merely a JSON claim—to issue STOP for an interrupted host. A host with no trustworthy binding returns `discover_then_stop`, explicitly not `stopped`.

Run `go test -race -count=1 ./hostadmission` from `audio-control/control`. Public Ubuntu/Windows/macOS CI owns only this directory/workflow. Actual OS integration and physical acoustic permission/verification remain outside this experiment. Aural-specific QuietSearch subjective trial phases stay Aural-owned; Go need not be embedded into Android merely to share control vocabulary.

Candidate only under Audio Foundry [#9](https://github.com/SemperSupra/stable-character-pipeline/issues/9) and its parallel DLE. No production audio, device access, new repository or PR merge authorized.
