# Experimental Kokoro ONNX CPU adapter (public synthetic only)

This optional Python backend demonstrates a **real open-weight neural text-to-speech engine** in the public Audio Foundry, driven by and subordinate to the Go orchestration contract. It does **not** create a selected final character voice or implement speaker cloning. Two original generic English sentences test feminine/masculine voice presets, not demographic classification or personality.

- Engine: thewh1teagle/kokoro-onnx 0.6.1, MIT code (PyPI), CPU only.
- Original Kokoro-82M weights: Apache-2.0 (hexgrad).
- ONNX export: GitHub release `thewh1teagle/kokoro-onnx/model-files-v1.1` (distinct from upstream original PyTorch checkpoint).
- Model `kokoro-v1.0.int8.onnx`, 114119327 bytes, SHA256 `ae315a79b623f244700e4afb9246c46a26066782e049ba174bf3ba433970ee9c`.
- Style vectors `voices-v1.0.bin`, 28214398 bytes, SHA256 `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`.
- Download and independently verify both hashes **before** any untrusted model is loaded. Source URLs and digests were obtained from GitHub's official release assets API on 2026-10-26; not copied from unspecified third-party mirrors.
- Runner installs `kokoro-onnx==0.6.1`, `soundfile==0.13.1` and espeak-ng. The transitive dependency lock/digest still needs a separate reproducible environment build; this is a proof of concept.
- Official voice IDs used: `af_sarah`, `am_adam` with original, non-person-identifying text. Output PCM 16-bit mono 24kHz WAV and machine-readable source/output hashes, duration/RMS/peak.

The public pull-request workflow synthesizes two **original generic, non-identity voice previews** on CPU, then publishes short AAC/M4A copies and their machine receipt as a **seven-day public GitHub Actions QA artifact**. The downloaded model files are never uploaded, and runner model/audio caches are cleaned after upload. The public test clips are *not* selected character voices. No private credentials or human reference data. Any final human character voices, personal models, real-person corpora or selected final products remain **private** on authorized sovereign workers.

These are two engine-provided preset voices, not genuinely created or cloned speaker identities. Human-like and robotic/androgynous styles require explicit later design adapters, speaker identity and postprocessing qualifications. Their audio must be evaluated perceptually by humans; numerical waveform checks only validate basic non-silence/format/levels.

Sources: https://huggingface.co/hexgrad/Kokoro-82M and https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1 and https://pypi.org/project/kokoro-onnx/ .

This branch is research-only, unmerged and not released or deployed.
