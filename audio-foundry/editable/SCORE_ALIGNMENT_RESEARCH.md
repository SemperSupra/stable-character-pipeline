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
