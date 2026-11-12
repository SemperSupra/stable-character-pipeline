# R014 sculpt-to-rig surface-cage experiment — not release quality

This is an independent, source-only research workcell: the source-preserved 2026-11-12
[PR #437 corrected world coordinates and fresh-reopen baseline](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43248830711)
is rehydrated unchanged. The prior [failed source scene](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43218606862) is retained as negative control. Each real synthetic male/female adult sculpt is
evaluated against the 163-bone MPFB rig without copying mismatched skin weights.

## Why this experiment exists

Nearest-triangle weight transfer was structurally executable but
anatomically **invalid**: 52–61% of sculpt vertices were over 50 mm from the
rig source surface and posed shoulders/hips tore. An alternative
[Blender Surface Deform](https://docs.blender.org/manual/en/dev/modeling/modifiers/deform/surface_deform.html)
uses an existing skinned mesh as the driver. Blender warns that distance between
driver and bound surface itself can cause artifacts. This is a falsification
bakeoff, not a claim that a different modifier fixes the problem.

The workcell tests actual pose-induced surface displacement; vertex counts;
triangle inversion and area shrinkage; authored Blender Studio Multires level-1
evaluation after binding; correct female=0/male=1 source controls; neutral and
posed rendered camera-framed images; and saved native Blender scenes.

## Execution boundaries

- Research branch remains DRAFT and UNMERGED. Authority:
  [private R014 DLE #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138).
- Never ship old wrong-phenotype model receipts as positive evidence.
- Uses only previously public, source-pinned adult synthetics. No user likeness,
  identity photos, private character models, protected content, or restricted keys.
- $0 public GitHub Actions disposable runner. Source-only Git; large native
  binaries stay in short-lived GHA staging until verified private Drive custody.
- The saved source must pass a separate Blender fresh-reopen geometry-position
  receipt; this workcell applies **zero** centroid transformation. The prior
  stale-world-coordinate scene remains a rejected independent negative control.
  Source/target residual anatomy correspondence remains poor regardless.
- Even a successful bind and an L1 vertex-count match cannot certify sculpt
  detail, UV preservation, facial anatomy, genital morphology, foot contact,
  physically plausible deformation or human realism.
- Machine status remains **HOLD**, without automated promotion.

## Next qualifying step

If measured surface-cage displacement is non-inverting and visually
plausible, constrain regional landmarks and test the actual L3 authored detail,
arm/shoulder and hip contact at extreme poses, animation transport, local
tissue volume/contact and 1080p independent review. Otherwise retain the
negative control and try a physically grounded retopology/skin-cage pipeline.
