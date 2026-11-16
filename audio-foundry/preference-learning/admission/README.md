# Public synthetic fixture admission — DRAFT

Original Go 1.23 standard library, source-neutral and fail-closed. Implements only a **second, explicit custody boundary** between reviewed synthetic `audio.intent.v0` documents and public disposable CPU runners. The exact payload SHA-256 must be in an out-of-band reviewed immutable manifest; each reference hash must also be independently approved and classified synthetic. Duplicate top-level JSON keys and malformed/trailing input are denied. Raw `PreferenceEvent` feedback and private voice content are **never** public-runner eligible. Review of the free-text description and reference rights is a prerequisite **outside** this code; a hash proves identity of reviewed bytes, not legal permission or privacy by itself.

Run `go test -race -count=1 ./... && go vet ./...` from this module.

This is not a full JSON Schema validator (the versioned schemas remain in parent draft PR #522). It is not yet wired into the runner, generator or protected source; explicit reviewer admission and separate semantic schema validation are required. No merge, deployment, private data or hosted job inferred.
