# Public Voice Foundry — synthetic speech proof of concept

This Go standard-library workcell creates **disposable synthetic human speech candidates** using an independently installed `espeak-ng` or `espeak` executable. It generates real PCM WAV audio. It **does not** create a selected/persistent character voice, clone a person, or provide neural TTS. Other backends (Qwen3-TTS, Chatterbox, MOSS, etc.) remain future candidates requiring pinned/versioned/licensed qualification.

## Repeatable local example

~~~sh
cd voice-foundry
go test -race -count=1 ./...
go vet ./...
go run . -engine auto -voice en-us -text 'This is a disposable synthetic voice preview.' -out /tmp/synthetic-candidate.wav
~~~

The target directory must exist; the target WAV must *not* exist. The program validates the WAV header and emits machine-readable JSON with WAV/text SHA256 and `PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL` classification. This is an initial engine wrapper, not an identity-generation or quality guarantee.

## Explicit public/private custody boundary

- **Public approved:** reproducible generator source, clean Go APIs, public synthetic test prompts, non-identity model benchmarks, short-lived generic test WAVs, safe receipts, agent/CLI/human docs.
- **Private required:** final character voice WAVs, identity profiles, real-person speaker references, individual embeddings, chosen voice adaptations/fine-tunes, private prompts, character-specific evaluation and output packs.
- Public CI must never read private data, use private tokens, publish final voice artifacts, or claim confidential custody. A public-generated recording was public-exposed, even if it is later copied to private storage.
- Produce *final* characters on a private/local actor using public source and private reference material; keep immutable private manifests, rights/provenance/evaluation and hashes with final output.
- This public proof runs only one original non-identifying sentence under bounded CPU GitHub Actions, checks WAV and hashes, then deletes it; no WAV artifact upload.

No upstream voice model weights, third-party clips, or vendor binaries are committed. Licenses for external synthesizers/voices and generated output require their own admission. No merge, release, or deployment is approved by this research draft.

Authority: [public audio workset](https://github.com/SemperSupra/stable-character-pipeline/issues/7); private final-product ownership is tracked in the private DLE.
