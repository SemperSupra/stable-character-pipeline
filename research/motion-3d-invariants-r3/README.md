# Motion R3 — first-party 3D rig translation physical-coordinate falsifiers

Independent source-safe math/geometry workcell based on public `main`, not on other motion-source or actor branches. Tests original mathematically generated **3D** joint FK and weighted linear-blend skin across proper rotation, mirror reflection and local axis conventions. No real MakeHuman rig, Blender, capture, VMD, animal, native physics, or trained ML model.

Independent hosted standard public CPU Go stdlib lanes:
- **quaternion:** WXYZ vs glTF XYZW conversion; q vs -q antipodal continuity; noncommuting parent/local rotations; refuse nonunit or NaN
- **parity:** source joint hierarchy transformed by reflection across X; mirrored coordinates and quaternion axial-vector transformation must produce corresponding world transforms, while a determinant −1 reflection cannot itself be a proper SO(3) quaternion rotation
- **weighted-skin:** bind-to-pose multiweight LBS skin world position, reflected result parity, reject invalid weights/bone indexes
- **topology:** source immutable; root/parent order, duplicate IDs, nonfinite offsets and rotations invalid

All source is first-party source-original and no external dependencies. Each lane runs independently on public free Ubuntu-24.04 CPU, max 5 minutes; no secrets, external media, paid/private Actions, GPU, model weights, acceptance promotion, merge or deployment.

This is a **mathematical prerequisite**, not real MPFB/MHR source-to-target correspondence; source motion anthropometry, twist, ROM, pelvis contact, glTF bind inverses, native engine skin, quaternion numerical drift at millions of steps, source-instance fidelity and realistic biomechanics remain unqualified. The separate true MMD→Blender→GLB workcell #630 is orthogonal and cannot be replaced by passing these source tests.

Existing DLE authority: public Motion #29, MMD #19, Visual QA #150, private R014 #138, R009 #23, R033 #168. Human README, Go tests machine stdout, source test IDs for agents. DLE = Durable, Legible, Executable.
