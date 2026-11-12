# R014 real MHR jaw-bone alternative (research HOLD)

Actual prior [facial expression factorial PR #445](https://github.com/SemperSupra/stable-character-pipeline/pull/445), public GHA run 43285803998: the provisional MHR `shape_69` jawDrop morph inverted **47 triangles at amplitude .15**, 71 at .50 and 80 at .70. Mouth-corner shapes 77/78 alone showed zero inversions across observed amplitudes. This strongly indicates an isolated jaw geometry/semantic problem, not a failure of every facial control.

This independent MHR native rig workcell tests whether the verified built-in **`c_jaw` skeletal bone** can produce bounded lower-face deformation without those mesh foldovers. It sweeps signed ±0.08/0.16/0.24 rad rotations on the three local axes, with a bone-only lane and a coupled lane using the previously measured low-intensity blink/mouth-corner morphs. Evidence includes jaw bone tip movement, actual surface vertex motion, oriented triangle inversions, collapse, up to 50 suspect face IDs, editable keyed Blender scenes and actual 768px closeup stills. Inputs are original generic licensed MHR v1.0.1 and checksum-pinned Blender on disposable public GHA jobs.

A structurally non-inverting jaw sample is not necessarily correctly directed mandibular opening, dental contact, lip seal, muscle deformation, expressivity, viseme or photoreal skin/eyes/hair. Do not promote until independent physical/visual QA and native/GLB behavior parity.

Source only in draft [private DLE #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138) scope, stacked on original [MHR native #405](https://github.com/SemperSupra/stable-character-pipeline/pull/405). No real-person data or private runner minutes, no merges/releases. R014/R009 product gates remain HOLD. Archive actual native assets, visualization and SHA receipts in the owner’s private R014 Google Drive folder.

Next corrective step if no safe skeletal path exists: anatomically constrained jaw/mouth retopology or pose-corrective sculpt with explicit lip/teeth collision tests, not a fake lower intensity threshold.
