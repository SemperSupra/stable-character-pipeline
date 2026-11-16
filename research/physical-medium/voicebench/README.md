# Voice Workbench — novice and automation controls (research only)

Stacked on the original public-safe [continuous-delay PR #574](https://github.com/SemperSupra/stable-character-pipeline/pull/574), under Voice Workbench [DLE #526](https://github.com/SemperSupra/stable-character-pipeline/issues/526), critic [#521](https://github.com/SemperSupra/stable-character-pipeline/issues/521) and atmospheric acoustics [#529](https://github.com/SemperSupra/stable-character-pipeline/issues/529). This is NOT the private Physical Vocal source/engine, human speech, an anatomical model or a public production deployment.

## Run in local research environment

From `research/physical-medium`: `go test -race -count=1 ./... && go vet ./... && go run ./cmd/voicebench`. The UI is **http://127.0.0.1:8765**, only accessible from that same host. The executable refuses other bind addresses, runs Go 1.23 standard library only, makes no persistent recordings, accepts no uploads, and handles no sensitive voice identity data.

The novice UI uses two visible controls: **acoustic tube length (mm)** and **synthetic source frequency (Hz)**, plus a collapsed advanced **interior sound speed (m/s)**. On choosing Preview, a 250 ms deterministic WAV is prepared; the user must press the native audio Play control. There is no autoplay, microphone, automatic reference import, true continuous real-time morphing, synchronized 3D anatomy or scientifically calibrated human speech.

## Audience parity, explicit limits

Human: field labels, descriptions, keyboard-adjustable range inputs, focused controls, native audio, explicit A/B, no autoplay, language dictionary EN/DE/TH, ARIA status and reduced motion CSS. These are structural checks, NOT real iPhone/VoiceOver or browser hardware-in-the-loop evidence.

Automation and agents: typed read-only `GET /api/v1/controls` exposes `voicebench.control_capabilities.v0`, units, default ranges, audience and unsupported-feature declarations. `GET /api/v1/preview?length_mm=170&pitch_hz=160&sound_speed=343.22218086816235` emits 48 kHz PCM16 mono synthetic WAV, SHA256 bound to the response. Deny unknown fields, duplicates, NaN/Inf, bad methods and request bodies. No CORS or mutation API.

Tests include exact replay hash, different WAV for 1 mm and altered gas, peak/headroom, input rejection, control metadata and basic EN/DE/TH/AT-markup structural checks. No claims of perceived differences, source-tract realism, internet authentication, safe respiratory atmospheres, identity matching, or real-time latency.

Next gates: physicalvocal.v0 integration after actual private billing readback, 9-section fractional transport with stable time-varying transitions, independent spectral/octave critic validation, true mobile assistive HIL, human A/B preference calibration, and owner release gate. All private historical 21 WAV hashes remain untouched; keep this PR DRAFT and unmerged.
