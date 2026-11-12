# R014 independent pelvis-reach correction on true MHR skinned human

Research-only draft, stacked on [world-unit corrected PR #457](https://github.com/SemperSupra/stable-character-pipeline/pull/457). The original Go 169-frame world ankle targets and exact source digest are retained. The MHR public v1.0.1 native skin, 126-bone rig and native source ankle/hip positions are unchanged; no protected identities.

## New quantitative evidence motivating this test

The actual native-footbone IK full-gait source #457 has zero sampled skin inversions; its MHR FBX armature scale is 0.01 and the previous 27.98 rig-local-unit skin excursion is truly 0.2798 Blender world units. Right ankle exceeds the nominal hip-to-ankle two-segment reach by up to 0.10483 world units in 91 of 169 frames, explaining right ankle residual 0.10483 units. The left leg similarly exceeds nominal reach by 0.03312 units across 90 frames. This is a **geometric reach constraint**, not full human biomechanical acceptance.

## Actual corrective action

For every frame, keep each Go world-space foot target fixed. With original rig object root translation+heading, compute both native MHR hip-to-target distances using source anatomical hip/head landmarks and verified hip→knee and knee→ankle joint spans, **not** the imported lower-leg display tail. Solve the minimum root/pelvis vertical lowering needed to make both feet nominally reachable with 0.012 units of knee flexion margin; anticipate via a centered 13-frame maximum envelope and cap at 0.20 world units. Then key the adjusted rig-object root translation alongside both original foot-target animations for 169 frames. This is a bounded geometric feasibility experiment, not physical mass transfer, acceleration regulation, or ground reaction forces.

Output: actual native editable Blender rig and 5 true technical Cycles PNG frames, frame-by-frame hip-foot residual and contact drift, source-rest reachability shortfalls, source-basis-corrected skin deformation, polygon foldover/collapse and an exact 169-frame pelvis correction preplan. Two independent ephemeral public GPU-free jobs: original neutral and uncalibrated shape_20 skin morph.

## Fail-closed

Report even if the pelvis lowering is capped, targets remain unreachable laterally, foot slip increases, body penetrates ground or transient visual motion is unnatural. Do not compensate with bone stretch, move ankle targets, or silently relabel world dimensions. R014 and R009 production/cinematic acceptance is always HOLD. This branch and siblings remain draft, unmerged, source-only Git; durable native binaries and receipts go to private Drive. DLE authority [R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138), morphology [R015 #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141), R009 #23 video.
