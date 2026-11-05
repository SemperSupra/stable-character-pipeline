# Native equine carpus/hock range and continuity falsifier

Authority [Shetland DLE #293](https://github.com/SemperSupra/stable-character-pipeline/issues/293).
Public original synthetic GLB only, no photo subjects, no protected datasets. Current 26-bone rig has **no explicit hind stifle** and front upper/lower junction is only an unvalidated **carpus candidate**. This observer is deliberately a scientific diagnostic; do not claim the model has correct anatomy merely because the Blender export passed.

Read actual 48-frame imported GLB skeletal positions, calculate signed sagittal bend, excursion, snap, out-of-plane motion, segment-length invariance, identify missing stifle, produce JSON first science failure. Provisional engineering guardrails (not veterinary reference intervals) include carpus candidate 115° max, hock candidate 130° max, snap 24°/frame, lateral 5.5cm, 3° minimum motion and no segment stretch >2cm. Their thresholds must be calibrated with qualified horse biomechanics before asserting true species-specific ROM.

Human: per-bone 48f table and failure list. Automation: deterministic unittest and receipt schema. Agent: bounded source pinned diagnostic, never releases or mutates owner source. No merge/release/deploy/CPE, $0 public runner.
