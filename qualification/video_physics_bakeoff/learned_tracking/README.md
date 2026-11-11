# First actual learned tracker inference — CoTracker3 CPU research

**Scope:** public original synthetic H.264 video only. This is independent research under [Visual QA DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), not an owner character asset or product quality gate.

- Upstream source [Meta CoTracker](https://github.com/facebookresearch/co-tracker) exact Git commit `82e02e8029753ad4ef13cf06be7f4fc5facdda4d`.
- Upstream code and [checkpoint](https://huggingface.co/facebook/cotracker3/blob/acc21f9dba34834006a50432bde26b86aa68d794/scaled_offline.pth) **CC BY-NC 4.0**. Model size 101,890,938 bytes; exact blob SHA256 `2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834`. Research-only/noncommercial license acknowledged. Any promotion or commercial use requires separate review. No checkpoint is checked into Git or uploaded as a public artifact.
- Fresh ephemeral Ubuntu public Actions VM installs FFmpeg via APT, Python 3.12 CPU PyTorch `2.6.0` and NumPy `1.26.4` in `runner.temp` venv with caches disabled. Source and weights acquired in `runner.temp` at exact pins. No host caches, organization secrets, private media, paid compute, Kaggle GPU/TPU quota, new services or persistent applications.
- Actual synthetic 12-frame **encoded and independently decoded** H.264 moving checker patch at 128×128/8 fps. Run real pretrained `CoTrackerPredictor` against query frame 0; count visible frames and compare measured track to synthetic ground-truth 3 pixels/frame. Return explicit `inference=EXECUTED` separate from measured `science.gate`: PASS/FAIL/UNKNOWN. Poor learned tracking on artificial imagery is not a tooling failure. Never claim natural human walking, realistic anatomy, identity or physical compliance.
- Tests run before source/model acquisition: nine CPU stdlib controls on fixture determinism, actual codec, missing/hidden tracks, nonfinite values and scientiﬁc oracle gating. No invented model outputs.
- All new source and artifacts remain in isolated research draft PR. Native GitHub Actions run result must be checked before any qualification claim. CPU learned inference may be slow or memory-limited on the standard free runner; evidence of failure is retained as a bounded negative, not retried or converted to a fabricated PASS.
- Next model candidates remain separate (DOVER/PyIQA and GPU/TPU through standalone Kaggle only after credential/quota/provider-native admission). DLE=Durable, Legible, Executable, with accessible text/JSON receipts for human, automation and agent consumers.

Example on preconfigured **disposable** environment after exact source/weight acquisition:

```bash
python3 -m unittest discover -s qualification/video_physics_bakeoff/learned_tracking -p 'test_*.py'
python3 qualification/video_physics_bakeoff/learned_tracking/cotracker_cpu.py \
  --source /tmp/pinned-upstream --checkpoint /tmp/pinned-scaled-offline.pth \
  --out /tmp/tracking-science.json --workdir /tmp/synthetic-video
```
