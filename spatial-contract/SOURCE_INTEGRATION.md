# Spatial source integration W1 — real WAV custody / ENU sample geometry

Authority: [integration issue #27](https://github.com/SemperSupra/stable-character-pipeline/issues/27) and [Spatial DLE #18](https://github.com/SemperSupra/stable-character-pipeline/issues/18). Branch **stacks on unmerged draft PR #22**, preserves its Go `spatial_audio.v1` source/listener/schema; renderer PR #21 and independent EBU reference PR #25 remain separate; unmerged Csound/MIDI source PR #15 is next source-generator adapter. No source or rights assumptions from other branches. Only \$0 public CPU CI and original synthetic materials.

**Scope implemented in W1 A1–A3**: source fixture generator creates a *real* mono 48k PCM16 WAV containing original 410Hz synthetic sound and an editable Go scene with the **actual** SHA256 of WAV file bytes. A strict read-only Go verifier checks actual SHA and WAV RIFF data, sample count exactly equal to scene timeline, symlinks/file replacement, naming/path escapes, public/private classification and source size, producing a JSON receipt. Re-running verification is read-only. Fixture refuses any preexisting output directory; no overwrite. Existing metadata-only `SyntheticFixture` hash is intentionally NOT a media admission and cannot pass `AdmitSources`. The narrow canonical PCM16 format is intentional; noncanonical WAV, FLAC, MP3 or multichannel sources require a separate rights-audited conversion adapter.

**Coordinates**: world ENU right-handed +X east, +Y north, +Z up in meters. +yaw clockwise from North to East; relative azimuth = wrapped atan2(dx,dy) minus yaw in degrees, elevation = atan2(dz,hypot(dx,dy)), distance in meters. Position interpolates linearly, yaw interpolates along shortest arc, all evaluated at exact 48k integer sample frames (1ms=48 frames). The last key holds. Coincident source/listener gives undefined azimuth and fails; nonzero spread/cardioid fail until a supported renderer is qualified. DSP, Doppler, room response, head pitch/roll are explicitly not implemented.

**Run on a clean checkout from `spatial-contract`:**

- `go test -race -count=1 ./...`
- `go vet ./...`
- `go run ./cmd/spatial-admit fixture /tmp/NEW_AUDIO_DIR` (requires nonexistent output directory)
- `go run ./cmd/spatial-admit verify /tmp/NEW_AUDIO_DIR/scene.json /tmp/NEW_AUDIO_DIR`

**Three audience interface**: human gets source/project JSON, original dry WAV and explicit pose receipt (not a full GUI); operator gets idempotent verification, collision-free source creation and CI failure reasons; developer/agent gets Go `AdmitSources`, `PoseAtFrame`, typed receipts and explicit unmodeled-feature strings. The source design remains editable for all, unlike a flattened WAV-only interface.

**Next W2:** once exact-head public GHA passes, connect these admitted PCM frames/poses into the *pinned native VideoLAN* object renderer, initially for 5.1 and headphone binaural. Source IDs, sample timing, channel order and HRTF rights must survive. Native stereo remains quarantined (first-sample NaN); use only the separately qualified 5.1-to-stereo downmix. Run actual decoded WAV evidence and independent EBU comparison. No upload of private media, merges, release, deploy, Dolby/THX certification, 2.1 bass-management claim or iPhone playback claim.
