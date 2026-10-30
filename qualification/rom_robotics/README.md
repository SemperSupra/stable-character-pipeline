# ROM V1 — source-only robotics limit extraction

Authority [ROM DLE #170](https://github.com/SemperSupra/stable-character-pipeline/issues/170). The Python standard-library `urdf_observe.py` works offline on locally admitted original synthetic URDF only, with bounded size and no network. It parses source robot/link/joint/mimic/axis data, and preserves SHA256 provenance for proposed revolute/prismatic/continuous/fixed joint hard positions, velocities and efforts.

Its only positive outcome is **PROPOSED_MECHANISM_LIMITS_UNQUALIFIED**. URDF limits may not match physical hardware, gearing, servo power, controller safety, collisions, soft-stops or thermal behavior. The adapter deliberately makes no effort to infer missing acceleration/jerk and treats an unmodeled loop/compound/ball joint as ineligible for this subset. Test hostile DTD, invalid axis, bad mimic, nonexistent links, wrong hard bounds, missing velocity/effort and continuous stop contradictions.

Follow-on adapters (separate source/rights review) should implement ros2_control soft/effort/acceleration/jerk configuration, MuJoCo MJCF equality/polynomial/tendon constraints and actual powered dynamics, and OpenSim .osim nonlinear coordinate couplers. No direct arbitrary XML conversion into a biological pass. Spherical/manifold limits and collision/ground/load proofs require real geometric and physical solvers.

Git/DLE owns source and constrained JSON metadata. Large model/rig artifacts belong in owner-private Drive only after AAR/CDR full-byte verification. Public free CPU Actions only on original fixtures, no protected identity, owner merge/release/deploy/CPE hold.
