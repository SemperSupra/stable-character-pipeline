# Spatial W3b transport offset — independent audio-source timeline semantics

Authority: [Spatial W3 #39](https://github.com/SemperSupra/stable-character-pipeline/issues/39) and the [W3b activity native PASS](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40589268761). This standalone stacked research DRAFT uses only original synthetic 48k WAV and pinned LGPL VideoLAN renderer. No merge/release/deploy, private voices, proprietary Dolby/THX or paid/private runners.

## Canonical event vs source distinction

Previously a W3b emitter with source_start_frame/source_stop_frame controls a half-open **scene-time input activity gate**. Its audio source always uses the same absolute scene-frame file index. This backward-compatible default remains **scene_locked**.

An explicit opt-in `source_transport:"clip_relative"` permits an event start at scene frame 24575 while reading from original dry source frame 0 or 512. The exact mapping is:
- scene_locked: source_index = scene_frame
- clip_relative: source_index = scene_frame - source_start_frame + source_offset_frame
- outside [source_start_frame, source_stop_frame): source input is zero; rendered output may contain acoustic tails

Original source WAV bytes and SHA remain unchanged for transport experiments. The Go source frame oracle checks first/last ±1 boundary samples and strict source size. Unknown mode, bare offset without mode, invalid range, negative seek, collision, tampering or missing source must fail.

**Native compatibility:** the previous supported Go blockplan format is 16 fields. Only explicitly requested clip-relative transport extends the plan to 20 fields, including transport+offset for both stable emitters. Native pinned VideoLAN C++ consumes the optional fields, validates modes/ranges/consistency across all 47 blocks and maps PCM input at each individual frame. Emitter spatial pose still updates only once per 1024-frame block. These are separate clocks and features.

## Genuine native qualification

The public GitHub Actions test builds exact VideoLAN source, creates two independently SHA-admitted original mono PCM files, and renders two actual 6-channel float32 WAVs at 48k with B active [24575,36865): transport offset 0, then transport offset 512. A 410Hz unchanged; B 690Hz unchanged in content and scene motion. Independent Go/FFmpeg full decode checks sample count, channel count, peak and finite values. Go DFT oracle checks predicted 690Hz B phase difference (2 pi × 690 × 512/48000), A 410Hz energy within 5%, B 690Hz energy within 20%; identical or rescaled files must fail. No actual rendered sample is uploaded by default.

This proves bounded, synthetic source-file seek if and only if an exact-head native workflow completes SUCCESS with spectral/original-source proof. It does NOT prove source continuity across arbitrary scene lengths, pitch/stretch, true acoustic silence at boundaries, head tracking, spatial position updates within 1024-frame blocks, subjective surround fidelity or iPhone playback.

## Three audiences and next baton

Creators get readable source-preserving JSON scene, transport and start/stop controls, original WAV. Operators get deterministic no-clobber CLI and structured receipts, bounded public CI and first failure. Developers/agents get Go `Emitter` fields, `contract.SourceFrameAt` reference mapper and strict validation with negative tests. Visual sound-stage GUI and native Ardour session remain unqualified.

After exact-run proof, next READY is W3c independent EBU gain DoE for 0°, ±45°, ±70°, 120°, 180° plus elevation/listener yaw; use matching source and timebase. No direct native stereo use until NaN defect is independently fixed. Existing W3b activity proof remains distinct.
