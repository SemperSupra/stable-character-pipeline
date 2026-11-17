# R067 — independent WAV integrity and acoustic signal hard gates

**Authority:** Public [Audio Foundry #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9), [Voice Foundry #7](https://github.com/SemperSupra/stable-character-pipeline/issues/7); private voice identities [#34](https://github.com/SemperSupra/stable-character-pipeline-private/issues/34), existing critic proposal [public #521](https://github.com/SemperSupra/stable-character-pipeline/issues/521) remains **PROPOSAL/NOT OWNER ACCEPTED**. Canonical Way of Working v0.0.4, DLE = Durable, Legible, Executable.

[R063 #607](https://github.com/SemperSupra/stable-character-pipeline/pull/607) actual Whisper-tiny recognized original synthetic speech but hallucinated `you` from perfect digital silence. [R064 #609](https://github.com/SemperSupra/stable-character-pipeline/pull/609) achieved a narrow success by applying a zero-energy veto on that exact silence. **Any nonzero signal is NOT proof of speech.** R067 independently tests signal provenance before introducing more speech model reasoning.

## Independent source-original adversarial matrix

| Fixture | Sound / corruption class | Expected typed result |
|---|---|---|
| silence | all-zero PCM | `DIGITAL_SILENCE` |
| tone | generated 440-Hz sinusoid | `AUDIO_PRESENT_UNCLASSIFIED` (NOT speech) |
| breath-like-noise | deterministic seeded wideband noise, **not a biological respiration model** | `AUDIO_PRESENT_UNCLASSIFIED` (NOT speech) |
| clipped | alternating full-scale PCM | `CLIPPED_REJECT` (positive evidence of source clipping) |
| truncated | source WAV missing 19 bytes but header still advertises full payload | nonzero exit, `UNKNOWN` with typed invalid-format reason |

Five independently scheduled public 4-min GHA jobs, each actually writes a WAV, **reads it back from bytes**, verifies RIFF/WAVE PCM 16 kHz mono 16-bit, checks lengths, hashes input, computes RMS/peak/sign changes/clipped samples, and applies separate strict-negative rules. Offline stdlib Go 1.23 race/vet. No third-party sources, private character voice, model checkpoint, cloud inference bill, private Actions minutes, API secrets or binary audio artifact. Only receipt text and first RED retained 3 days.

**Caveats:** Fixed 44-byte PCM WAV header only, not general WAV/RF64/chunk parser; a richer importer must normalize alternative layouts separately. Full-scale detected clipping need not establish historical source distortion or actual signal peak in all mastering cases. Noise/tone are **sound present**, not speech/music/whistling/breathing evidence. Zero-energy digital silence is narrower than quiet speech/room tone. This component does not qualify VAD, ASR, vocal-tract physics, respiratory mode, multilingual EN/DE/TH audio, perceptual sound quality, audio identity or film mix. Real audio requires protected source custody, independent acoustic analyses and human evaluation.

Code: `research/r067-audio-hardgates`; CI: [R067 workflow](../../.github/workflows/r067-audio-hardgates.yml). At creation runner evidence **NOT YET OBSERVED**; source SHA, job IDs, first failure, individual verdicts and pending expansions must be crossfed to existing audio #9 and R009 #23. No merge, release or product acceptance.
