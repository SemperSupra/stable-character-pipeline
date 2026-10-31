# C2/C5 synthetic musical score to choreography clock

This child workcell **reuses** the original public `editable_audio.v1`
source project, its 480-PPQ MIDI and 48 kHz audio source constraints. It does
not introduce a new music editor, DAW, scheduler, CPE ontology or renderer.

```sh
cd audio-foundry/editable
go run ./cmd/scoreclock -capabilities
go run ./cmd/scoreclock -fixture > original-synthetic-plan.json
```

The fixture supplies eight 4/4 bars, two fictional role IDs, one precisely
specified musical tempo-change position and an off-beat choreography event.
The derived second/sample position uses exact rational arithmetic and a
stable content digest; event order permutations replay identically.

**Explicit limitation:** existing source MusicXML/CSound renders constant
`editable_audio.v1` BPM. This prototype's tempo change is a proposed *score
mapping only*: it does NOT alter or independently verify performed audio WAV
samples. No verified historical score transcription, true human gait, real
partner contact, nonlinear tempo warping or generic non-Western meter support.
Changing to those claims requires new source-aware and independently
admitted testing. Three-audience full UI/UX/DX and browser/mobile parity
remain NOT_RUN for this **research-only function**. No merge/release/deploy.


## Actual initial screening correction (2026-10-31)

Original eight-bar source fixture previously extended `Beats=32` without
authoring any notes in bars five through eight. It now contains eight
additional original synthetic notes, including notes in bar eight, without
changing the project's constant 120-BPM renderer. The score *proposal* still
changes to 90 BPM at bar five; **that tempo change is not rendered into the
current source WAV**.

The read model now exposes both exact clocks and their signed difference:
at beat 18 (tick 8160), the proposed score event is at sample 416000 while
the original 120-BPM source clock is at 408000, a delta of **8000 samples**
(1/6 second). At the end of the eight bars (tick 15360) the proposed clock
ends at 896000 samples and original project audio at 768000 samples: delta
**128000 samples (8/3 seconds)**. No downstream consumer may claim
synchronized performed audio on the basis of this candidate map. The
`clock_alignment_status` explicitly reports
`DETERMINISTIC_SOURCE_CLOCK_DIVERGENCE_NOT_RENDERED_AUDIO`; the boolean
`performed_audio_accepted` stays false. A real score→render→PCM
independent alignment experiment is still required.

This is a correction to *evidence legibility*, not native audio-to-dance
qualification, general swing/rubato handling, body motion, browser acceptance
or a release.
