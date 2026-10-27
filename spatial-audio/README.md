# Public Spatial Audio renderer qualification

DLE: [Audio Foundry spatial #18](https://github.com/SemperSupra/stable-character-pipeline/issues/18), parent [Audio Foundry #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9). **Research and test only; no merging, publishing final character audio, deployment, or proprietary Dolby/THX certification.**

This public CPU-only workcell checks a real *third-party spatial audio renderer*, not a bespoke stereopanner and not merely a simulated metadata pipeline. It pins [videolan/libspatialaudio](https://github.com/videolan/libspatialaudio) to commit `d149ed9744fd399b835c6f2920511f8cbcfce5ea`. The runner shallow-fetches that exact source commit, verifies revision + LGPLv2.1-or-later license, compiles source using Meson, exercises upstream native C++ tests, then compiles a small separate first-party moving-source probe.

The probe generates an original 410 Hz mono sine with two horizontal azimuths, runs through the actual `Renderer` object source path, and records six floating-point multichannel WAVs: **2.0, binaural 2-channel, 5.1, 7.1, 5.1.4 and 7.1.4**. Go independently checks stream channels, 48k sample rate, frame count, valid non-clipping numerical output, energy per channel, file existence, format and SHA256. The input and outputs are independently reproducible fixtures within pinned toolchain constraints; numbers can differ across FFmpeg/CPU/compiler revisions.

## Security, rights and qualification limits

- Synthetic non-character test input only; no private voice recordings or final human identity files, GHA no private billing/minutes.
- The bundled MIT HRTF is used only as an upstream source-qualified built-in test component; do not assume all SOFA HRTFs or other spatial sample sets are licensed for redistribution.
- No third-party binary packages or weights are committed; upstream LGPL code is linked dynamically at test time, remains available from its original repository with notices and source.
- The WAV audio stream format (IEEE float32) does **not inherently identify** all channels' standardized ITU/SMPTE layout order. Native `GetSpeakerCount` and receipt validate channel count, **not the mapping or every loudspeaker's acoustic position**. Independent channel-order and panning tests using EBU libear remain a follow-up gate before claiming 5.1/7.1 consumer interchange.
- The signal moves by changing source azimuth once; no continuous Doppler, occlusion, distance attenuation, room simulation, perceptual headphone localization or head tracking is yet verified.
- 2.1 is stereo signal routed to a bass-managed subwoofer; it does not add a discrete LFE by default.
- No claim of spatial scene integration with Go `scene_audio.v1` yet. A provider-independent `spatial_audio.v1` schema and canonical coordinate handedness/frame convention are the next contract step. Avoid silently mixing LFE with redirected bass.
- No live iPhone playback claim: user has experienced attachment/Drive delivery failures, and this research branch does not silently mark that resolved.

## Reproduction

On a clean Ubuntu 24.04 public CPU runner, the workflow `spatial-audio-qualification.yml` builds the pinned upstream library with `-Dlibmysofa=disabled -Dmit_hrtf=enabled`, installs its local test library, runs `meson test`, compiles `renderer_smoke.cpp` with public `pkg-config` metadata, renders six temporary WAVs, and checks the machine-readable receipt using Go stdlib + FFprobe. Every test run deletes source copies and audio after validation. No media artifacts are uploaded.

The test builds upstream source, and GHA logs are authoritative. Do not mark a profile qualified from code compilation alone or treat a spectral-valid WAV as a correct spatial listening experience.

Next: implement explicit-channel order oracle and listener/object transforms; test EBU libear and headphone HRTF source limits; encode a sample through open IAMF or ADM, validate lossiness, and build an accessible creator audition interface over the common contract. The native Ardour session issue [#16](https://github.com/SemperSupra/stable-character-pipeline/issues/16) remains separate. 
