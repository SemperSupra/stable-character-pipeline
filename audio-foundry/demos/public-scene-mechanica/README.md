# Mechanica public synthetic scene fixture

This is an original, procedural 12-second **PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL** scene made from six separately replayable synthetic textures: machine-room ambience, motor hum, servo sweep, gear ticks, hydraulic hiss, and metal resonance. These are generated tones/noise; they are not recordings or claims of realistic machinery.

Run `bash audio-foundry/demos/public-scene-mechanica/build.sh /tmp/mechanica-scene` with FFmpeg/ffprobe and Python 3 installed. The script refuses to overwrite output. It writes six 48 kHz stereo PCM16 WAV stems, a `scene_audio.v1` manifest with source hashes/events, a 12-second stereo WAV mix, an AAC/M4A preview, and a technical receipt.

The canonical Go `scene_audio.v1` renderer applies the manifest gain, fade, timing and source hashes to create the WAV mix. The receipt validates every stem and mix for codec, sample rate, channels, duration, non-silence, and unclipped peak; public CI prints those per-file values and hashes. It explicitly marks perceptual and real-device acceptance NOT_TESTED. Public CI requires actual FFmpeg execution and fails on missing outputs or skipped checks. No human recordings, private identities, live devices, or external media sources are used.
