# Synthetic gas-medium audible comparison — **research/acoustic proxy only**

Stacked above [draft PR #549](https://github.com/SemperSupra/stable-character-pipeline/pull/549) / [DLE #529](https://github.com/SemperSupra/stable-character-pipeline/issues/529), this original Go 1.23 stdlib-only code generates two **synthetic 1-second, 48 kHz PCM16 mono** vowel-like examples. It is *not* the protected Physical Vocal source, true vocal-fold / tract simulation, a recording of a real person, speech, or a breathable-atmosphere qualification.

Run from `research/physical-medium`:

```sh
go test -race -count=1 ./...
go vet ./...
go run ./cmd/gas-audition -out /tmp/gas-audio-new
```

The requested output directory must not already exist. A SHA-256 receipt is emitted for both WAV files. The **same 150 Hz prescribed harmonic source, tract length, sample count and parameters** are used in both cases. The only changed property entering the educational spectral envelope is speed of sound from the ideal gas mixture oracle. A 1D, uniform, open-ended quarter-wave resonance equation sets odd-mode locations; harmonic gains follow a toy Lorentzian response. Thus the clips should have identical source F0 but slightly changed spectral texture. The modest example change may not be audibly obvious; do not overstate human-detectable differences.

**Independent comparator:** the public source [draft critic PR #548](https://github.com/SemperSupra/stable-character-pipeline/pull/548) at exact commit `5aad9415cabb30f14931494a3a843ac3539aee28` measures both generated WAVs from a separate, read-only checkout in the workflow, without assuming the synthesis report is correct.

The formula is not a human segmented/dynamically articulated vocal tract. Reference validation against Cantera/CoolProp, multi-section waveguide source-filter analysis, perceptual A/B, and direct Physical Vocal engine integration are still required. Only synthetic public-safe work; no personally identifying voice assets, private source, third-party modules, paid compute or cloud secrets. Do not merge/release/deploy until owner approval. Keep exact underlying original PR #549 isolated and draft.
