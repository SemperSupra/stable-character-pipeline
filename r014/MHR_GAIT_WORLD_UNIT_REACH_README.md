# R014 native MHR gait — world-unit and leg-reach correction

## Critical independent observation

The actual public MHR v1.0.1 FBX armature in the root-motion experiment [PR #454](https://github.com/SemperSupra/stable-character-pipeline/pull/454) has a world-to-rig linear mapping with singular values **(0.01, 0.01, 0.01)**. That is source evidence: the imported rig's armature object maps a 20-centimeter world translation directly but a local root-bone translation of 0.20 to only 0.002 Blender world units. The previous [corrected foot-IK #456](https://github.com/SemperSupra/stable-character-pipeline/pull/456) erroneously reported 27.980 **local** units of skin deformation as though they were metres; that corresponds to **0.2798 world units** (assuming world units metres). This is not an anatomical skin explosion. The actual 5-frame technical rendered sequence shows a coherent clay model, albeit unconvincing/stiff walking.

The GHA job status on #456 was SUCCESS (evidence capture), but its structural_contact_candidate was false because the 1.5-unit skin bound was applied **in rig-local space** (effectively only 0.015 world units). This is an overly restrictive and dimensionally invalid criterion; preserve as failure evidence. Correct the calculation, not the acceptance threshold by guesswork.

## Experimental correction (independent public neutral and shape20 jobs)

This new stacked draft branch:
- Retains exact source-pinned MHR FBX native model and Go 169-frame world foot source, as well as the verified correct 3-link foot-bone IK endpoint from #455/#456.
- Confirms actual armature transform singular values are isotropic approximately 0.01; fails on an unknown imported coordinate basis.
- Converts all rig-local *deformation relative to animated root* into actual Blender world coordinate displacement before labeling or thresholding motion.
- Separately reports old unscaled numbers as negative-control historical metrics, never metres.
- Tests the skin triangle orientation and area at 5 poses, toe/ankle/contact drift across 169 frames.
- Measures actual per-frame hip-to-ankle-target distance versus source anatomical hip→knee+knee→ankle rest length, both sides, finding the fraction and maximum overshoot beyond nominal reach. Geometry numbers are source Blender units, not a proven physical centimeter calibration.
- Leaves R014/R009 promotion on HOLD regardless of purely technical improvements, including full gait, heel-toe, body morphology, cinematic skin/hair/eyes, detailed anatomy and realistic physics.

### Expected decision

If world displacement remains under a reasonable full-body local motion bound but target/hip distance exceeds bone reach at specific frames, modify only the trajectory-relative pelvis/root/foot constraints in a new bounded branch and enforce stance continuity, rather than forcing the foot through an anatomically unreachable point. If target coordinates are reachable but right ankle residual remains high, investigate pole-vector, leg chain orientations and solver iteration.

Preserve old #446, #454, #455, #456 raw JSON/ZIP and screen evidence in private Drive; no merges, private data on public Actions, paid private runners, or release.
