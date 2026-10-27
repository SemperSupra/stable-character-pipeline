# R3 W02 — Video framing design of experiments (research candidate)

Owner: public R3 DLE https://github.com/SemperSupra/stable-character-pipeline/issues/43. This workcell is stacked on the successful parent R3 duration-selected Go exporter and independent software glTF verifier. No changes to R1/R2 source, receipts, camera evidence, model weights, or prior success classification.

## Observation
The initial longest 11-frame interval uses NASA source seconds 24–34, where the subject occupies little of the image frame. Another uninterrupted 10-frame detected interval, source seconds 13–22, has substantially larger visible body coverage. A long segment is not necessarily a usable animation preview. The initial GLB, all missing-frame masks, and pass receipt remain immutable comparison evidence.

## Hypothesis and falsifiers
A separately named coverage selector, using only original normalized 2D pose observations:
- enumerate contiguous sequences of 33-landmark frames, never fill missing time;
- require minimum 5 frames for a candidate;
- discard joints with visibility below 0.5 or outside normalized 0–1 image;
- per frame, calculate the bounding-box image area of eligible joints; take sequence median;
- choose largest median visible area, breaking ties by longer duration; preserve source clocks and unmodified landmarks;
- emit an explicit frame_selection_method of coverage and compare against the original duration method.

This is a visual framing and observability heuristic, NOT an anatomical accuracy, same-person identity, true body geometry, camera calibration, motion realism or skin-weight quality score. Do not cherry-pick frames from missing intervals. Algorithm and decisions are deterministic and source-inspectable.

Expected result: editable GLB, independent software GLB skin/animation evaluation, and iPhone H264 preview from the pinned NASA R2 artifact on standard $0 public GHA. Separate draft PR and exact-head native run; two explicit negative tests confirm duration policy remains unchanged and invisible landmarks do not improve the framing score. No merge, release, deployment, CPE promotion, private inputs or GPU/paid runners. Native Blender deformation remains independent and HELD after package-mirror timeout.
