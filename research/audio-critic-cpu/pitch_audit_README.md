# Pitch-octave ambiguity diagnostic — source-neutral, draft

Extends [original independent WAV critic draft PR #548](https://github.com/SemperSupra/stable-character-pipeline/pull/548), under [Audio DLE #521](https://github.com/SemperSupra/stable-character-pipeline/issues/521). New `AuditPitchWAV` examines bounded PCM16 mono WAVs using local normalized autocorrelation minima **and** source-independent coherent spectral support at each candidate. It may select a synthetic pure- or multi-harmonic dominant fundamental when evidence exists; it must **abstain** for ambiguous or missing-fundamental cases. `PitchAudit.Status` is a categorical diagnostic, **not** calibrated confidence, probability, definitive fundamental, anatomy or identity.

This explicitly addresses private source-only diagnostic (human commanded160Hz vs original independent autocorrelation80Hz; avian commanded700Hz vs independent~348Hz, mechanical120 vs120). These commands are **not** an independent verified physical F0, and the code is NOT yet tested against real private-engine PCM because private GHA billing readback is held. Synthetic-only public/free CI cannot justify a claim of resolving true source pitch.

Run `go test -race -count=1 ./... && go vet ./...` from `research/audio-critic-cpu`. No new Go runtime dependencies or waveform publication. Negative fixtures include silence, nonperiodic noise, invalid WAV, and a two-harmonic missing-fundamental signal.

Acceptance requires source-specific independent spectral/harmonic benchmark with false octave rates and abstention calibration, held-out devices and languages, and review of computational cost. Original `Measure` API/PCM historic hashes unchanged. No merge/deployment/release.
