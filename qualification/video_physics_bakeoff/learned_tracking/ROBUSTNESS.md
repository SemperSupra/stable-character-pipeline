# Second actual pretrained CoTracker3 RDT&E — occlusion and reversal

**Authority:** Visual QA DLE #150. Independent model-robustness **child** of real pretrained-model CPU PASS [#364](https://github.com/SemperSupra/stable-character-pipeline/pull/364), with exact-source SHA and research-license boundaries unchanged. This is an executable research follow-up, not source polish or production acceptance.

## Shared model and disposable runtime

Reuses the exact Meta CoTracker source Git `82e02e8029753ad4ef13cf06be7f4fc5facdda4d`, CoTracker3 checkpoint SHA256 `2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834` (101.9 MB, **CC BY-NC 4.0 research-only**), Python 3.12 CPU PyTorch 2.6.0+cpu, model source, FFmpeg and original-video workflow already accepted in #364.

The same **single disposable** public Ubuntu Actions VM and checkpoint hydration is reused; the model runs actual inference for three original 12-frame H.264 variants with independently defined target paths:

| Variant | Actual original mutation | Measure |
| --- | --- | --- |
| Baseline | 3 px/frame moving checker patch | Visible-frame MAE in pixels |
| Occluded | Opaque wall completely masks moving patch in frames 4–7 | Number of false-visible occlusion frames, missed visible frames, visible-ground-truth error on unoccluded frames |
| Reversed direction | Patch changes from +3 to −3 px/frame after frame 5 | Visible-frame MAE, per-frame errors, late reversal errors |

All variants are encoded to and actually decoded from H.264; model tracking is **real CoTracker3 pretrained inference**, not fake predicted tracks from synthetic ground truth. The independent oracle never promotes the model: results are `MEASURED_NOT_PROMOTED`, with documented limitations. Artifacts include clip/decoded byte SHA256 and actual per-frame predictions, true positions, true visibility and CPU runtime; only original/public-safe receipts are uploaded, never checkpoint binaries.

Ten new offline hostile source/measurement tests cover true visibility vs predicted visibility, reversal trajectories, deterministic original clips, nonfinite predictions and never granting an acceptance PASS when all predicted points become invisible. Combined with nine inherited controls, test suite comprises **19 tests** on the same fresh runner.

## Open scientific gaps

Neither one-point checkerboard motion nor masking establishes natural gait, multi-view actor consistency, human identity or physical credibility. The frame-level occlusion detector is only as good as the model output; independently specified truth prevents model self-scoring. A genuinely synchronized 3D animated scene plus multiple external trackers should be the next motion-evaluation class. Research-only model license prohibits production promotion without independent rights review.

**Status:** native public Actions results/receipts required before any claim of success. All changes stay isolated, draft/unmerged and non-secret. No paid compute, Kaggle quota, protected data or persistent developer/deployment state.
