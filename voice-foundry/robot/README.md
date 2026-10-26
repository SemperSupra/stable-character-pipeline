# Robot / computer voice style matrix — public qualification

This Go workcell adds **robot timbre and processing** as an independent audio axis to the existing open neural and procedural speech generators. No Audio2Face work. In the 3×3 sample demonstration, acoustic sources intentionally represent **feminine-presenting**, **masculine-presenting**, and **unspecified** output intent. These labels describe our *authored voice specification*, not measured gender perception, and certainly not a listener's sexuality or a speaker's sex. The third source is a non-identity formant/synthesized computer announcement, not a validated androgynous voice.

Effects: (1) computer: filtered and restrained compression, (2) classic-robot: bit-crushing + tremolo + band limiting, (3) social-robot: less aggressive filtering and short reverberant coloration. Because the effects operate on a generic PCM WAV source, neural voice engines can be swapped or compared independently. Fidelity and intent require listening tests, not just valid signals.

## Public workflow

The path-filtered [public GitHub Actions workflow](../../.github/workflows/robot-voice-styles.yml) qualifies all nine combinations using **Kokoro 82M INT8** / **eSpeak NG** source voices on CPU, then FFmpeg transforms to 48-kHz stereo PCM and 128 kb/s AAC/M4A. It uses two exact-hash-verified Kokoro release assets already qualified in draft PR #12. Go unit tests, race tests and vet check the matrix, safety gates, no-overwrite and output formats/levels. A seven-day public Actions artifact contains **only nine generic synthetic AAC previews** and `receipt.json`, never model weights, real-person recordings, secret material, private final selected character voices, or human media corpora. Runner scratch model files are cleaned up.

Workflow will fail rather than silently reclassify a private final voice into a public experiment. Its CLI requires `PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL`; final character voice custody remains in private workset #34. Do not put private source recordings in public Actions. This is a research-only draft, not a release.

## Three audiences

Human: compare a named matrix of nine generic previews side-by-side using native audio players; accessible visual/keyboard waveform player remains pending, and iPhone playback acceptance is still open.
Operator: run `go test -race -count=1 ./...`, `go vet ./...`; use stable labels, receipts, SHA256, codec/length/amplitude checks for admissions and failures.
Agent/developer: `go run ./robot/cmd/robotvoice -sources DIR -out NEW_DIR -provider PROVIDER` over validated source files named `feminine.wav`, `masculine.wav`, `unspecified.wav` (24kHz, mono, 16-bit PCM WAV), obtaining nine M4A+WAV files and a machine-readable JSON receipt with input/output digests and measured acoustic levels.

## Known limitations / next experiment

This demonstrates sample-conditioned DSP, not true voice identity or neural voice *design*. Intermittent clips are deliberately short, and 3x3 covers 3 designer intents, not all genders, cultures, accents or robot personalities. Perceptual ratings, intelligibility, word error rate, automatic playback in a browser, continuous soundtrack mixing, streaming latency, independent post-generation phoneme/acoustic checking and iPhone user acceptance remain unqualified. The robot profiles currently do not prove asexuality or a measured androgynous acoustic voice; they can express **no gender specified** independently from social and affective behavior.

Workcell references [public audio P0 #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9), [Voice Foundry public PR #12](https://github.com/SemperSupra/stable-character-pipeline/pull/12), and private custody #34. No merges, releases or deployments authorized.
