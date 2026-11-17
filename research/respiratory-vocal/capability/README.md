# Respiratory Performance Capabilities — human, assistive, automation and agent parity

Standalone source-only **original Go 1.23 standard library** capability-negotiation layer under [DLE #582](https://github.com/SemperSupra/stable-character-pipeline/issues/582), stacked directly on [draft PR #584](https://github.com/SemperSupra/stable-character-pipeline/pull/584) without modifying its original synthetic WAVs. It is intentionally *independent of sibling* port physics #621 and observer #622.

A single canonical `respiratory.audience_capabilities.v0` document enumerates **all 18** currently declared `behavior.Action` values, with UTF-8 English/German/Thai labels, audience coverage for humans using assistive technology, automation and agents, and source-admitted scenario filenames. Instead of claiming real person acoustics, it derives only two statuses from the **actual committed source fixtures**:

- `synthetic_preview_only`: 15 actions with at least one actual original synthetic Go generator fixture (17 waveform scenarios total). This is **never an authentic nasal/woodwind/voice/balloon model**.
- `typed_contract_only`: sniff, sigh and gasp are represented in state validation but **have no admitted synthetic audio preview yet**. A human/AT/agent application must disable playback and explain the reason; do not silently synthesize an unreviewed substitute.

Explicit per-action machine flags `can_make_physical_human_voice=false`, `can_claim_real_anatomy=false`, `can_claim_breathability_or_medical_safety=false` guard against UI/agent overclaim. They are truthfulness metadata, not healthcare or privacy decisions. Locale strings are static and require independent native German/Thai usability review; no screen-reader or real-browser acceptance has been performed.

Run offline:
```sh
cd research/respiratory-vocal
go test -race -count=1 ./...
go vet ./...
go run ./cmd/respiratory-capabilities
```
No external module, model, voice sample, personal reference or container network requirement. Tests verify all 18 actions, 15 synthetic-vs-3 contract-only split, exact 17 scenario bindings with no duplicates, EN/DE/TH nonempty valid strings, all flags false, unknown action rejection and deterministic JSON. The executable is CLI/JSON only, **not integrated** with earlier novice Voice Workbench #577 or its visual/audio controls. Future adapters must import this typed model rather than maintaining separate GUI/API semantics and add capability-gated unavailability; real iOS VoiceOver/human preference and web HIL remain held.

The original private Physical Vocal source [draft #72](https://github.com/SemperSupra/stable-character-pipeline-private/pull/72) and historical 21 PCM hashes remain immutable; the prior private Actions budget remains held until actual billing. Public source-only pinned 5min Go race/vet CI, no media uploads, no merge, deployment or release.
