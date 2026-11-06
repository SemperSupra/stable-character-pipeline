
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
