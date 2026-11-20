# N03D-AD — Controlled planted-foot reference and explicit contact-state transitions

**Authority:** public #662/#650; private MVP #23; AD branch rooted at qualified AB #699 immutable head. Original synthetic reference, not Naomi/Alison/MPFB/CC0 output.

Ground-truth fixture: an analytic sagittal two-bone leg (0.45m each), rigid 0.20m heel-to-toe foot, deterministic 60 samples @60Hz. Explicit phases SWING, HEEL, FLAT, TOE and UNKNOWN fail-closed; one planted heel, two flat support endpoints, one planted toe, then ground-free swing. Use true mathematical point constraints and two-circle intersection IK, with nonstretch segment lengths. Independent oracle recomputes actual geometric penetration, persistent ground-contact slide, leg/foot reach, clock and valid transitions. Acceleration, force, balance and third-dimensional anatomy are NOT qualified. The fixture is a reference harness for the more difficult MPFB native retarget, not evidence that a real shoe can reproduce it.

Parameters deliberately exposed: femur/shin length, foot length, hip trajectory, step length, heel-strike/toe-off angle, ground plane, contact-state lengths, velocity/slip and clearance tolerance. The source provenance/rights and acceptance contracts never allow synthetic success to promote protected R009 MVP.

## Design of experiments

- Baseline known-contact fixture is expected PASS_NARROW only.
- Slide a nominal planted heel while maintaining state label -> independent critic FAIL.
- Forced lower heel / raised toe / discontinuous contact state / unreachable chain / nonfinite source / clock drift / unsupported rights / forged MVP PASS all fail.
- Convert reference into future native Blender rig-mesh/posture calibration only after source-target anatomical and heel-ball-toe IDs have been independently confirmed.
- 2 parallel free public CPU jobs: adversarial controls and independent fixture execution + witness JSON. All provenance/error results must be retained, source unchanged, no private GPU/Actions.
