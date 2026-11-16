# R0: Learned translation and critic arbitration — original synthetic only

This is a narrow, source-safe experiment, not a MakeHuman/MMD rig or verified motion VLM.

- Two invented planar two-link rigs (0.48/0.46 m and 0.53/0.47 m).
- 16 source-generator phase families × 40 frames for training and 5 *different* families × 40 heldout frames. Families share a generator; this is not held-out human performers or true out-of-domain generalization.
- Four independent arms: direct joint angle copying; learned 3-feature linear regression; learned 6-feature polynomial regression; exact analytical target inverse kinematics.
- All models are evaluated against the same source-space foot endpoint, using float64; model fitting uses regularized normal equations with pivoted Gaussian elimination.
- Simulated structured VLM observation is only an **adversarial stub**. It is NOT an inference result. Hard numeric failures always override a positive subjective claim.
- The three independent public free hosted CPU jobs are geometry, learning, and critic; their contract and exact-head results must be verified on actual CI.
- This workcell has no personal data, third-party motion, model weights, neural network, Blender, VMD, video, skeletal skinning, production rights, GPU spend, private Actions, release or merge.

Commands: go test -count=1 ./... ; go vet ./... ; go run ./cmd/bakeoff . The executable prints a typed JSON research receipt and its SHA256.

Authority: public motion #29, MMD #19, visual QA #150; protected R009 #23, rig R014 #138, and R033 critic #168 remain their owning DLEs. This workcell deliberately adds no competing authority. The next experiments should reuse the existing real CMU source #469 and real BVH/VMD/Blender workcells, then test 3D/IK contact and a blind actual VLM with independent image and geometry ground truth.

Do not infer robust generalization or natural motion from a synthetic two-link test. The teacher (analytic IK) is an upper bound for this known-geometry task; regressors may learn teacher artifacts, overfit shared generator structure, or extrapolate poorly.
