# ROMFMT C — authored source limits and format capability boundaries

Authoritative ROM metadata DLE #175. Source original-only JSON fixture, 8-format research matrix and separate source-text conversion checks for USD Physics, URDF, MuJoCo MJCF and OpenSim Coordinate. Formats do **not** mean the same thing:

* USD Physics Revolute uses degrees; its rigid-body PhysicsJoint is not the same as UsdSkel skeletal joint and limits do not magically constrain skeleton animations.
* URDF revolute uses radians and needs separate source velocity and effort, plus actual controller/hardware authority for runtime behavior.
* MuJoCo MJCF is explicitly emitted with `compiler angle="radian"` to avoid compiler angular convention ambiguity. No motor is authored; source effort is deliberately marked **NOT PRESERVED** instead of fabricating an actuator.
* OpenSim Coordinate source XML range uses radians for rotational coordinates, `clamped=true`; source model/physiology and full .osim loaded semantics NOT qualified by this fragment.
* FBX has native rotation limits but different Euler/rotation-order and pre/post-rotation semantics; require native FBX SDK/independent import review before claiming parity.
* VTK data arrays support carrying arbitrary data, not generally rig constraints. Keep canonical ROM manifest external.
* Blender and GLB have separate independent qualification PRs. A full 3D rig constraint provenance and humanoid/animal joint coordinate mapping remains future work.

The tests check exact source values, degrees/radians conversions, refusal to infer missing effort or velocity, absence of unsupported mechanical or anatomical authority, axis sign, and source-only confidence. They **do not** parse emitted USD with OpenUSD or emitted OpenSim snippets with OpenSim, simulate MuJoCo, import FBX or certify physical safety. All green outcomes are `SOURCE_TEXT_PROJECTION_TEST_ONLY_NOT_NATIVE_ENGINE`.

Git/DLE for this small matrix+source. No substantial output files in this batch, no Drive custody claim. Preserve no-private-media/public-runner, paid runners, merge/release/deploy/CPE and exact source SHA boundaries.
