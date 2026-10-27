# Motion dataset admission and training-data readiness

Research-only source catalog and a deterministic split planner. **Catalog listing is never an authorization to download, copy, train, redistribute or upload data to Kaggle.**

## Authorities and boundaries
- Human motion, interactions, whole-person sources: private R012 [#35](https://github.com/SemperSupra/stable-character-pipeline-private/issues/35); **no private assets** appear in this public workcell.
- Fauna motion/gaits/ecosystem: public [#5](https://github.com/SemperSupra/stable-character-pipeline/issues/5).
- Shared synthetic learner: draft [PR #24](https://github.com/SemperSupra/stable-character-pipeline/pull/24); Kaggle actuation lives exclusively in [Agent Dispatch #638](https://github.com/SemperSupra/agent-dispatch-private/issues/638).
- All third-party source records in `catalog.v1.json` are **CATALOG_ONLY / NOT_ADMITTED**, irrespective of public URLs or nominal licenses.
- Never place restricted human or animal media, identity-specific weights, unadmitted re-targets, confidential datasets, or raw Kaggle credentials in public CI.

## First admissible source roadmap
- Human: use original procedural `motion_learning/synthetic.py` as test data; pursue CMU mocap BVH / ASF-AMC as the first external source after source-terms readback and file-level checks. AMASS/SMPL, HumanML3D, BABEL, Inter-X, Motion-X, KIT-ML and LAFAN1 require distinct provenance, redistribution, and training-rights review; derived versions inherit the original source conditions.
- Fauna: current original procedural quadruped test data first; then inspect Vienna Horse Data Collection kinematic measurements (CC BY-SA 3.0), PFERD C3D/FBX/hSMAL (item-level Dataverse terms), and PAIR-R24M rat 3D interactions (repository lists CC BY 4.0). Animal Kingdom and Animal3D are helpful for semantics/shape but not direct 3D trajectory ground truth.
- 3D pose/motion, 2D tracked video, text labels, inferred 3D pose, and dense mesh deformation remain separate modality classes. Never fabricate measured contact events, identities, anatomical detail or uncertainty from semantic labels.

## Future canonical training sequence contract
One admitted capture family should have immutable source ID + SHA256 + terms receipt; original capture ancestry and recording/session key; individual/pair identity only when present and authorized; species / rig/skeleton identity; meters, seconds, handedness, source coordinate frame and units; original frequency plus resampling transform; root position & orientation; joint hierarchy and 3D positions/rotations; per-channel observed/estimated/synthetic source flags and confidence/unknown masks; contact/support with evidence; behavior/time labels in original language plus multilingual mappings; provenance of annotation/model; recording environment/terrain; immutable transform revision and downstream artifact hashes.

**Split by the underlying recording family and capture session**, not by random frame or overlapping sliding window. Keep multiview videos, re-annotations, transformed mirrors and derivative datasets in the same group. Separate held-out species from within-species held-out performers/animals. Preserve an untouched public-safe synthetic holdout for independent CPU/TPU verification.

Use `prepare_splits.py --records admitted-records.json --output splits.v1.json` with admitted records only. The planner's group hash is reproducible but not stratified and cannot establish population independence by itself. It is a release-gated foundation, not a quality oracle or license grant. Run `python3 -m unittest test_prepare_splits -v` in this directory.

## Training sequence
1. Dry-run with 128 × 48 × 18/17 × 3 synthetic records at 24 FPS from the existing generator, preserving original SHA256 and current 96/32 train/validation claims. A separate 70/15/15 split plan is a new held-out experiment and **must not** be relabeled as existing model validation evidence.
2. Admit a small measured capture subset, verify raw content SHA and rights offline. Convert through a pinned, independent adapter preserving topology and provenance; mask unknown channels.
3. Test frame-rate, units, valid quaternion norm, missing frames, anatomical bone lengths, root trajectories, foot sliding, ground penetration, abrupt jerk, distribution of gaits/actions, and source-leak detection.
4. Run next-pose, variable-horizon autoregression and motion completion baselines before motion diffusion or text-conditioned generation.
5. For animal work use species-specific rigs. Do not treat a horse or a rat as a '17-joint universal quadruped'.
6. Only then package admitted public-safe immutable datasets for Kaggle offline attachment, under approved source-specific namespaces and an Agent Dispatch typed TPU training assignment. Remain $0, no private GHA spend, no automatic promotions.

### Readiness assertions
`SOURCE_CATALOGED` is not `SOURCE_ADMITTED`; `SYNTHETIC_PREPARED` is not `REAL_MOTION_TRAINED`; `CPU_TRAINED` is not `TPU_HARDWARE_PASS`; passing short-horizon MSE is not verified realistic motion.
