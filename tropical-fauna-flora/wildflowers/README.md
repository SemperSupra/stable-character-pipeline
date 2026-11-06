# Baden-Württemberg parametric wildflower workcell — v0.1

Independent public-safe research prototype for the **Stable Character Pipeline**. Synthetic geometry is generated from editable species presets using the Go standard library; no third-party meshes, copyrighted photos, or protected-source data were copied into the generator.

## Delivered

| Species preset (provisional where marked) | Editable morphology | Output |
| --- | --- | --- |
| Achillea millefolium / Gewöhnliche Schafgarbe | Multi-stems, feathery compound leaves, composite flower clusters | `outputs/achillea_millefolium.glb` |
| Centaurea jacea / Wiesen-Flockenblume **provisional species match** | Stem count, lanceolate leaves, bract and radial florets | `outputs/centaurea_jacea.glb` |
| Convolvulus arvensis / Acker-Winde | Low radial vine, arrowhead leaves, trumpet flowers | `outputs/convolvulus_arvensis.glb` |
| Tripleurospermum inodorum / Geruchlose Kamille **provisional species match** | Branched stems, narrow leaves, composite capitulum | `outputs/tripleurospermum_inodorum.glb` |

Every GLB has four morph targets and a looping 4-second glTF 2.0 `weights` animation. **This is procedural wind displacement, not a measured wind field or physically validated XPBD simulation.** Base plants are synthetic illustrations; morphology is not yet botanically qualified against photographs. The previews show the *actual exported morph targets* decoded from GLB, not a separate wind approximation.

## Quick start

Extract the ZIP. On Windows PowerShell 5.1:

```powershell
.\flora-gen-windows-amd64.exe -preset .\presets\achillea_millefolium.json -out .\yarrow_variant.glb
```

On Apple Silicon macOS:

```bash
chmod +x ./flora-gen-darwin-arm64
./flora-gen-darwin-arm64 -preset presets/convolvulus_arvensis.json -out bindweed_variant.glb
```

On Linux x86-64:

```bash
chmod +x ./flora-gen-linux-amd64
./flora-gen-linux-amd64 -preset presets/tripleurospermum_inodorum.json -out mayweed_variant.glb
```

All four examples use the same generator. Modify `seed`, `height_m`, `stems`, `leaf_pairs`, `petals`, `flower_radius_m`, `wind_amplitude_m`, `wind_period_s`, and `colors_rgba` in each JSON preset, then regenerate to obtain a new deterministic specimen. Not every parameter is meaningful for every template (e.g. `heads_per_stem` applies only to yarrow). **Do not expect arbitrary genotype-to-species morphing**: this is a family of structurally distinct, parameterized morphology templates.

## Build and tests

```bash
go test -v ./src
go vet ./src
go build -o flora-gen ./src
python3 tests/inspect_animate.py
```

Python rendering/independent validation requires `numpy` and `Pillow` and is **not** required to generate GLBs. `tests/render_previews.py` is an optional trimesh+matplotlib static inspection script. `outputs/validation_report.json` is the recorded result of a separate binary glTF reader. The included binaries were built with Go using no external Go modules. Scripts have no network access, package-manager side effects, or source downloads.

## Engineering scope and known defects

- Approximate ecology and plant morphology: no botanical image fit, organ growth model, flowering phenology, seasonal material response or photogrammetric reconstruction.
- Morph target wind is a **kinematic reduced-order deformation**: no cloth/XPBD mesh solution, leaf/stem contact, branching torsion, bending stiffness calibration or atmospheric gust field.
- The bindweed is radially sprawling rather than actually twining around a support, and its funnel geometry is not oriented to measured flower normals.
- Plant geometry lacks texture UVs and scanned PBR materials; LOD generation and mesh budgeting should follow once species validation has begun.
- The source presets describe **species hypotheses**, not authoritative identifications of the user's photographs.
- Approximate GLB vertex normals are carried from the rest mesh; for production, deform/correct normals or compute them in renderer.
- The prototype does not yet import, vendor or adapt the external dynamic-plant repositories listed below.

## Source reuse adapters proposed

Upstream candidates were investigated in public repositories; do not conflate their source with this original prototype:

- [Godot Plant Generator](https://github.com/AndreasBurbach/godot-plant-generator): genome+seed, staged growth, skeleton IDs, GLB. Proposed branch/stem generator adapter.
- [Inkwell WebGPU Flowers](https://github.com/siliconjungle/inkwell-webgpu-flowers): GPU placement, LOD and wind. Proposed meadow scattering and distant crowd adapter.
- [Digital Peony](https://github.com/LewisOrton/digital-peony): GPU XPBD petals. Proposed near-field hero flower motion adapter.
- [SeedThree](https://github.com/SkyeShark/SeedThree): species presets, wind and glTF. Source inspection only; tree-oriented alpha, not yet an accurate wildflower species generator.

Separate license checks and pin exact upstream source commits prior to integration. No third-party license coverage or source equivalence is implied by this prototype.

## DLE/custody boundary

- **Git/source:** code, species presets, test harness, upstream license references, source receipts, negative findings, and handoff.
- **Binary deliverables:** four sample GLBs, preview GIF/PNG and validation JSON; ideally stored in a private Drive `Stable Character Pipeline` output area with SHA256 links, not in public Git.
- **Protected:** no user-supplied photos or original protected character sources are placed in this package. No downstream merge, release, CPE, or protected-source promotion.

## Next executable baton

1. Qualify one exact upstream source commit/license and build a thin adapter for plant-organ skeletons; do **not** vendor the repository wholesale.
2. Fit species morphology to independent, permissioned reference silhouettes and leaf/flower measurements. Admit `Centaurea` and `Tripleurospermum` species only after corroborating detail.
3. Add section-wise bend and torsional degrees of freedom, wind/drag stochastic forcing, and XPBD only for hero petals/leaf contact; test against still-air, gust, branch continuity, root locks, and loop seams.
4. Support EN/DE/TH species-label metadata, LODs, morphology time series and flowering stages. Preserve deterministic seed, per-organ IDs, provenance, and end-to-end validation.

First independent test REDs: (1) tiny nonzero floating point weights at wind loop seam; corrected by exact zero endpoints. (2) unanchored bindweed root geometry; corrected by setting basal center to ground plane. All five Go test groups and independent GLB structure/wind tests now pass; visual/botanical quality is held.

---

## v0.2 architecture extension — grasses, grains, vines, shrubs and trees (2026-11-06)

The v0.1 four-wildflower files and their original parameter meanings are preserved. v0.2 adds **10 independent geometry templates** and **12 seed-pinned, individually editable botanical *illustrations***. These are not species-verified photogrammetric reconstructions. All exports remain original source and synthetic meshes; no third-party donor mesh has been incorporated.

| Template | Example preset | What varies | Modeling hold |
| --- | --- | --- | --- |
| `grass` | meadow fescue | tuft stem count, blade width/height, panicle state | simplified blades, no species-scale inflorescence |
| `wheat` | wheat, rye | tillers, leaves, spikelets, awns | grains stylized, no measured allometry |
| `oats` | oats | tillers, rachis, panicle branch count and tilt | simplified panicle, gravity not solved |
| `maize` | corn | stems, phyllotaxy, internodes, tassel, cob/husk | no real ligule/sheath, kernels abstracted |
| `sunflower` | sunflower | head/ray floret count, radius, stage | disk and florets stylized, no heliotropism |
| `grapevine` | grape | trunk/cordons, canes, 3-lobe approximated leaves, berry count | no actual grape morphology, lattice support/collision |
| `bamboo` | golden bamboo | culm clusters, segmented internodes, nodes, branch leaves | no rhizome spreading, hollow section mesh |
| `shrub` | hazel | multi-stem crown radius, branches, leaf size, fruits | fruit type generic, foliage sparse |
| `tree` | oak, apple | taper, tier count, recursive branching, leaf scale | highly regular procedural crown, no accurate species organ morphology |
| `conifer` | spruce | whorls, tapering crown, needle sprays | simplistic branch architecture and needle organization |

The other four v0.1 templates are `yarrow`, `knapweed`, `bindweed`, and `mayweed`. A single source file does NOT imply a species is morphable into another architecture without changing the template.

### Parameter contract

All presets specify `template`, `seed`, `height_m`, `stems`, `leaf_pairs`, `flower_radius_m`, `wind_amplitude_m`, `wind_period_s`, and materials. Expanded templates additionally require `crown_radius_m`, `stem_radius_m`, `branch_count`, `branch_levels`, `internodes`, `ear_count`, `fruit_count`, `awn_length_m`, `leaf_scale` and `growth_stage` in (0,1]. For crop species, immature stages disable reproductive geometry; the **growth stage is a single discrete source snapshot**, NOT time-evolved organ identity or validated phenology. Labels can carry English, German, and Thai independently from species IDs. Repeated species ID + parameter bytes + seed yields a repeatable GLB byte sequence in the tested Go runtime.

**Dynamic representation:** four separate morph-target displacement fields + 13 recorded keyframes, four-second looping glTF weights animation. It does not model real wind loading, elasticity, torsion, aerodynamics or growth-rate kinetics. Roots remain approximately immobile; some small radial tube rings penetrate the surface by 1–12 mm, retained as visible geometric holds. Normals are rest-pose normals and should be recomputed during deformation in a production renderer.

### Build and generation

```bash
cd flora-dynamic-prototype
go test -race -count=1 ./src
go vet ./src
go build -o flora-gen ./src
./flora-gen -preset presets/zea_mays.json -out outputs-v02/zea_mays.glb
./flora-gen -preset presets/quercus_robur.json -out outputs-v02/quercus_robur.glb
python3 tests/validate_extended.py
python3 tests/render_extended.py
```

PowerShell 5.1: use `flora-gen-windows-amd64.exe -preset .\presets\triticum_aestivum.json -out .\wheat.glb`. Every exported species is independent; scenes/fields can instance them as many times as needed. Tests use local CPU only; `trimesh` and `Pillow` are optional for preview, and Python+NumPy+Pillow for the independent binary inspector. The Go generator has no third-party dependencies.

### Three-audience interface

- **Human:** edit JSON presets (EN/DE/TH labels), regenerate in CLI, inspect contact sheet and GIF; no authoring GUI yet.
- **Automation:** deterministic Go CLI, strict input bounds, glTF output and SHA manifest; no hidden environment state.
- **Agents:** source-of-truth species/family/trait JSON, file-level hashes, inspectable GLB extras and validation JSON; proposals remain untrusted until independent checks.

### Reuse research, not imported

- OpenAlea [ADEL](https://github.com/openalea/adel), **CeCILL-C**, models maize/wheat shoot architecture; [ArchiCrop](https://github.com/openalea/ArchiCrop) provides crop-scale-constrained 3D+t cereal architecture. These are good references for serious cereal growth but are not incorporated here.
- OpenAlea [HydroShoot](https://github.com/openalea/hydroshoot) models grape hydraulic/energy/gas exchange for fixed shoot architecture, NOT continuous grape growth; avoid claiming otherwise.
- [Godot Plant Generator](https://github.com/AndreasBurbach/godot-plant-generator) includes grass, bamboo, hazel, deciduous/conifer presets, parametric skeletons and GLB. Qualify exact commit, tests, and per-source rights before reusing source.
- Public DLE [Flora/Fauna #5](https://github.com/SemperSupra/stable-character-pipeline/issues/5), existing flora leaf PR [#13](https://github.com/SemperSupra/stable-character-pipeline/pull/13); human and Shetland PRs remain separate and held.

### Next quality gates

1. Orthogonally validate mesh and organ quality for each architecture: maize phyllotaxy/ears, wheat/oat spikelets and panicles, grape trained canes/tendrils/bunches, bamboo rhizomes, shrubs and tree branching allometry. Source-photo-backed measurements must be distinct from simulator expectations.
2. Introduce stable organ IDs, branch-skeleton parent edges, per-organ material channels and geometric LOD; currently output is flat material-group mesh with no durable organ graph.
3. Parameterize stiffness/mass/drag and separate rare bone-/XPBD-based hero motion from field-scale GPU vertex wind. Qualify in actual renderer, not only GLB structural validator.
4. Add growth-time snapshots as independent states with organ continuity and phenology; tie to temperature/water/soil/light observations only after experimental qualification.
5. Run a targeted CI test with correct path gate. Avoid broad workflow churn and changes to previous completed stack. Hold merges/releases/CPE until owner review.
