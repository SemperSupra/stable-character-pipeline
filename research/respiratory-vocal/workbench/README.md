# Respiratory–Vocal Workbench — source-gated novice/AT/agent localhost research

This independent public-safe Go 1.23 standard-library batch is stacked on [draft canonical catalog #628](https://github.com/SemperSupra/stable-character-pipeline/pull/628), so the typed catalog and original 17 WAV fixtures are present. This is **the first executable bridge between the respiratory-vocal canonical source catalog and a human/assistive/automation/agent interface**. It does not claim to merge into the earlier separate [novice Voice Workbench #577](https://github.com/SemperSupra/stable-character-pipeline/pull/577), or integrate the actual private Physical Vocal source. No human breathing recordings, protected character identity, third-party audio, non-public source or model weights are used.

## Run the local read-only interface

```sh
cd research/respiratory-vocal
go test -race -count=1 ./...
go vet ./...
go run ./cmd/respiratory-workbench
```

Open `http://127.0.0.1:8766` on **the same host**. The executable refuses nonloopback listen addresses. No public network deployment, authentication, microphone, automatic audio playback, file upload, remote scripts, database or persistent user data are implemented. Use of this toy localhost HTTP service outside loopback is **not security-admitted**. Server has capped read/write/header timeouts and headers; it is NOT an audited internet service.

One source of truth: `GET /api/v1/capabilities` returns the source-bound `respiratory.audience_capabilities.v0` for all **18 actions** with EN/DE/TH labels and declared `synthetic_preview_only` vs `typed_contract_only` classification. `GET /api/v1/preview?action=quiet_breath&scenario=nasal_quiet` returns the actual original Go `preview.Render` PCM16 WAV bytes with verified `X-Audio-SHA256`, action and scenario binding, without duplicating the synthesizer. If an agent or human requests sniff/sigh/gasp, the API always emits typed HTTP **409 `contract_only_no_audio`**, never invents missing sound; an unrelated action/scenario pairing is HTTP 422. Unknown/duplicated fields, other methods, upload bodies and nonlocal origin are refused.

The web page consumes only the same `/api/v1/capabilities` source contract to populate actions/scenarios. It provides keyboard-native selects, focus, ARIA status, English/German/Thai strings, reduced motion and voluntary native audio controls; contract-only options disable preview. The structural/HTTP tests and native public HTTP smoke tests do **not** establish actual Chrome/Safari/iOS VoiceOver/screen-reader interaction, translation quality, audible perception, realistic physiology, musical instrument behavior, or live vocal-fold/nasal physical response. Every page and API response declares synthetic-only limits.

## Provenance and test gates

Clean GitHub public Actions with read-only pinned Node24 checkout and no credentials; Go offline stdlib race/vet and source fixtures. Handler tests cover every original 17-case WAV against exact independent `preview.Render` byte equality, deterministic SHA, 3 contract-only errors even when clients attempt to force someone else's scenario, wrong action/scenario, duplicates, unknown params, nonfinite/hostile request patterns, foreign origin, POST/upload and structural EN/DE/TH/ARIA page. An actual localhost server is built and accessed through Python stdlib in disposable CI; no file artifacts uploaded. No private GHA billed usage. All changes additive to this PR.

**Next**: actual browser graphical and iOS AT HIL, local-vs-remote threat modeling, source capability-disabled states and natural-language/audio prompt consent, merging this source-bound novice mode with existing separate #577, source-bound physiological/physical-vocal adapter and original 21 private historic waveform SHA. Draft only; owner merge/deploy gates held.
