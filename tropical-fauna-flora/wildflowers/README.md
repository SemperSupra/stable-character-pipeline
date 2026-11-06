
## W04 geometry-bound organ receipts (independent botanical qualification)

Use the optional `-organs` argument to emit a deterministic JSON sidecar recording
**exact** per-material vertex/index extents for each generated tube, leaf, petal,
corolla, fruit and disk. The receipt includes typed organ IDs, a provisional
parent attachment inferred from the nearest earlier stem/bark/branch segment,
metric anchor/attachment distance, a SHA-256 of the organ records and an explicit
`attachment_status` that does **not** claim developmental botanical lineage.

```sh
go run ./wildflowers -preset wildflowers/presets/quercus_robur.json \
  -out /tmp/oak.glb -organs /tmp/oak.organs.json
```

The graph is validated against actual generated mesh lengths: no missing
vertices/indices, overlapping ranges, zero-length organ, invalid parent order,
or disconnected forced parent is admitted. This sidecar is optional and leaves
existing GLB bytes unchanged for identical presets. IDs are stable for an
identical preset/seed/software revision, **not** guaranteed across stages or
arbitrary topology edits. The next gate is explicit stable developmental organ
paths (plant→axis→phytomer→leaf/inflorescence) with birth/death semantics.

## Native CI dependency acquisition hold

The existing OpenAlea/Blender workflow pixel oracle is pinned to **Ubuntu's
Blender 4.0.2**. `tools/install_blender_apt.sh` is a fail-closed, Ubuntu
24.04-only acquisition candidate that skips Azure `apt-mirrors.txt`, keeps
Ubuntu repository signatures, tries two explicit upstream mirrors with bounded
update/download/install phases, and verifies Blender 4.0.2+NumPy+Xvfb before
allowing original raster/pixel checks. Offline syntax/negative controls are in
`tools/test_install_blender_apt.sh`.

This is a **corrective candidate, not a proven CI fix** until the original
native workflows complete successfully and original pixel baselines pass.
No reference-image or validator-threshold relaxation is authorized.

## W05 generator-source organ paths and developmental crosswalks

The v2 organ receipt extends geometry-bound records with `generator_scope` and
`semantic_key`: a deterministic scope/organ-type/material/ordinal path. This is
**source-generated continuity for matching code revision, seed and immutable
parameters**, not a biologically persistent organ identifier. The original
local numeric `id` remains a mesh-index enumeration, not a stable ID. Semantic
paths are scoped to individual plant stems, canes and recursive tree branches,
so new reproductive geometry on one stem does not rename later stems' leaves.

Use `-lineage /tmp/maize.lineage.json -from-stage 0.4` on the *mature* maize
preset to compare explicit source organ keys with the earlier developmental
snapshot. Outputs list `persistent`, `introduced`, and `disappeared` keys and
reject changed seed/species/immutable parameters, duplicate keys, unscoped
geometry and reversed stages. Each output explicitly reports unknown biological
identity and unqualified visual validation; it is **not** a continuous growth
simulation, generalized leaf tracking, or observed phenology.

## W05 bounded physical wind qualification — not GLB motion admission

`-wind-probe /tmp/maize.wind.json` produces a separate fixed-step trace for
one synthetic effective lateral mass, a damped spring, and quadratic aerodynamic
drag. It does **not** yet drive the four exported GLB wind morph targets.
Values are **unmeasured** family examples, not botanical stiffness/drag data.
The simulation rejects nonfinite, unstable, extreme, over-budget, or nonintegral
step inputs. Oracle `tests/validate_lineage_wind.py` reads sidecars only using
the Python standard library to independently qualify structure and energy
calculation. It does not assert plant-specific physics or rendered correctness.

Example from `tropical-fauna-flora/`:

```bash
go run ./wildflowers -preset wildflowers/presets/zea_mays.json \
  -out /tmp/maize.glb -organs /tmp/maize.organs.json \
  -lineage /tmp/maize.lineage.json -from-stage 0.4 \
  -wind-probe /tmp/maize.wind.json
```

## W06 experimental physics-to-GLB bridge and developmental parent audit

The default `-wind-driver harmonic` remains unchanged. The historical v0.2
binary SHA-256 for maize is locked by `TestLegacyMaizeByteContractUnchanged`;
all twelve expanded v0.2 GLBs have additionally passed independent byte
comparisons against the source archive.

An **opt-in** path exports directly sampled reduced-order wind motion into the
actual glTF 2.0 `weights` animation. It uses the same four mesh morph targets,
but drives only their lateral positive/negative pair. It does **not** add leaf
flutter, multiple bending modes, collisions or a second physical degree of
freedom. The time series is one-shot and deliberately **not forced to have a
periodic seam**. It must not be looped as if it were periodic without a new
qualification. All stiffness, mass and aerodynamic parameters are artificial,
not measured material coefficients.

From the `tropical-fauna-flora/` module root:

```bash
go run ./wildflowers -preset wildflowers/presets/zea_mays.json \
  -out out/zea_mays.physical.glb \
  -wind-driver spring-drag -wind-probe out/zea_mays.wind.json \
  -lineage out/zea_mays.lineage.json \
  -parent-audit out/zea_mays.parents.json
python3 wildflowers/tests/validate_physical_wind_glb.py \
  --glb out/zea_mays.physical.glb --wind out/zea_mays.wind.json
python3 wildflowers/tests/redteam_physical_glb.py \
  --glb out/zea_mays.physical.glb --wind out/zea_mays.wind.json
```

`parent-audit` checks authored semantic keys across early/later generated stages
and reports cross-stage changes in *heuristically inferred geometric* parent
axes. Unresolved attachments are counted, not claimed verified. The
`generator_scope_contract` makes this source path naming version explicit;
cross-generator semantic continuity, real botanical parentage, senescence,
root systems and leaf abscission remain **unqualified**. `parent-audit` requires
an early `-from-stage` lower than the active positive `growth_stage`.

The independent read-only GLB oracle parses binary animation samplers,
weights, geometry and basal vertices. It rejects tampered wind receipts,
modified animation bytes, nonfinite morph deltas and fraudulent loop metadata.
The four-species GIF is a low-fidelity flat-shaded software preview from
serialized GLB morphs, **not** a Blender render or species-validation witness.

Repository policy: store only Go/validation source, presets, DLE receipts and
small machine-readable manifests in Git. Generated GLBs, wind JSON traces and
previews belong in the verified large-binary Drive corpus. Keep existing PR
#13 draft, source parent #4 and protected release/scientific/rights holds.

## W07 independent multi-axis wind and organ-level LOD experiments

The W06 historical `-wind-driver harmonic` and `spring-drag` exports are unchanged by default. New **opt-in** `-wind-driver spring-drag-multimode` produces glTF 2.0 GLBs with **six** morph targets: positive/negative X bending, positive/negative Z bending, and positive/negative local foliage deformation. The three profiles are independent one-dimensional synthetic damped-mass/drag oscillators, not coupled finite-element wind or botanical measurements; foliage shape is kinematically anchored at each generated leaf base. The 49 animation keyframes sample three independent 481-step traces over four seconds, with `loop=false`, and are decoded by a separate Python standard-library validator. The animated GLB geometry and source traces are checked together.

`-lod` levels 0, 1, 2, and 3 select full detail or deterministic whole-organ foliage thinning (approximately 1/2, 1/4, 1/8 leaf retention); stems and reproductive geometry remain. Geometry indices, source semantic keys and parent references are recomputed and revalidated, not simply reindexed arbitrarily. `-lod-receipt` records original and retained triangle/organ counts. **This is an experimental rendering-cost primitive, not a visually qualified/impostor or distance-aware LOD system.** Simplified foliage can be too sparse and is not ready for botanical claims. Morph target normal updates, shade/wind attenuation, organ collisions, detailed branch torsion and source-observed photogrammetric fidelity remain HOLD.

Example from module root:

```bash
go run ./wildflowers -preset wildflowers/presets/zea_mays.json \
  -out /tmp/maize_multi_lod2.glb \
  -wind-driver spring-drag-multimode \
  -multi-wind /tmp/maize_multi.wind.json \
  -lod 2 -lod-receipt /tmp/maize_lod2.json
python3 wildflowers/tests/validate_multimode_glb.py \
  --glb /tmp/maize_multi_lod2.glb --wind /tmp/maize_multi.wind.json
python3 wildflowers/tests/redteam_multimode.py \
  --glb /tmp/maize_multi_lod2.glb --wind /tmp/maize_multi.wind.json
```

The independent binary validator checks all six serialized weights against the supplied source sample clocks and displacement values, all six morph targets, nonfoliage isolation, signed leaf target symmetry, finite geometry and near-ground anchoring; the adversarial tests verify source/GLB drift, species mismatch, nonfinite leaf geometry and false looping. A source receipt is **not** an independently calibrated wind measurement. Per-species test data, output hashes and performance budgets must be preserved in the owning flora DLE. Existing GitHub Actions Blender 4.0.2 acquisition correction remains **native-unqualified** until exact-commit CI and canonical PNG oracles pass. Do not merge or release on the strength of this local proof alone.
