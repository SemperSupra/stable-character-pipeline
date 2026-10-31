# C2/C5 synthetic musical score to choreography clock

This child workcell **reuses** the original public `editable_audio.v1`
source project, its 480-PPQ MIDI and 48 kHz audio source constraints. It does
not introduce a new music editor, DAW, scheduler or CPE ontology; a separate
original-only diagnostic PCM renderer is described below.

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

## C5 diagnostic PCM performance witness — new incremental capability

This workcell now also has a **separate original-only, deterministic diagnostic
sound renderer**. It does **not modify or claim to fix** the existing Audio
Foundry Csound project, which remains constant-tempo and independently
qualified under its own contract. The new diagnostic executable is:

```sh
cd audio-foundry/editable
go run ./cmd/scorewitness -out score-evidence
python3 score_tempo_witness_oracle.py score-evidence
```

From the same immutable eight-bar synthetic project it emits original-source
JSON, a MusicXML 4.0 score with 120/90 BPM directions at bars 1/5, a
480-PPQ MIDI file with corresponding tempo meta events, a **real rendered
48-kHz mono PCM16 WAV** of synthetic pitched notes with diagnostic onset
markers, the original clock map and SHA-pinned qualification receipt. Its
sample count is 896000 and it contains **20 actually rendered note onsets**.
The independent stdlib Python oracle reopens bytes, parses XML and MIDI,
detects attack markers in the actual PCM samples, verifies 20 note onsets and
checks sample positions against independently decoded MIDI tempo events
within two samples (MIDI tempo uses integer microseconds/quarter).
The operation refuses to overwrite existing evidence and produces no
protected character or commercial/personal recording.

**Scientific acceptance remains bounded:** `ORIGINAL_SYNTHETIC_WAV_GENERATED_EXTERNAL_ONSET_REVIEW_REQUIRED`.
This is a synthetic onset diagnostic; not a faithful acoustic performer,
source-verified historical musical score, global meter/expressive retiming
engine, physical dance motion, full human/agent UX or an upgrade of the
existing Audio Foundry renderer. The previous `performed_audio_accepted=false`
for its fixed-tempo source clock remains correct and unchanged. Further
real-world/DAW timing qualification is separate and HELD.

## Native Csound external-engine diagnostic qualification

This increment also tests the **real Csound executable** as a separate native
engine rather than taking in-process synthetic WAV generation as its own
ground truth. Run `go run ./cmd/scorewitness -out new-dir` and qualify
`original-synthetic-csound-transport.csd` using Csound's 48-kHz,
one-sample-block original diagnostic voice. The source MIDI, MusicXML,
synthetic Go PCM and Csound WAV come from the same immutable original-only
score/project, but are checked by independent parsing and decoded PCM.

The public $0 native qualification tests 20 expected onset times at 48 kHz,
including the 120→90 BPM transition, independently verifies actual Csound
PCM and saves a separate verdict. Two independent Csound executions from
the same source must generate **byte-identical WAVs**, recorded as two SHA-256
values. Refuse a changed source digest, invalid tempo, unexpected onset,
non-PCM result or changed replay bytes. Native engine diagnostic artifact is
stored in expiring GHA results; retain in controlled Drive only with actual
SHA read-back and explicit source-rights disposition if durable custody is
later required.

**Scientific scope:** Csound diagnostic note/click onset equivalence is NOT
the production Audio Foundry music-voice timing qualification, a human
performance, genuine source musical score, rig animation, native mobile
media playback or release admission. The existing fixed-BPM source audio's
128,000-sample end-of-score mismatch with the *proposed* tempo model
remains explicitly documented, and `performed_audio_accepted=false`
for that original renderer is unchanged.
