# R2: Gaussian parameter sensitivity on known source geometry

**Authority:** [Stable Character R034 #169](https://github.com/SemperSupra/stable-character-pipeline-private/issues/169#issuecomment-6883578932), [R1 virtual captures PR #508](https://github.com/SemperSupra/stable-character-pipeline/pull/508); shared DOE methods [Model Mechanisms #1](https://github.com/SemperSupra/model-mechanisms-private/issues/1). R1 exact-head [free public run 43637009818](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43637009818) PASS with 24 images/12 matched pairs/16 native source vertices and 204 deterministic PLY splats. The source-native mesh/rig/material/physics/time state is canonical; 3DGS is **optional** appearance/reconstruction research.

## Hypothesis

A Gaussian shell sampled from exact mesh surfaces may show poor silhouette overlap despite following pose and material interventions. Tuning its *explicit* positive scale/opacity parameters on ONE observed view might improve reproduction. Does that adjustment transfer to unseen camera views, hinge poses and material edits without affecting source-native geometry? What does that teach about the utility—and limitations—of splat parameters as independently composable controls?

## Preregistered design (fixed before examining results)

- Original procedural 2-link source from R1, 204 ordered surface Gaussians. Native Blender mesh/known transforms unchanged. Source-rendered mesh alpha silhouette is exact known-ground-truth control, not a trainable model.
- 5 common multiplier values for the three positive Gaussian radii: **0.55, 0.75, 1.0, 1.25, 1.6**.
- 3 raw opacity-logit settings: **1.5, 3.0, 4.0** (via Blender standard 3DGS PLY `opacity` field); their logistic probabilities are distinct. Baseline **(1.0, 4.0)** must be byte-identical to the R1 PLY.
- 15 fixed treatments × four source/camera conditions: **60 actual Gaussian Cycles CPU renders** + four native mesh renders = 64.
- **TRAIN**: hinge 0°, lower blue, front camera. Choose winner solely by maximal binary-alpha IoU versus native-mesh image, tie by smaller mean absolute alpha error. All candidates compared identically with alpha threshold 0.15.
- **HOLDOUT-1** pose: hinge 90°, lower blue, front camera. **HOLDOUT-2** different view+pose: 45°, lower blue, oblique camera. **HOLDOUT-3** edit+pose+view: 45°, lower green, oblique camera. Compute *chosen minus baseline* IoU/alpha L1 on holdouts only after choosing from train. The winner is frozen immediately after rendering and scoring the training condition, **before heldout scenes are rendered**. Full factorial heldout results are subsequently retained for sensitivity exploration, but not used to retroactively select the winner.
- Exact native geometry and camera matrices are inherited from R1. The only modified PLY fields are Gaussian log-scaled radii and opacity logit. World center, quaternion, colors, source pose, clock and mesh remain fixed and checked.

## Falsifiers and state

**Independent anti-shortcut metrics:** for each native mesh/baseline/selected rendered condition, record (i) average alpha and fraction alpha <0.9 inside a 5×5-eroded native mesh silhouette, (ii) mean adjacent RGB-pixel variation inside that silhouette as a speckle/texture-gradient proxy, (iii) false-positive/false-negative silhouette pixels. Higher IoU alone can reward tighter Gaussians that create translucent/aliased interiors; a regression on these metrics must remain visible, even when the experimental method PASSes. These are diagnostics, not a qualified perceptual-quality metric.\n\nAll 15 PLY hashes unique; baseline PLY byte-identical to original R1 fixture; reject invalid/nonpositive/nonfinite parameter values; all quaternion norms unit, Gaussian count always 204; source exact mesh vertices preserved; native Blender 5.3 GAUSSIAN_SPLAT imports valid; 64 nonblank finite rendered PNGs with SHA256 receipts; all numeric metrics finite, train winner no worse than its baseline (by construction); 3 heldout comparisons retained even on regression. A holdout regression is **important negative scientific evidence**, not failure of a functioning experiment. No artificial PASS gate that forces a wished-for improvement. Source asset remains original and public-safe.

**Scientific limitations:** This is a **grid search over exposed Gaussian parameters**, not gradient optimization, pretrained 3DGS reconstruction, MLX speed experiment, fair PBR-vs-SH model contest, 3D printed geometry, photorealistic human modeling, clothing behavior or full real-scene generalization. The visual target uses alpha silhouettes alone, so improvements in IoU can reflect blur/opacity threshold behavior and need independent RGB, depth, surface, view, lighting and physical metrics before promotion. The scene and camera represent one source object only; heldout is within this scene, not generalization across subjects.

## Execution

`python3 research/gsplat53/rig_fixture.py` then `BAKEOFF_R2_OUT=out/gsplat53-r2 blender --background --factory-startup --threads 4 --python-exit-code 1 --python research/gsplat53/r2_param_sweep.py`. CI workflow `.github/workflows/gsplat53-r2-param-doe.yml`, standard **free public** `ubuntu-24.04`, official Blender 5.3.0 SHA and mirror failover, 18-min limit and 3-day artifact retention. Persist result digest and numeric outcome in private R034 DLE. No restricted checkpoint/data or private/paid cloud spend.

**Next experiment R3 (conditional):** If this controls a useful appearance tradeoff and passes holdouts, freeze calibrated splat primitive parameters and implement a small true differentiable RGB/depth inverse-render fitting experiment on existing Apple MLX R0 (public Model Mechanisms PR #23); add matched novel camera, material-light nuisance, pose/occlusion, costs and preserved geometry. If not, keep mesh/PBR direct rendering as standard and reserve splatting for independently qualified unknown-geometry reconstruction. Decision on deployment is tied to measured advantage, not novelty of representation.

No merge/production adoption until independent exact-head source/receipt review, separate from owner manual review.
