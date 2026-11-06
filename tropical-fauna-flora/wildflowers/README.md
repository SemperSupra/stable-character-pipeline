# Original parametric wildflower motion proof (W0)

Additive, isolated companion to public Flora/Fauna DLE #5 and candidate OpenAlea qualification PR #13. This Go stdlib generator authors **new synthetic geometry**, not copies of upstream mesh assets. It produces four editable botanical-illustration specimens with 4 glTF morph targets and a 4-second looping wind clip.

Species presets: Achillea millefolium (yarrow), Centaurea jacea (knapweed, provisional species ID), Convolvulus arvensis (bindweed), and Tripleurospermum inodorum (mayweed, provisional species ID). Parameters include seed, height, stems, heads, petals, leaf pairs, flower radius/color, wind amplitude and period. Stems/leaves/flower geometry are generated from separate templates; color and motion parameters do not alter botanical identity by themselves.

## Source-only development

From `tropical-fauna-flora/`:

```bash
go test ./wildflowers -v
go vet ./wildflowers
go build -o wildflowers/flora-gen ./wildflowers
./wildflowers/flora-gen -preset wildflowers/presets/achillea_millefolium.json -out /tmp/yarrow.glb
```

No extra Go dependencies; no network calls or third-party meshes. The optional independent binary glTF reader/raster preview under `tools/inspect_animate.py` uses NumPy/Pillow and expects generated GLBs in `wildflowers/outputs/` (Git-ignored). The generated binary outputs, preview and evidence remain in private Drive: [W0 generated media](https://drive.google.com/file/d/1RUFIwlkLnqWqWkDdEc_VSU3gka8KlWEU/view?usp=drivesdk). Local release bundle SHA256 `7a75e57edbe5b1bfb58b1e6f18690f65042e27ebbbf591cdac08631cdb82fc4e`; full-byte remote SHA validation still pending.

## Holds and falsification

Go unit tests PASS including exact GLB header and bytes, four valid morph targets, first/last key weights exactly zero, near-root motion small, seed determinism/difference, all four templates, invalid preset failure. An independent GLB reader PASS on four actual exports (61,488 vertices and 25,424 triangles total). Prior first REDs: nonzero last-frame floating point seam and unanchored bindweed vine root, both fixed without weaker checks.

**Not qualified:** botanical accuracy against source photos, real vegetation organs and growth, leaf-stem stiffness, XPBD physics, photometric materials or animation normal updates, branching/climbing correctness, performance/LOD, rights of external sources, real CPU-native Actions run for this new source, or downstream scene integration. No human/protected media, runner secrets, third-party vendor source, or binary assets in Git. No merge/release/CPE promotion.

## Integration strategy

Keep F1 OpenAlea L-Py/PlantGL separately qualified. Proposed optional licensed upstream adapters: Godot Plant Generator for DNA+organ skeleton, Inkwell WebGPU Flowers for GPU meadow scattering/LOD, and Digital Peony for near-field XPBD petals; no source vendored or claims of direct interoperability. Next: decide whether to integrate this additive source on the current flora PR branch after exact-head review, run bounded native public Go CI, crosswalk organ IDs, and compare species morphology to photo silhouettes. DLE #5 is the owner; parent #4 remains frozen.
