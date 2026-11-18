# R088 — Real 100STYLE recorded locomotion, native source-target preflight

## Why this workcell
R084 observed physical foot penetration and severe skating on mechanically valid R082 clothing. R085 lifts roots at sampled frames but does not fix stance. R087 established actual MakeHuman/MPFB 163-bone subdivided legs. Replace invented motion as *input* with recorded, genuinely acquired BVH; validate numerical semantics and measurable target compatibility before adopting any retarget output.

**Publisher:** 100STYLE by Ian Mason, Sebastian Starke, Taku Komura, Xsens 60fps, [author's original source and CC BY 4.0 license](https://www.ianxmason.com/100style/).
**Derivative examined:** [tomcatmew/simple_motion_matching](https://github.com/tomcatmew/simple_motion_matching/tree/10938b4881b55c5801faded89e427407ddf14bce/data/100style), exact commit `10938b4881b55c5801faded89e427407ddf14bce`, previously trimmed per `Frame_Cuts.csv` / 40s and rounded to 0.01. Not byte-identical to Ian Mason original. Single source actor across styles; NOT independent persons, demographics or photographic identities. **Never equate author-supplied motion label with ground-truth biomechanical contact.**

Three selected byte-pinned Git blobs: `Neutral_FW.bvh` `a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61`, `Neutral_TR1.bvh` `1b7af92a4df47d4f5e12db32bac90a968a03e0b9`, `Old_FW.bvh` `a3b13a437de7d2151f3c9743d51b5ccfe332b3bd`.

## Actual hosted evidence
Two independently controlled public free GHA jobs. First acquires three actual upstream derivative BVH files into ephemeral runner only, checks exact Git blob identity and bounded syntax, performs **full numerical forward kinematics** (cm, Y up) and writes root horizontal travel and independent inferred ankle/toe near-minimum vertical position / sliding candidates. Second creates fresh actual official MPFB 163-bone Aster/Juniper rigs and compares source hip→knee→ankle length against five native MPFB subdivided leg bones, independently verifying rig lineage and source files. No BVH/Blend redistributed. JSON receipts only. No private source images/model, vendor Alison, Naomi source, private/paid minutes, or automatic merges.

## Mandatory negative controls and next action
11 adversarial source tests: axes, clocks, forgery, duplicate bones, frame count, nonfinite, channel count, source pin. Strict results show raw BVH root/candidate foot dynamics; **ground truth foot-ground contact is unavailable** and source ankle is not the target shoe sole. Native leg ratio is a measurement, **not a full retarget**; next workcell qualifies Diffeomorphic BVH Retargeter against native MPFB with rest-pose/axis/leg chains, then applies R084 sole-world-space critic and blinded camera review. This workcell never promotes photorealism, physical gait, identity, MVP, or release.

Source selection DLE: public #349 / #29. Native foot/contact DLE: #645/#646/#648; private MVP #23 and private motion source R012 #35. All scopes draft, unmerged.
