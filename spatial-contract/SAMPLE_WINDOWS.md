# Spatial W3b sample-activity gates — first bounded experiment

Authority: [Spatial W3 #39](https://github.com/SemperSupra/stable-character-pipeline/issues/39), [parent #18](https://github.com/SemperSupra/stable-character-pipeline/issues/18). Stacked draft on already verified W3a [PR #44](https://github.com/SemperSupra/stable-character-pipeline/pull/44), with no merge/release/deploy and only original synthetic $0 public-GHA input files.

**Problem:** W3a mixes two same-start one-second sources and applies location only at native 1024-frame block beginnings. Real sound events need independent onset/offset and gaps; per-sample source activity must not be confused with block-start spatial pose updates.

## Added semantics

Two optional, backward-compatible fields for each existing `spatial_audio.v1` emitter:
- `source_start_frame` (default 0)
- `source_stop_frame` (default 0 meaning end of scene)

Both are **absolute 48000-Hz scene sample indices**, with half-open interval [start,stop); they mute unselected samples of the original source file (the source PCM remains timeline-aligned). They **do not offset or seek the source PCM**, implement source looping, change its tempo, or add new listener/head orientation. The scene keeps the authoritative source identity/hash and media files are unchanged. Invalid negative, reversed, equal, beyond-scene and nonnumeric fields fail validation.

The Go dual block plan writes both emitter windows alongside each native pose/gain, each source's stable ID and its exact block start/frame count. Native C++ rejects incomplete/extra columns, inconsistent gate windows, invalid frames, wrong IDs, output collisions, nonfinite samples and unacceptable format/peak. Within each 1024-frame block the C++ adapter applies **source mute gates at each individual sample frame**. The native VideoLAN spatial object *position* remains evaluated at the beginning of the block, not continuously per sample.

## DoE qualification fixture

- Two actual independent public WAVs: 410Hz A and 690Hz B, exact SHA256 admission before plan/render.
- A: continuously active frames 0 through 47999.
- B: enabled at **24×1024 − 1 = 24575**; disabled at **36×1024 + 1 = 36865**. These deliberately straddle native 1024-frame boundaries by one sample.
- Render one actual mixed 5.1 floating-point WAV through pinned VideoLAN `libspatialaudio` source and actual `Renderer`. Independently Go/FFprobe verifies frames, channels, clipping and finite output; Go spectral oracle compares 690Hz energy in before/active/after windows against a fully active B baseline, while checking the unchanged 410Hz A contribution. This tests *coarse audibility* and a real per-frame source gate in the native adapter, **not exact acoustic disappearance at each frame** because HRTF/filter tail and panning introduce ringing/time smearing.
- Retain W3a source-retune spectral proof, byte-identical replay, changed B geometry response, malformed plan, source SHA tampering and output O_EXCL regression tests. Pass only after exact-head CI.

## Three audiences and limits

Humans edit the same source JSON activity fields and sound asset references, not a flattened waveform. Operators run Go fixture/plan, native renderer, Go independent verify and receive source/time-window receipts. Agents/developers can discover the typed emitter start/stop fields, use negative tests and reason-coded refusals. A graphical timeline, visual scrubbing, real DAW session, physical reverberation, headtracking, multiple independently shifted PCM source files and iPhone playback remain unimplemented.

No invented "exact-sample acoustic spatial motion" claim. More than two emitters, arbitrary events, 7.1/binaural dynamic QA, EBU off-axis parity and real music/speech sources remain future gates. Native direct stereo NaN quarantine stays intact.
