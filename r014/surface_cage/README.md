# R014 sculpt-to-rig surface-cage experiment — not release quality

This is an independent, source-only research workcell: the previous 2026-11-12
[failed sculpt-to-MPFB weight-transfer job](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43218606862)
is rehydrated unchanged. Each real synthetic male/female adult sculpt is
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
- Pre-bind mesh registration still fails; diagnostic translation of the
  incorrectly saved scene is **not** a valid anatomical landmark fit.
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
