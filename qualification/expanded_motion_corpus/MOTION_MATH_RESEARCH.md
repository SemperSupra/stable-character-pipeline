# Parametric human-like motion research — v0.1 (2026-11-12)

## Scope and scientific caution
This is a research implementation map, not a biomechanical validation or claim that human motion is determined by binary sex. The original labels `male` and `female` denote two **adjustable morphological presets** (hip/shoulder widths, link lengths, timing). Individual anatomy, age, fitness, technique, terrain, clothing, footwear, and style can have substantial effects. A future rig should use continuous body dimensions and a separate motion-style vector; neither stereotypes nor classification from images are needed.

### A. Parameter vector and evidence boundaries
Let the state at time t be a pelvis/root pose and joint angles x(t) = [r(t), R(t), q(t)] with body measurements M, equipment E, task T, environment W, and style S:

`x(t) = F(t; M, E, T, W, S)` subject to constraints `C(x, xdot, M, E, W)`.

Suggested independent normalized metadata: gravity `g`, mass, hip height, shoulder/pelvis breadth, thigh/shin length, foot length, ROM, damping, speed, cadence, stride, duty factor, heel height, foot/toe support polygon, friction coefficient, joint limits, center of mass, joint trajectories, timestamps, camera transforms, nominal exercise and actual dynamics status. All physical units SI. Each value must be marked `measured`, `derived`, `hypothesis`, or `unqualified`.

### B. Locomotion: Froude similarity, stride frequency, phases, contact
A dimensionless dynamic similarity measure (Alexander and Jayes 1983) is

`Fr = v^2 / (g * L)`

where v is forward speed, g is gravitational acceleration, and L a specified characteristic leg length. Similarity is a *scaling hypothesis*, not a gait acceptance threshold. Source: https://doi.org/10.1111/j.1469-7998.1983.tb04266.x

For a same-side stride of length s and average speed v: `f_stride = v/s`. If steps alternate equally, `cadence_steps_per_min = 120 * f_stride`. The *duty factor* is the stance fraction `D = T_stance / T_cycle` and is motion/footwear/speed dependent. At stance, lock world contact anchor `p_foot(t)=p_anchor`; at swing, use a smooth trajectory to the next anchor. If a labeled stance ankle has nonzero finite-difference world speed above tolerance, FAIL the contact oracle. A no-contact aquatic clip must not PASS a ground contact oracle.

For stepping/balance, require support polygon plus projected COM or center-of-pressure/contact-wrench evidence before asserting balance. A purely kinematic rendering is not proof of dynamical stability. For running/hopping, a spring-mass (SLIP) system is a better model than simply increasing walk frequency: stance leg compression and ballistic flight require force integration. Geyer, Seyfarth & Blickhan 2005: https://publications.ri.cmu.edu/spring-mass-running-simple-approximate-solution-and-application-to-gait-stability

### C. Point-to-point movement: minimum-jerk and law-of-cosines IK
Let u=(t-t0)/T in [0,1]. A common C2 point-to-point interpolant is

`s(u) = 10*u^3 - 15*u^4 + 6*u^5`

and `p(t)=p0+(p1-p0)*s(u)`; zero endpoint velocity and acceleration. A swing foot may add vertical lift `h sin(pi*u)` but **that sine arc alone has nonzero endpoint vertical velocity**, so a physically credible, C2 touchdown should replace it with a boundary-controlled spline or separate blending phase. Flash and Hogan 1985: https://pubmed.ncbi.nlm.nih.gov/4020415/ ; open discussion https://pmc.ncbi.nlm.nih.gov/articles/PMC13439047/

Given hip H, ankle A, link lengths L1,L2 and distance d=||A-H||, two-link reachability requires `abs(L1-L2) < d < L1+L2`, modulo intended singularity handling. Along-link length is `a=(L1^2-L2^2+d^2)/(2*d)`, offset `h=sqrt(L1^2-a^2)`; choose the approved anatomical bend pole for the perpendicular direction. Unreachable targets must **not silently clamp d while leaving ankle unchanged**; that corrupts the source leg length. Analytical IK reference: https://courses.ideate.cmu.edu/16-375/f2026/text/reference/two-link-kinematics.html

### D. Footwear as physical affordances rather than categorical gait stereotypes
Treat shoes as foot constraints with measured parameters (heel rise, sole stiffness, toe box, traction, contact polygon, ankle ROM, footwear mass, retention, heel-to-toe roll and slip threshold). High heels typically increase plantar flexion, alter rollover, knee motion and lumbar posture, and may reduce step length/stability, but individual response varies. A controlled comparison must not prescribe a universal value based only on category. Review: https://pubmed.ncbi.nlm.nih.gov/29475153/ ; more recent observational data https://pubmed.ncbi.nlm.nih.gov/42355503/

Minimum heel/contact physical terms: shoe rotation `theta_ankle`, vertical heel sole height `z_heel`, horizontal support polygon `P_contact`, normal force `N>=0`, tangential friction `||F_t|| <= mu*N`, no floor penetration, and zero world-frame contact velocity when planted. Need specialized model for slips, toe-off, heel-strike, sandal flapping and stiletto small support area.

### E. Actions, dance and gestures
For sitting/standing, squats and poses: use phase-labelled transitions, bounded joint ROM and an explicit support transition (feet, chair, hand, airborne). Transition key poses using minimum-jerk or splines; optimize collision, balance and jerk, but do not pretend positional interpolation is force-consistent. For dance, a beat phase `phi(t)=2*pi*f_beat*t + phi0` can drive Fourier or rhythmic-DMP joint components with style vectors for Laban Body/Space/Shape/Effort, subject to support constraints. Laban reference: https://pmc.ncbi.nlm.nih.gov/articles/PMC6455080/ ; dynamical movement primitives (DMP) tutorial https://doi.org/10.1177/02783649231201196

Martial-arts kata should use named phase/pose templates, transition timing, COM support and verified technique references; a few arm gestures are **not** equivalent to karate, judo or kickboxing technique. Cartwheels require hands as alternating supports, body-axis inversion and positive hand-ground support; feet alone are insufficient. Keep current primitive templates labelled **unqualified placeholder** until domain-specific motion and force validation.

### F. Swimming/diving require different dynamics
Water introduces buoyancy, drag, momentum, body pitch, hydrodynamic torque and stroke-specific recovery. A dry-land contact evaluator should return UNKNOWN for swimming. Front crawl arm coordination can be represented by the normalized index of coordination `IdC = (t_propulsive/T) - 1/2`, for idealized equal-arm alternating cycles, where negative indicates catch-up and positive overlap. This alone is not a swimming-performance score. References: https://doi.org/10.1098/rspa.2020.0071 and https://pmc.ncbi.nlm.nih.gov/articles/PMC3613086/

Diving needs takeoff support, airborne COM integration `z(t)=z0 + vz0*t - 0.5*g*t^2` until water entry; post-entry velocity/direction then changes with fluid forces. Stylized clips have **not** satisfied these physics.

### G. Reusable parameterization: DMP and objective optimization
A discrete DMP (tutorial, see source) is a second-order attractor with a learned forcing term:

`tau * z_dot = alpha_z * (beta_z*(goal-y) - z) + f(phase)`

`tau * y_dot = z`

Use this for retargetable gesture and technique trajectories; rhythmic DMPs or Fourier oscillators for periodic gaits, strokes and dances. Optimization objective should penalize `joint_limit`, `contact_slide`, `foot_penetration`, `self_collision`, `pose_drift`, `balance`, `jerk` and deviation from original measured/video data with explicitly declared weights and force limits. A neural generator may propose poses; only an independent judge produces qualification verdicts.

## What the actual 22-case audit found
The baseline `build_motion_batches.py` creates real source-driven animated GLBs and decodable 40-frame H.264 MP4s, but some templates have wrong contact labels or unreachable leg geometry. Independent pure-standard-library `motion_math.py` tested 22 source-labelled cases at 1 cm limb-length tolerance and 0.025 m/s labeled-stance speed tolerance: **10 PASS / 11 FAIL / 1 UNKNOWN**. The 10 PASS are only those targeted checks; none is a realistic-human animation acceptance. Failures cover jump leg lengths, ground-anchored idle drift, jumping-jack stance mislabeling, cartwheel, pinup, photoshoot, dance, kata and diving. Swimming UNKNOWN because ground stance doesn't apply. Do **not** relabel or delete these original examples: they are valuable negative controls; maintain immutable source SHA and separate corrected generation.

### Next corrective algorithm
1. Expose independent continuous `Morphology`, `Footwear`, `MotionStyle`, `TaskPhase`, `Environment` parameters (preset labels optional, never laws of sex).
2. Solve pelvis/root trajectory and exact reachable world-space contact anchors with a two-link inverse-kinematics solver that rejects unreachable targets; optimize the root or change phase where needed.
3. Mark landing/contact only when foot world velocity is within tolerance, height is compatible with support geometry, and support surface is declared. Introduce hand and chair contacts as separate modes.
4. Use C2 transitions for authored poses; rhythmic DMP/Fourier for dance, sprint steps and swim stroke rhythms; spring-mass/ballistic integration for takeoff and flight.
5. Re-render the same multi-camera source, retain immutable wrong-motion examples and independent before/after oracle evidence. Keep UNKNOWN when no qualified dynamics or visual pose model exists.

## References
- Alexander & Jayes (1983), dynamic similarity hypothesis: https://doi.org/10.1111/j.1469-7998.1983.tb04266.x
- Flash & Hogan (1985), minimum jerk: https://pubmed.ncbi.nlm.nih.gov/4020415/
- Geyer et al. (2005), spring-mass running: https://publications.ri.cmu.edu/spring-mass-running-simple-approximate-solution-and-application-to-gait-stability
- Schaal/Ijspeert et al. and tutorial survey, DMP: https://doi.org/10.1177/02783649231201196
- Carnegie Mellon two-link kinematics: https://courses.ideate.cmu.edu/16-375/f2026/text/reference/two-link-kinematics.html
- High-heel gait review: https://pubmed.ncbi.nlm.nih.gov/29475153/
- Laban Movement Analysis: https://pmc.ncbi.nlm.nih.gov/articles/PMC6455080/
- Front crawl coordination: https://doi.org/10.1098/rspa.2020.0071
