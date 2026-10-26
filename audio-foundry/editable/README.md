# Audio Foundry editable-source qualification v1

**Approved objective:** preserve sound *sources* that humans, operators and agents can change, not merely postprocessed WAV/M4A. Audio2Face deferred. Public software and original generic synthetic fixtures only. Final human character voices, identity embeddings, trained voice adaptations and final private mixes never enter public Actions.

## Implemented first vertical slice

The `authorctl` CLI (Go 1.23 standard library) manages an immutable/reversible canonical JSON project (`editable_audio.v1`) with a 120 BPM melodic line and a synthetic motor frequency sweep. It exports **independent, original editable assets**:

- `project.json`: original authoritative parameters, MIDI pitch/tick/velocity and procedural motor sweep, all with a declared public-only custody class.
- `melody.mid`: valid type-0, one-track, monophonic 480 PPQ MIDI containing onset, duration, velocity, and tempo; **strict roundtrip import** is implemented. Supports source music note edits by MIDI-capable creators and by agent/CLI.
- `melody.musicxml`: MuseScore-readable score notation for the quantized subset (integer 4/4 bars, no ties, chords, tuplets, multivoice or playback-expression support); not a complete MuseScore-native project.
- `mechanical_motor.csd`: editable Csound procedural motor with a frequency sweep and gain.
- `musical_theme.csd`: original synthetic Csound oscillator score; its notes are defined in the canonical project.
- Rendered `mechanical_motor.wav`, `musical_theme.wav`: independent 48 kHz, stereo 16-bit PCM stems.
- Render `scene_audio.json`: **scene_audio.v1** handoff usable directly with the existing Audio Foundry Go scene/mix renderer, with stem SHA256 hashes.
- `receipt.json`: input/output metadata and explicit `native_ardour_session_exported: false` — do not conflate synchronized WAV stems with a native Ardour session or a fully reversible DAW project.

### Human user path

A human can edit notes in a MIDI-capable DAW such as Ardour or a score editor exporting our restricted MIDI subset, then use `import-midi` to bring them back into the canonical project. MuseScore can use MusicXML as a score-editing **export**; a MusicXML round-trip importer is not yet implemented. A creator can edit the procedural parameters through the project JSON; the Csound `.csd` files are source-like but **any direct .csd hand edits will cause a fail-closed hash/recipe mismatch at render** until adopted into the canonical project. Aligned WAVs are ready to import as separate Ardour tracks. Actual creation/reopening/editing of `.ardour` session, LV2 parameter mapping and OSC/Lua API parity remain unverified/not implemented.

### Operator / agent path

```sh
cd audio-foundry/editable
go test -race -count=1 ./...
go vet ./...
go run ./cmd/authorctl init -out /tmp/source.json
go run ./cmd/authorctl export -in /tmp/source.json -out /tmp/source-bundle
go run ./cmd/authorctl import-midi -in /tmp/source.json -midi /tmp/source-bundle/melody.mid -out /tmp/imported.json
go run ./cmd/authorctl edit -in /tmp/source.json -out /tmp/revised.json -field 'note[0].pitch' -value 62
go run ./cmd/authorctl export -in /tmp/revised.json -out /tmp/revised-bundle
go run ./cmd/authorctl render -bundle /tmp/revised-bundle -out /tmp/revised-stems
cd ..
go run ./cmd/scene render -assets /tmp/revised-stems -manifest /tmp/revised-stems/scene_audio.json -out /tmp/revised-mix.wav
```

Every output path must not already exist. No global state, downloads, network, secrets, private repo minutes, or TrueNAS/CUDA dependency. `render` needs Csound, ffprobe and the parent scene mixer needs FFmpeg. Public Actions runs the complete lifecycle on Ubuntu using free CPU resources.

## Interchange policy / honest limitations

Canonical JSON is the source of truth for v1; revisions create new files and never overwrite. Reverse edits can reproduce original JSON and MIDI bytes; stem rendering depends on pinned **system Csound and FFmpeg builds**, and sample digests provide observations, not universal cross-environment bitwise proof. MIDI import handles only a strict monophonic type-0 subset and rejects nontrivial commercial DAW exports instead of losing notes silently. No material-dependent 3D acoustic model, real vehicle samples, studio-quality orchestra, natural voice generation, native Ardour session automation, or perceptually tested audio is claimed.

Next qualified steps: import full MIDI/tempo/automation interop; actual Ardour session round-trip using supported Lua/OSC APIs in a disposable GUI host; Csound editable parameter-source reconciliation and source-control diffs; plugdata/Faust; full MusicXML import; creator accessibility/perceptual QA; model- and source-licensed sound library admission. Keep UI, operator lifecycle and agent semantics aligned. Owner has **not authorized any merge/release/deployment**.