# Independent modality conflict bakeoff (original synthetic RDT&E)

This workcell makes progress on **real decoded-frame and 3D counterfactual comparisons**, without installing a production suite or copying another workcell's source into this branch. It is a new independent sibling of public root [#356](https://github.com/SemperSupra/stable-character-pipeline/pull/356), under [Visual QA DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150).

## Two independent source judges
- Pinned independent [geometry #360](https://github.com/SemperSupra/stable-character-pipeline/pull/360) at `bcccffbc016b980974fb46397e6eaa6e6f6d0b45`, source-observed hip/knee/ankle 3D joints and approved rest-pole with explicit FAIL/UNKNOWN.
- Pinned independent [temporal pixels #361](https://github.com/SemperSupra/stable-character-pipeline/pull/361) at `8ed8ad31e4438fd2e537dc8903a4b85291e1ab68`, native FFmpeg-decoded 36-frame H.264 images with luma/flicker/cut/black-frame checks. Rights-original synthetic image generator is imported at the same exact commit.
- Each source is fetched into its own disposable path on the standard free public Actions runner, verified against its **exact Git commit**. No runtime dependency on moving branch heads, alternative source code mirrors or private assets.

## Actual six-case hypotheses

| Original case | Expected geometry | Expected video pixels | Expected combined |
| --- | --- | --- | --- |
| Clean | PASS | PASS | PASS |
| Reversed knee in geometry witness | FAIL | PASS | FAIL |
| High-frequency brightness flicker | PASS | FAIL | FAIL |
| One possible scene cut | PASS | UNKNOWN | UNKNOWN |
| Black H.264 video | PASS | FAIL | FAIL |
| Both independent defects | FAIL | FAIL | FAIL |

Combination is fail-dominant; no weighted average can turn an observed violation into PASS. A scientific UNKNOWN remains UNKNOWN in absence of FAIL. Any missing judge or corrupt expected oracle is an execution error, not UNKNOWN.

This is **not** an authenticated synchronized pose↔render comparison. The original synthetic 3D pose witness is independently fabricated relative to the video; there is no reconstruction of anatomy from those pixels, and no bridge between video and actual character model. This experiment **tests failure-dominant arbitration and coverage independence**, not multimodal physical consistency or human gait naturalness.

Six hosted case receipts include full video SHA256, separately hash-serialized pose input, judge Git commit IDs, judge source SHA256, exact verdicts, findings and uncertainties. Nine standard-library negative/control unit tests run before the FFmpeg case matrix. Output is a single JSON receipt with accessible field labels for human, automation and agent review, not a UI replacement.

## Constraints and exit

All dependencies install only on a disposable public GitHub Actions Ubuntu VM; no persistent tools, caches, model weights, public private-person images, Kaggle quota, GitHub Actions secret, agent controller or paid runner. No merge/release/CPE acceptance. Actual status remains **PENDING** until the native source-exact job and JSON artifact are inspected. Next wave should couple real native Blender pose transforms and rendered pixels from the **same synchronized scene**, under independent custody/rights gates.
