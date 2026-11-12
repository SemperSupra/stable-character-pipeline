# R014: real MHR latent shape-response qualification (research HOLD)

Native whole-body morphology control research on the **actual source-pinned public MHR v1.0.1 TorchScript model**, independent of the MPFB/Blender Studio surface-deform failures.

Two public disposable CPU-only jobs sweep all **45 opaque identity/shape latents** at ±0.35 with the 204 body-pose and 72 face-expression controls fixed to zero. Every result is measured on **real model vertices** (not toy control values), with signed changes, raw coordinate bounding spans, finite-difference response, local Jacobian rank and axis correlations. Each cloud job has separate source hashes and receipts. Source checks verify the published release archive and the embedded asset license; model weights are held in RAM only and **never uploaded**.

This workcell explicitly **does not** assign body-shape meaning (e.g. stature, body fat, bust, hip, sex, age, BMI or centimeters) to any latent. Those require matched anatomical landmarks, known source units and independent mesh/visual calibration. It also cannot guarantee an arbitrary full physical morphology range from 45 neural coefficients. All variation is mathematical exploratory testing, not a completed photoreal person.

Boundaries: [private R014 DLE #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138) controls actual mesh/rig; [R015 #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141) controls CPE/spec consumer mapping. Do not mutate CPE or claim R015 calibration. This branch is a **draft, unmerged** isolated public source-only experiment; no private identities, likenesses or protected files.

## Next experiments

1. Compare each native TorchScript variant to saved/reopened Blender character using exact geometric checks, not just output filename or vertex counts.
2. Ground body measurements in documented sex-neutral anatomical landmarks and real units. Derive Jacobian maps and residual, uncertainty and non-invertibility for requested measurements.
3. Verify extreme morph combinations on the actual articulated and subdivided model: triangle foldover, per-region volumes, contact, UV texture stability, MHR native rig, facial controls and finger detail.
4. Only after acceptance, pass typed capabilities to R015. Never equate source numerical parameters with physical age, sex, identity, or anatomical completeness.

Numerical experiment is not cinematic video quality, external genital anatomy, realistic soft-tissue, FACS/viseme, or high-res L3 rig acceptance. Fail closed: **R014/R009 release remains HOLD**.
