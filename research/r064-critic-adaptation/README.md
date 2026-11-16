# R064 — hypothesis-driven critic adaptation after observed R063 REDs

Stacked solely on [R063 original synthetic critic interview #607](https://github.com/SemperSupra/stable-character-pipeline/pull/607) at exact tested source commit `c5767def664dcf8d4eccbeadc070da93d5cdca68`; inherit fixed model/data cards, public-scoped producer and pinned original frame/audio fixtures without modification. Owning existing DLE: public visual #150, audio #9 and private R033 #168. DLE = Durable, Legible, Executable.

Two **independent** public-CPU source-only workcells, neither assumes upstream model acceptance:

1. **Video challenger:** pin `HuggingFaceTB/SmolVLM2-500M-Video-Instruct@5761ea844d66ecc658ae4fa88d0ba22b151f4131` (publisher declares Apache-2.0); replay exact original R063 left/right two-frame H.264 decode. Falsifier is both responses saying LEFT. Change one factor: candidate model size+weights, not prompt/data/evaluator/source.
2. **Whisper + energy veto:** replay exact original pinned multilingual Whisper-tiny on the *same* espeak “move the square left” and digital silence. Preserve the raw hallucination, which **failed R063** (silence -> “you”). Combine with independently computed PCM RMS: exact zero-energy digital silence returns NO_SPEECH without trusting its ASR output. Low-energy nonzero input => ABSTAIN, not invented silence certainty. This is a very narrow rule, not a qualified general speech/music/whistling or noisy-respiration VAD.

The model call happens on source-original fixtures, not protected private voice. Output JSON records original raw model answers separately from composite decision. No prompt tuning on heldout outcomes, no private uploads, no paid services, no privileged Actions token, no deployment or user acceptance.

### Qualification ladder (no promotion)
- **P0** Reproduce and preserve R063 failure with exact source and model hash.
- **P1** Run actual revised candidate and compare same predeclared positive/negative fixtures.
- **P2** Freeze held-out nuisance factors: camera inversion, occlusion, cut/freeze, background/lighting, multiple frames, noisy silence/music/quiet speech, EN/DE/TH and physiological non-speech.
- **P3** Quantify false positives, false negatives, abstention rate, CPU/VRAM/time, confidence and independent numerical witnesses; run multi-seed and model-disjoint review.
- **P4** Owner may admit a specific candidate as an auxiliary critic, never replace real geometry/acoustic hard oracles with VLM scores.

Run `research/r064-critic-adaptation/run.py --lane video-500m|audio-guard --out /tmp/r064` with dependencies from [R064 workflow](../../.github/workflows/r064-critic-adaptation.yml). Each public GHA job is independently bounded to 20 minutes; uploads only raw *text* logs and JSON receipts with three-day retention. Status at branch authoring **NOT_YET_OBSERVED**; CI must be inspected before any PASS claim.

**MCP/remote**: This workcell intentionally remains an offline, GitHub-observable tester. No unauthenticated `trycloudflare.com` ingress or unrestricted inference endpoint is created. Stable authenticated remote MCP is a separate access/authorization question, not an experiment prerequisite.
