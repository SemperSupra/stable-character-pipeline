# Original synthetic equine parameter-fitting proof

**Purpose:** Exercise an actual 26-joint Blender rig, an elementary bounded one-dimensional numerical search, and an independent Go decoded-image measurement service on **two orthographic cameras and two motion frames**. This is a reproducible source-original validation of the inverse-rendering mechanism. It is **not** fitted to external photographs or real animal motion.

The immutable source-original Shetland #294 is pinned to `1f2febbd28d508d1c3d9f2a644f861d634f65a9d`. This workcell stacks on frozen [#301](https://github.com/SemperSupra/stable-character-pipeline/pull/301) for the Go silhouette measurement service; it adds no changes to source owner #294 or its ancestor #300. All public runner work uses original synthetic bytes, pinned source, disposable official Blender 4.5.15, no private runners or credentials.

## Experiment
The native Blender script loads a genuine source-generated 26-bone pony in editable .blend, sets a source rest/reference neck Z angle, and creates a deliberate +0.6-radian defect. The candidate family tests angle offsets -0.6, 0, +0.6 radians. For each of frames 12 and 24 and for each of the side and oblique cameras, it writes source-reproducible .blend and raster PNG files for the reference, baseline and three candidates. Every image and scene file is SHA256-bound in an individual manifest. The 12 manifests are independently assessed by the unchanged Go decoder/IoU algorithm from #301, with a separate Python reducer checking all camera/frame/candidate combinations.

Crucial scientific note: the reference is **the original model's own rendered state**, therefore the zero-angle result is a known expected answer. This validates parameter fitting and the multi-view measurement interface, not subject identity, occlusion inference, actual photographic camera calibration, anatomical shape, human/animal realism, contact physics or generalization to genuine unknown target data. The camera labels are declared rather than independently authenticated. A deliberately unchanged or incorrect geometry can still appear excellent from selected angles.

## Invariants and fail-closed
- Strict source commit and exact SHA256 binary identity for source .blend, each perturbed/candidate .blend and all PNGs.
- Declared camera/view and animation frame must match a complete two-camera × two-frame × three-candidate matrix.
- A candidate cannot be declared acceptable unless all 12 independent pixel receipts are present, geometrically consistent in reference SHA, with source/rig/threshold and scientific caveats intact.
- Invalid/missing/duplicate/misassociated receipts, malformed pixels, or absent improvement must fail.
- Reject mistaken claims that self-renders are real photographic observations.
- Produce one `ENGINEERING_MULTI_VIEW_FIT_PASS_SCIENCE_UNKNOWN` conclusion at most, not owner acceptance.

The workcell is **not yet wired to a live LLM reasoning actor**. A separate deterministic source-neutral parameter proposal policy is developed in its own independent workcell; joining them must validate angle, joint/axis, evidence/camera/reference and immutable source state before any parameter adapter is admitted.

## Three audiences and custody
A human reads contact sheets/PNG/candidate matrix and concise science label. CLI automation consumes exact JSON receipts. An actor consumes the same typed observations and may propose a bounded candidate, never publish or merge a model. Store implementation, tests and evidence metadata in Git/DLE; large .blend/PNG archives belong in controlled owner Drive only after whole-byte SHA verification. Public Actions artifacts expire and are **not** a durable product store.

R009 human/Naomi/Alison sources, local Shetland v1 uploads, protected runner data, main merge, release/deploy/CPE gates, anatomical/identity truth remain separately held. Preserve first failures, never declare a hypothetical actor optimization or authoritative model acceptance from this demonstration.
