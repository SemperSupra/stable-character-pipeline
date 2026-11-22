# Audio Control R0 C4 — existing scene offline adapter

**Nonproduction synthetic qualification.** Reuses the already-authored Audio Foundry `scene_audio.v1` `Manifest.Plan`, `Manifest.Render`, source SHA-256 custody and actual FFmpeg audio QC from [scene PR #11](https://github.com/SemperSupra/stable-character-pipeline/pull/11). Does not fork codecs, audio samples, or the scene schema. [R0 parallel workset](https://github.com/SemperSupra/stable-character-pipeline/blob/research/audio-capability-control-r0/docs/architecture/AUDIO-CONTROL-PARALLEL-WORKSET.md) defines C4 as a disjoint workcell.

- `Prepare` validates the original scene and its source digests, source path security, public/private class and a safe new absolute WAV output path; records the original source fingerprint.
- `Execute` re-plans and compares all source receipts before invoking the existing FFmpeg renderer; performs no device playback, capture, network or identity processing. The scene renderer already refuses overwrite and verifies format/levels/hash; `VerifyOutput` re-hashes the resulting file.
- **Not exactly once:** a retry after a completed WAV is a refusal, not the original durable success receipt. A crash between file write and receipt persistence is not resolved by this adapter. Adoption requires an owning host durable outbox/replay and explicit conflict handling. This work does **not** bind the Go R0 in-process reducer directly (different source authority/branch), and proves no universal orchestration service.
- Risks: working-directory/output symlink races, FFmpeg process lifecycle, integrity between revalidation and file reads, exhaustion/interruptions; do not interpret this simple experiment as production-grade atomic file transaction.
- Run on a synthetic public host with FFmpeg and ffprobe: `cd audio-foundry && go test -race -count=1 -v ./offlinecontrol && go vet ./offlinecontrol`. Dedicated public CPU workflow `.github/workflows/audio-offline-control-r0.yml`.

No merge to main, real microphone/headphone use, private character voice, user health record, signing, or release authorized.
