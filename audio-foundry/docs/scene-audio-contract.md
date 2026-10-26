# scene_audio.v1 — audio-only soundtrack contract (public draft)

Owner P0 is voice, SFX, ambience, score and soundtrack production. Audio2Face is **deferred**. This public additive branch stacks on the existing [Audio Foundry PR #10](https://github.com/SemperSupra/stable-character-pipeline/pull/10); it does not modify PR #10 or the private human-character pipeline.

## Reference flow

Run once per original synthetic scene (requires Go 1.23+, FFmpeg/ffprobe, eSpeak/NG):

~~~bash
bash audio-foundry/demo.sh /tmp/scene-source-new
cd audio-foundry
go run ./cmd/scene init -assets /tmp/scene-source-new > /tmp/scene_audio.json
go run ./cmd/scene plan -assets /tmp/scene-source-new -manifest /tmp/scene_audio.json
go run ./cmd/scene render -assets /tmp/scene-source-new -manifest /tmp/scene_audio.json -out /tmp/scene_v1.wav
~~~

- init creates a manifest from the observed SHA-256 hashes of six independently produced 48kHz/16-bit/stereo WAV source stems. Hashes are **observations**, not cross-version deterministic guarantees.
- plan checks syntax, schema, event and track IDs, event positions, per-track timing and gain/fades, custody, file location, symlinks, and SHA-256 digests without synthesizing.
- render rechecks source hashes, format and adequate source duration, makes an FFmpeg mix with sample-oriented offsets, trims and fades, verifies sample rate/channels/output duration, rejects completely silent, implausibly quiet or clipping results, and writes an exclusive new WAV plus JSON receipt. All source paths are resolved within one admitted asset directory. A manifest is not a source of executable shell commands.
- This is not yet a real 3D spatial propagation, sidechain ducking, perceptual sound-quality, speech intelligibility, or end-user playback acceptance oracle. Neither an exact hash nor acceptable peaks establishes artistic quality.

## Audiences

Human creators: the same JSON manifest drives an accessible future waveform/stem editor; local tool output and generated soundtrack can be inspected in any audio player today.
Operators: plan first, render as a separate reversible/idempotent job, store receipts and first failures in DLE, never overwrite or silently reuse outputs.
Agents/developers: Go package API and CLI with versioned strict JSON, event coordinates, timestamps, explicit model/source-adapter custody and machine-parseable receipts. Error messages go to stderr.

## Public/private boundary

Public source software and independent synthetic candidate voices allowed. Final human voice identities, reference media, selected outputs and private model adapters are PRIVATE. The public CLI **rejects** manifests classified PRIVATE_FINAL_CHARACTER_VOICE unless the executable is explicitly run with -private-workcell on an authorized private worker. That opt-in is not permission to put final assets on public CI; public test workflows never set it.

## Constraints and next work

Input stems in the first version must already be local PCM 16-bit WAV with matching 48k/44.1k rate and mono/stereo channels, and actual duration sufficient for the declared source offset and trim. Model-specific adapters handle conversion separately, not the timeline renderer.
The six supplied tracks are a synthetic fixture only; chirps and contact noises are not species- or physics-accurate and the pad is not a completed musical composition.
Next: native public mechanical/fauna event ingestion, reusable provider interface for neural TTS/music/SFX, source-licensed recording admission, free-tier GPU availability qualification, headless acoustic/spatial solver and human playback acceptance. No merges/releases/deploys until authorized.
