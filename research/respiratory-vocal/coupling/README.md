# Mechanics-to-audio synthetic source adapter — R055, research only

This independent Go 1.23 stdlib batch is stacked on [draft RC work #599](https://github.com/SemperSupra/stable-character-pipeline/pull/599), hence the existing original **17 synthetic audio scenarios** [#584](https://github.com/SemperSupra/stable-character-pipeline/pull/584) are present. It integrates the physically constrained **prescribed-flow** numerical bookkeeping into the existing original synthetic sound palette through a new versioned optional package. **No original code in `preview`, `physics` or `behavior` is modified.** No real-world lungs, human vocal tracks, protected identity reference, private Physical Vocal original #72, or 21 historic PCM hash are changed.

Each `coupling.Render(behavior.Performance, coupling.Config)` call first executes `physics.Integrate`, refusing impossible source/pressure/airflow/volume states, then scales pulmonary acoustic sources in a *copy* of the original source event using an explicitly user-given reference dissipated energy `E_ref`: `gain_i = min(1, sqrt(E_loss_i/E_ref))`. `E_loss_i=Σ R_j Q_j² Δt` is an SI work quantity from the mathematical RC oracle. **This is only a unitless educational transfer function, NOT physically calibrated acoustic power, speech intensity, laryngeal mechanics, human breath noise, or a statement that doubling airway resistance causes a specific auditory change.** Original non-pulmonary articulatory clicks are **not** scaled by lung-flow energy, preserving no-lung-flow beatbox sound. The adapter refuses invalid finite/range bounds, source classification, flow/clock inconsistency and failed downstream waveform headroom, returning both original source-neutral physics receipts and a fresh source-bound WAV SHA.

Tests across all 17 original synthetic scenarios explicitly verify source input immutability and bit-for-bit unchanged original generator WAVs before/after adaptation, deterministic same-configuration WAV replay, synthetic noise energy response to increased fixed-flow resistance, clipping/headroom bounds, zero-flow silence, preservation of non-pulmonary clicks, negative pressure/reservoir/normalization controls and inward straw sign. These are **algorithmic regression tests** only, not a validated model of respiratory/phonatory dynamics.

Commands from `research/respiratory-vocal`:

```sh
go test -race -count=1 ./...
go vet ./...
go run ./cmd/coupled-performance
```

The CLI emits a **17-case original synthetic physics + audio numeric JSON receipt**, including 17 waveform hashes, without WAV uploads. Public source-only five-minute CI runs Go race/vet, checks energy/no-flow/hash fields and hashes the JSON transcript. No private Actions or model downloads; do not merge/release/deploy automatically.

**Next gates:** independent parameter DoE and perceptual/noise controls, nonlinear pressure-flow/hysteresis, separate time-varying acoustic area/resonance and glottal source, calibrated pneumatic-to-acoustic efficiency from lawful measurements and actual private source adapter/HIL on sovereign resources. No breathing safety or human anatomy claims.
