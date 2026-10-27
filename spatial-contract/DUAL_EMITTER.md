# Spatial Audio W3a — two real independent emitter sources, $0 public qualification

Authority: [Spatial #18](https://github.com/SemperSupra/stable-character-pipeline/issues/18) and [W3 #39](https://github.com/SemperSupra/stable-character-pipeline/issues/39). This is a stacked DRAFT on [W2 PR #37](https://github.com/SemperSupra/stable-character-pipeline/pull/37) exact tested head `d2b6ab93d239d59ab06e823a703c007b6565a192`, not a merge or deployed service. Original public rights-clean synthetic audio only. No paid/private Github minutes, final person-specific voices, release, Audio2Face, Dolby/THX or HRTF dataset redistribution.

## What W3a actually changes

- **Two distinct, real** mono RIFF PCM16 WAV sources: `robot_a.wav` at 410Hz and `robot_b.wav` at 690Hz, 48k, 1 second. SHA256 calculated from each full real file; hashes differ and are independently validated by existing `AdmitSources` before computing spatial movements.
- One canonical `spatial_audio.v1` source/listener/project manifest with stable emitter IDs `robot_a` and `robot_b`, two separate motion curves crossing left/right, independent gain dB, one listener. No duplicate audio filenames or accidentally shared emitter IDs admitted.
- New Go `spatial-dual fixture NEW_DIR` creates a complete *new* source/project directory without overwriting existing files; `spatial-dual plan SCENE.json AUDIO_DIR NEW_PLAN.tsv` checks public classification and both file hashes and emits stable, time-ordered 1024-sample block instructions for two emitters with gain, azimuth, elevation and distance. It does not falsely call block-rate geometry "sample-by-sample DSP".
- First-party C++ test adapter compiled against exact pinned LGPL VideoLAN `libspatialaudio@d149ed9744fd399b835c6f2920511f8cbcfce5ea`: one native 5.1 renderer with **two object channels/tracks** and two mono signals simultaneously; source A track index 0, B track index 1. Both tracks added before each block's `GetRenderedAudio` and rendered as one six-channel WAV, with inherited output O_EXCL/O_NOFOLLOW no-clobber. Native direct stereo remains **NaN-quarantined**.
- Independent Go `nativeverify` full FFmpeg/FFprobe PCM decode validates 48000 frames, float32/48k, six channels, nonzero/finite/non-clipped audio and output SHA256. Rerender from identical original inputs must produce *byte identical* WAV. Change **only B's** emitter motion while preserving both dry source hashes; new rendered PCM must have a different SHA and remain valid. Red controls: missing frame block, existing output file, corrupted second source hash; additional Go negative tests for duplicate IDs, wrong ordering, private classification, gain/spread and mismatched media.
- Public CI workflows keep all WAVs ephemeral; no upload/download links. iPhone listenability is not yet accepted. No full GUI yet: human edits canonical JSON; operators run idempotent plan/test; agents and developers use Go source contract and machine-readable CI receipts.

## Reproduction

On clean checkout of this branch:

`cd spatial-contract`

`go test -race -count=1 ./...`

`go vet ./...`

`go run ./cmd/spatial-dual fixture /tmp/a-NEW-directory`

`go run ./cmd/spatial-dual plan /tmp/a-NEW-directory/scene.json /tmp/a-NEW-directory /tmp/a-NEW-dual-plan.tsv`

The public workflow [`spatial-dual-scene.yml`](../../.github/workflows/spatial-dual-scene.yml) additionally fetches/builds/qualifies the pinned real C++ library before running the native dual-source audio test. Exact hosted evidence must pass before asserting W3a-qualified output.

## Explicit limitations and next DoE

This is **exactly two** same-duration public mono sources with aligned starts, original test tones and one 5.1 layout. A real scene needs general 2–4 emitters, onset offsets, silent gaps, variable lengths, time-dependent source gains, head orientation, height/7.1, nonzero spread, sound event trigger, multiple HRTFs and a performant shared mixer. True per-sample interpolation, source-distance physics, Doppler, room acoustic and perceptual localization remain unsupported; do not infer them from waveform format. Later W3b/W3c will test block boundary ±1 sample, listener rotation, EBU gain energy oracle at more azimuths, wall-clock/retry budgets and sample-specific source edits. This draft does not invent a native Ardour session.

Preserve no-merge, release, deploy and private-custody boundaries. In DLE record exact SHA, CI PASS/FAIL/first failure and the next READY.
