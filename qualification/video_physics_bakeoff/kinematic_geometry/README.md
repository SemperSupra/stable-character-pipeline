# Independent gait geometry witness (RDT&E)
This is a CPU-only, standard-library synthetic validation workcell subordinate to Visual QA DLE #150, independent of the repair A/B workcell #358 and root #356. It accepts source-observed **world-space** hip/knee/ankle positions, time, calibrated segment lengths and an independently authorized bend pole. No visual-model inference.

Reports FAIL for observed reversed knee bend, segment length change, invalid segment geometry, excessive flexion and large knee speed spikes. Returns UNKNOWN for physically ambiguous near-straight bending with valid lengths. Missing, nonfinite or unsorted evidence raises INVALID_EVIDENCE and exits 2; errors are not UNKNOWN successes. This does not assert natural gait, dynamic balance, muscles, identity or correctness of supplied 3D points.

Local disposable Linux replay: `cd qualification/video_physics_bakeoff/kinematic_geometry && python3 -m unittest -v` (9 tests PASS, 2026-11-11). Source test initially incorrectly expected UNKNOWN from a straight-knee fixture that **also changed shank length**. First RED retained as a note; repaired fixture holds shank length and yields UNKNOWN. Degenerate nonzero-length requirements are explicit FAIL when observed.

Cloud workflow is an independent path-scoped, source-only `ubuntu-24.04` CPU job. No external packages, model weights, secrets, private assets or persistent host installation; branch stays draft and all product/rights/merge gates remain held.
