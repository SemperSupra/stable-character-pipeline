# R014 full gait retarget: correct the MHR IK end effector

This is an independent **corrective test**, not a rewrite/merge of the historical failed [PR #446](https://github.com/SemperSupra/stable-character-pipeline/pull/446). The old native 169-frame proof is preserved as a decisive failed experiment.

## Source-backed root cause

- [R014 #454](https://github.com/SemperSupra/stable-character-pipeline/pull/454) verified pure 0.2-unit armature-object root motion leaves 18,439 evaluated skin vertices rigid (p95 error below 1e-7), zero inversions. Moving the skeleton's root pose bone by 0.2 local units instead moved the root only 0.002 world units due original FBX scale, so object root motion remains the correct baseline pending further tests.
- [R014 #455](https://github.com/SemperSupra/stable-character-pipeline/pull/455) verified that MHR lowleg bone's tail is **0.49048 world units away** from the anatomical foot bone head. PR #446 applied a two-link IK to this **wrong lower-leg display tip**, asking it to follow a world-foot trajectory and causing up to 528 inverted skin triangles in a neutral stand and >17 world units of skinned-motion excursions during walking.
- The same public MHR left/right source in #455 supports a three-link foot-bone IK endpoint: foot.tail is ~0.0001 world units from foot.head and static foot-head target produces zero inverted base triangles in both legs.

## This corrective branch

Starting from the exact #446 source/Go 169-frame trajectory and source hash contracts, change only the IK constraint endpoint to the **real MHR foot bone with chain_count=3** (includes 2 anatomical leg links plus tiny foot end effector). Keep actual 169-frame root translation/turn, individually keyed foot targets, independently measured ankle/toe world contact drift, target residual, five evaluated mesh-pose triangle inversion/area-collapse samples, and editable Blender plus five Cycles PNGs. Two independent rights-clear public CPU GHA jobs: neutral and one uncalibrated shape_20 morph variant.

Add a strict new source footbone tip-to-ankle-head gap (<0.001 native Blender world units) and fail-closed **runaway skin motion >1.5 units** to the candidate assessment. Do not call source Go foot math equivalent to biomechanical foot lock, nor interpret normalized MHR shape_20 as a named human body type. The experiment can still fail from unreachable targets, solver instability, toe pivot or source model properties.

### Acceptance

Green workflow status only means data and receipts collected. Candidate (research) requires source lineage, both legs' stance/heel/toe errors within stated bounds, zero sampled inverted/collapsed triangles, no runaway skin deformation and independent true image review; **it is never by itself cinematic film, 4K skin, anatomy, soft-tissue or product acceptance.** Any failed metric remains in recorded JSON, rather than being silently waived.

Private authority [R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138), R015 body-morphology consumer #141, R009 video #23. Draft/unmerged; no private likeness, no protected source, no paid GitHub runner minutes or persistent host installation.
