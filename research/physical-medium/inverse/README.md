# Reference-to-parameter fitting — synthetic inverse pilot

This is a **source-controlled, CPU-only, bounded research demonstration** of a small closed-loop parameter fit. It depends on the already reviewed original public-safe toy `gasvoice` generator in [draft PR #557](https://github.com/SemperSupra/stable-character-pipeline/pull/557) stacked on [#549](https://github.com/SemperSupra/stable-character-pipeline/pull/549), under [Audio Intent & Critics DLE #521](https://github.com/SemperSupra/stable-character-pipeline/issues/521). This is **NOT** actual private Physical Vocal, human speech, an anatomy reconstruction, an ML reward model, or human preference learning.

## Offline experiment
- Generate a 0.1-second synthetic target reference at source F0=160Hz, sound speed fixed from Earthlike ideal gas, hidden tract length = 0.178m.
- Fit unknown length inside [0.13,0.23]m using 12 objective evaluations per run. Compare reproducible random search against bracketed golden-section local optimization, four independent random seeds, **same evaluation budget**, original generated PCM MSE as a frozen simple critic objective. The golden-section search assumes local unimodality and may fail on other targets.
- Evaluate each fitted length against **withheld source F0=190Hz**. Do not tune using that holdout. Preserve result JSON stdout and source SHA in CI; don't claim perceptual or scientific validity from generator self-consistency.
- Negative controls: NaN/malformed WAV, malformed sample rate, zero budget, invalid method and region bounds.
- **Model identifiability caveat:** without known gas sound speed, acoustic resonance in this toy is proportional to c/L; PR #557 now has a unit test showing different c and L combinations produce bit-identical WAVs. Recovering real anatomy requires more diverse stimuli and independently validated biomechanical priors.

From `research/physical-medium`, run `go test -race -count=1 ./... && go vet ./... && go run ./cmd/inverse-bakeoff`. Only original stdlib Go, no private source, no new dependencies, no public biological data, no Python deployable. Keep this draft PR stacked/unmerged; its CI is source-only and does not perform deployment or any private-hosted work.
