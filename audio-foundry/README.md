# Audio Foundry — synthetic multistem soundtrack fixture

**Scope:** P0 audio-only research and production pipeline, tracked in [public issue #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9).
Audio2Face and facial animation are explicitly deferred. Voice Foundry is a replaceable subcomponent, not the whole product.

This deliberately simple, independently authored demonstration **creates audible PCM WAVs** using installed FFmpeg (for synthesized ambience, music pad, bird-like tone and contact pulses) plus eSpeak or eSpeak NG (for generic human/processed robot speech). The licensed neural TTS, animal SFX, music models and true rig-driven Foley are **NOT qualified by this demonstration**.

## Portable test

Requirements: FFmpeg/ffprobe, espeak-ng (or espeak), Go 1.23+, Python not required.

~~~sh
cd audio-foundry
go test -race -count=1 ./...
go vet ./...
bash demo.sh /tmp/audio-foundry-new
ffprobe -v error -show_entries stream=sample_rate,channels -show_entries format=duration -of json /tmp/audio-foundry-new/full_mix.wav
~~~

Output directory must not exist. Generates:
- Six 48kHz stereo 12s stems: `ambience_wind.wav`, `music_pad.wav`, `fauna_chirps.wav`, `foley_texture.wav`, `human_voice.wav`, `robot_voice.wav`
- Separate dry input voice samples: `human_raw.wav` and `robot_raw.wav`
- Combined `full_mix.wav` and machine-readable `receipt.json` with duration/sample/channel/hash verification.
- iPhone-friendly previews: `full_mix.m4a` (AAC-LC), `full_mix.mp3`, and `full_mix_iphone.mp4` (H.264 + AAC with fast-start). The MP4 is a generic static video wrapper for players that cannot directly preview audio; it is not scene animation.

For iPhone playback, open `full_mix_iphone.mp4` with the Files or Photos player. If chat attachment links do not open, use a durable file host such as an authorized Google Drive upload; the public test workflow deliberately does not publish media or use private credentials.

The current contact and animal tracks are stylized sound fixtures, not biologically/physically valid models. The music is a chordal test pad, not a composed score. Mixer gain/compression only smoke-checks signal flow and is not broadcast-loudness mastering. The generated hash is a reproducibility **observation**, not a cross-machine bitwise determinism guarantee. Actual artistic quality must be independently listened to and judged.

**Public/private:** source and generic synthetic candidate experiments may be public. Selected final human character voice identities, reference media, person-specific adapters and final voice packs must stay PRIVATE. No public final character artifact publication or tokens. Public runner uses self-generated disposable sounds only; uploads no audio.

**Next:** provider-neutral Go scene event/timeline/track schema, original media ingest/license admission, SFX models, ACE-Step music and Qwen3/Chatterbox voices qualification, transparent stem editing and quality oracles. Use established FFmpeg as mix engine rather than growing bespoke DSP until measured need.

This is an isolated draft research surface. No merge, release or deployment approved.
