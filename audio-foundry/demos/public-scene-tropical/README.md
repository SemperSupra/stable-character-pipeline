# Tropical public synthetic scene fixture

Original procedural 12-second **PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL** scene, six deterministic synthetic stems: wind, chirps, low pulses, insect-like texture, leaf rustle and water texture. Not actual wildlife recordings or species realism.

From the repository root, run `bash audio-foundry/demos/public-scene-tropical/build.sh /tmp/tropical-scene` with Go (per audio-foundry/go.mod), FFmpeg/ffprobe and Python 3. Output must not exist. The existing Go scene_audio.v1 renderer applies the manifest's gains, fades and timing to the six 48 kHz stereo PCM16 WAV stems. The output directory contains the source-hashed manifest, canonical render receipt, WAV mix, AAC/M4A preview and independent technical receipt.

The independent standard-library PCM observer checks every stem and mix's exact frame count, rate/channels, non-silence and sample peak; checks source and output SHA bindings; and exercises silent/full-scale/truncated-duration negative controls. A second ephemeral render changes only the six track gains by -6 dB; measured PCM RMS ratio must match the expected amplitude scaling within 0.02. AAC is format/duration/hash checked, not independently decoded for signal quality.

Events are **metadata only**, not qualified event-driven synthesis. Perceptual, device and production acceptance remain NOT_TESTED. No private media, physical playback or public media publication; CI retains technical receipts in logs, not audio binaries. Downloadable creator deliverables are a separate gated workcell.
