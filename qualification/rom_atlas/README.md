# ROM V1 evidence atlas — human, animal, mechanical

Authority: [public DLE #170](https://github.com/SemperSupra/stable-character-pipeline/issues/170), related VisualQA #150 / walking #84. Source-clean evidence and schema only. This atlas contains **no unvalidated human or animal normal range values**. It is a source inventory, not a reference atlas that can approve arbitrary character motion.

## Noninterchangeable coordinate systems

Every motion measurement has explicit **anatomical joint identity**, parent and child bone, local right-handed basis, neutral zero, rotation sequence, sign, units, pose capture clock and source version. A 2D stick-leg angle is not a human knee flexion JCS coordinate. For the hip, knee, ankle, shoulder, wrist and spinal articulations use the relevant ISB convention or a documented independently mapped alternative. Anatomical joints may translate and rotate together. Arbitrary Euler angles and a single authored bone pole cannot establish anatomy.

Animals require taxon **and** verified bone homologies: a dog has a stifle and hock, and a bird's backward-appearing intertarsal joint is an ankle, not its hidden proximal knee. Equine stifle-hock coupling is not strictly fixed; a linear mimic relation cannot prove its physiological motion. Dog and horse published goniometric and markerless studies are research input with breed/size/age/sedation/gait/phase/subject sampling constraints. Do not substitute canine measurements for felines, horses, birds or extinct creatures.

Mechanical designs need controlled prismatic, revolute, continuous, spherical, fixed, compound/loop, cable and tendon elements; ROS URDF offers one subset of semantics and may require ros2_control, MuJoCo or a full mechanism model for more complex couplings and dynamics. Require position/velocity/acceleration/jerk/effort/actuator thermal and collision constraints **as applicable**; bounds require manufacturer or source authority, not invented limits. Multi-DOF feasible sets are coupled surfaces, not simply independent min/max boxes.

## Constraint qualification tiers

1. `OBSERVED`: independently obtain actual scene/rig joint world poses and source frame clock, verify source binary SHA and rights.
2. `GEOMETRIC`: independently map joint local anatomical/mechanical frames; check angle and translation envelopes, coupled constraints and continuity.
3. `KINEMATIC`: observed angular velocity, acceleration and jerk with supported fps, phase, load and source provenance.
4. `DYNAMIC`: torque/effort, moment arms, muscle/tendon force, friction, inertia, ground reaction forces, fatigue/thermal as appropriate.
5. `VISUAL`: corroborate the correct joint, visible limb location and any contradictory 2D/3D landmarks under independent view/occlusion.

Every tier produces `PASS_BOUNDED_SCOPE`, `FAIL` or `UNKNOWN`, but **not** whole-person/animal/robot realism acceptance. Hard failures veto. Missing or inapplicable evidence stays UNKNOWN and cannot be cast as a PASS. Contact, visual defects and private product hold remain independent vetoes.

## Research and admission workflow

Read `research_sources.json` for research sources and their exact readiness. New numerical ROM tables must include explicit units, orientation, population context, measurement method, activation/passive status, DOI/license and independently checked bounding confidence, plus source approval. Where biological data are absent, qualify only source-authored fictional fixtures, with `SYNTHETIC_TEST_ONLY` scope. Joint selection and review must be traceable in DLE. Do not train on copyrighted restricted datasets, or publish protected identities, private captures, runner endpoints, hardware or paid resources. Source code/metadata -> Git/DLE; large images/motions/model binaries -> private Drive with complete-byte SHA custody after rights admission.

Three audiences: human-readable source and frame-by-frame anomaly report; deterministic Go/Python JSON CLI receipts; discoverable schema, action semantics and provenance graph for agent automation. No merge, release, deployment or CPE promotion without owner approval.
