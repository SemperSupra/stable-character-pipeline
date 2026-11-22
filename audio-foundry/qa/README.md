# R5-Q — independent technical A/B witness (draft)

Owner: [Audio Foundry #9](https://github.com/SemperSupra/stable-character-pipeline/issues/9), [R5 workcell plan](https://github.com/SemperSupra/stable-character-pipeline/issues/9#issuecomment-7079279230).

This is an **independent source-edit-to-render qualification**, not a new player, mixer, music model, final delivery, or live audio controller. It reuses the existing public **two-stem** `editable_audio.v1` Csound sources and `scene_audio.v1` Go scene mixer. Its outputs are entirely original synthetic candidate sounds; no private character voice, microphone, outside recording, downloaded model weights, secrets or production audio devices.

From the repository root, with Go, Csound, FFmpeg/ffprobe and Python 3 available:

```sh
python3 -m unittest discover -s audio-foundry/qa -v
bash audio-foundry/qa/qualify_ab.sh
```

The workflow *actually* builds original and changed MIDI note / mechanical motor sources, renders both sources through Csound, mixes both through the same Go scene render path, examines 48 kHz stereo PCM and records output SHA-256, duration, RMS/peak and A/B signal difference. It deliberately **fails** on identical mixes, silence, full-scale signal, inconsistent length, wrong sample rate and mono. No skipped tests are acceptable. All generated files live in a disposable temporary directory; no media upload or release occurs.

**Evidence ceiling:** a nonzero numerical A/B difference proves only the mix changes after source editing; it does not prove the difference is audible to a person, that a user interface controls it, iPhone/browser operation, sound design quality, actual scene Foley, spatial effects, compliance with broadcast loudness, production privacy or human/device safety. The final Audio Foundry P1 six-stem 10–20s scene and P2 creator UI remain independent prerequisites.

This QA lane edits only `audio-foundry/qa/**` and its dedicated CI workflow. It must remain a separate draft child of the frozen editable-source work, with no automatic merge/release. Preserve first failing logs and exact tested source + PR merge heads in the DLE.
