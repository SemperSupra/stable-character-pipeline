# Tropical public synthetic scene fixture

This is an original, procedural 12-second **PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL** scene. It uses six independent deterministic texture stems: wind, synthetic chirps, synthetic low pulses, insect-like texture, leaf rustle and water texture. They are deliberately not claims of recorded tropical wildlife or species realism.

Run `bash audio-foundry/demos/public-scene-tropical/build.sh /tmp/tropical-scene` with FFmpeg/ffprobe and Python 3 installed. The script refuses to overwrite output. It writes six 48 kHz stereo PCM16 WAV stems, a `scene_audio.v1` manifest with source hashes/events, a 12-second stereo WAV mix, an AAC/M4A preview and a technical receipt with hashes, codec/rate/channel/duration and mix mean/peak levels. It verifies every output using ffprobe and rejects silent or clipped mix levels.

The receipt explicitly marks perceptual and real-device acceptance NOT_TESTED. Public CI requires actual FFmpeg and fails on any skipped test. No human recordings, private identities or live devices are used.
