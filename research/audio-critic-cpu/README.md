# Deterministic WAV critic — draft, CPU-only research

Source-neutral original Go 1.23 stdlib implementation for synthetic audio in [DLE #521](https://github.com/SemperSupra/stable-character-pipeline/issues/521). Only validates **PCM16 mono RIFF/WAVE** with a 64 MiB input cap. Computes SHA-256, duration, sample rate, signal peak, RMS, near-clipping count, silence, and basic normalized-periodicity estimate/abstention.

Run: `go test -race -count=1 ./... && go vet ./...` and `go run ./cmd/wavcheck -wav /path/to/public-synthetic.wav`. The CLI exits 2 for malformed/unsupported input and 3 for valid but silent or near-clipped WAV, enabling fail-closed CI.

This is an uncalibrated **L0** critic and does not establish actual audio quality, intelligibility, source identity, perceptual preference, speech or human anatomy; future mapping to `audio.critic_receipt.v0` must include an actual pinned tool source SHA, not an invented or self-proclaimed authority. No hosted cloud execution, private samples, source engine modifications or merge implied.
