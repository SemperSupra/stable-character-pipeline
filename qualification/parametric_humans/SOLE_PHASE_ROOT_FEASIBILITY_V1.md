# R009 — 72-frame sole correspondence and root-only foot-lock feasibility

**Status (2026-11-07): RED_ROOT_TRANSLATION_ONLY_CONFLICT.** Research and diagnostic only. No modification to the 35-joint source, animation, shoe mesh, or original wardrobe. No native Blender, contact-force, gait, human realism, identity, cloth, release or merge approval.

## Source / guard

- Only the original self-authored Aster and Juniper plus permitted MakeHuman CC0 body derivative are used; `Juniper_SkirtYoke_s35_h80_Research.glb` is SHA256 `b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748`.
- From glTF 72 original LINEAR sample frames, independently evaluate both 35-joint shoes with source bind matrices and world-Y-up. No joint, source, or animation rewriting.
- Each frame: measure lowest vertex of both shoes; define *diagnostic-only* upward root offset that makes the lower shoe's lowest vertex Y=0. The offset is never applied to the source.
- For each adjacent frame pair, use only the **same persistent GLB vertex indices** that are within 5mm of the hypothetical floor in *both* frames. Require at least five persistent vertex correspondences per foot. Their 2D world-XZ displacement is the frame's foot motion witness. This avoids mistaking changing lowest-vertex identity for literal foot sliding.
- On transitions where **both** feet have qualifying persistent sole vertices, a *single* rigid root-XZ translation must serve both. If their median foot XZ displacements are `dL` and `dR`, the triangle inequality implies `max(||t+dL||, ||t+dR||) >= ||dL-dR||/2` for every root translation `t`. This is a **necessary lower bound**, not a physics simulation. Root rotation and independent IK are outside this bound.

## Actual full-source measurements

| Diagnostic | Aster | Juniper |
| --- | ---: | ---: |
| Diagnostic-only upward root Y offset | 7.379–13.163 mm | 7.485–13.142 mm |
| Worst adjacent-frame change in required root Y offset | 5.421 mm | 5.245 mm |
| Dual-contact adjacent-frame transitions with >=5 persistent sole points per foot | 23 | 22 |
| Dual-contact transitions with bilateral XZ motion disagreement >20 mm | **12** | **12** |
| Worst bilateral root-XZ disagreement | 120.547 mm | 119.840 mm |
| Necessary best-case max sole slip under root-XZ translation alone | **>=60.274 mm** | **>=59.920 mm** |

**Disposition:** The actual file is geometrically incompatible with a translational root-only foot lock during 12 measured transitions per actor. A vertical root lift could eliminate sampled sole-floor penetration by construction but would not establish natural ground contact and would leave contradictory bilateral horizontal motion. Do not commit a constant +Y offset or claim corrected gait. Next evaluate *independent* limb IK, heel/ball/toe phase assignment, root movement and 72-frame native Blender witness with foot-ground and joint-strain controls.

## Independent batches and validation

1. `measure_floor_support_v1.py`: full-source CPU LBS Y and lowest-sole clusters, source SHA pinned.
2. `measure_persistent_sole_v1.py`: persistent-vertex bilateral horizontal foot motion; 72 frames, both actors; source SHA pinned.
3. `sole_phase_root_feasibility_v1.py`: **stdlib-only**, strict 72-frame schema/clock/actor/source/finite/false-approval verification, plus geometric lower-bound `RED`/`HOLD`/relative-proxy classifications. No new workflow or resolver.
4. `test_sole_phase_root_feasibility_v1.py`: 17 hostile/positive source-free unit tests PASS; actual-source receipt produces expected exit 12, not test failure.

The original full-source GLB and frame evidence must remain in owner-private Drive; public Git may retain only source-only code, hostile tests, bounded metrics and false-approval flags. Preserve parent-base drift hold of draft PR #336, no merge/CPE/release, and maintain DLE #272 ownership.
