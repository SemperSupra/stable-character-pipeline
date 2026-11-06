# Hair / fur prior art and composable engineering decision (2026-11-06)

**Owner:** Shetland DLE #293; hair #329; integrated #330 deliberately frozen on older qualified hair source. **Status: architecture research + source-qualified candidates ONLY; no external runtime admitted.**

## Multilingual concept sweep and source confidence

Search channels: English (hair dynamics, rods, grooms), German (Haarsimulation/Fell/Haare), French (simulation fourrure/cheveux/mèches), Simplified Chinese (毛发动力学/毛发仿真), Japanese (毛髪/揺れ物), Thai (จำลองขนสัตว์/ผม), and Spanish (simulación pelo/pelaje). Primary upstream papers, developer manuals, GitHub licenses and release notes outrank translated commentary. Chinese and French official Blender manuals confirm the same XPBD model; no independently validated Thai/Japanese physics primitive outperformed those upstream implementations in this sweep. Absence of indexed examples is NOT proof of absent research. URL evidence anchored below; no third-party demo geometry/data copied or admitted.

### Existing engine/library alternatives (not a popularity ranking)

| Candidate | Verifiable primitive / role | License & boundary | Decision |
|---|---|---|---|
| **Blender 5.2.3 LTS** Geometry Nodes Hair Dynamics (released 2026-07-14; 5.2.3 2026-10-22) | XPBD Cosserat hair rods, animated surface/rest attachment, stretch/shear/rotation constraints, gravity, collision effectors, solver residual; optional full-featured native authoring | Blender GPL software; hair-node feature EXPERIMENTAL and internal node API may change. Official release https://www.blender.org/releases/5-2/ and https://developer.blender.org/docs/features/nodes/xpbd_simulation/ | **FIRST candidate** in independent read-only 5.2.x public runner lane. Existing production 4.5.15 untouched; no silent upgrade. |
| **AMD TressFX 4.1** | MIT GPU hair/fur simulation, skeletal skinning, LOD, rendering, SDF colliders; DirectX12/Vulkan | MIT code https://github.com/GPUOpen-Effects/TressFX, https://gpuopen.com/tressfx/; bundled sample models separate rights | **SECOND** for true runtime hair after provenance, driver and Vulkan/CPU fallback study. Do NOT vendor demos automatically. |
| **PositionBasedDynamics / pyPBD** | MIT C++ XPBD/PBD, orientation-based Cosserat rods, bend/twist and stretch/shear, cubic SDF, deterministic scenarios | MIT https://github.com/InteractiveComputerGraphics/PositionBasedDynamics, authoritative LICENSE | **SECOND** for isolated C++ numerical reference + hostile analytical fixtures, not drop-in Godot/Blender renderer. |
| **Blender GN hair generation/shading** | Sparse guide -> interpolated follower curves, scatter/clump/frizz/curl, Principled Hair BSDF (melanin/roughness) | Blender GPL engine, original CC0 Fur Examples https://www.blender.org/download/demo-files/ (check each asset) | **FIRST** for groom style, strand detail, honest close-ups and season/density; preserve procedural original source curves separate from baked GLB. |
| **OpenUSD UsdGeomBasisCurves** | Canonical high-volume hair rest and animated curve geometry with widths, interpolation, time samples, primvars | OpenUSD open spec https://openusd.org/release/api/class_usd_geom_basis_curves.html | **FIRST** authoritative source/export interop; glTF derived animation is not the source curve model. |
| **TressFX-Godot** | MIT Godot GDExtension TressFX port, root skinning, SDF, Blender curve exporter; helpful tests and performance notes | MIT source https://github.com/ismailivanov/TressFX-Godot ; needs Godot 4.7/Vulkan; bundled demo assets DIFFERENT rights, port notes frame-rate-sensitive sim | **CONDITIONAL** for downstream real-time Godot, not generic native GLB feature. |
| **Unity Demo Team Hair** | Strand/volume GPU simulation, Alembic curves, hierarchical LOD | **Unity Companion License**, NOT permissive MIT code https://github.com/Unity-Technologies/com.unity.demoteam.hair/blob/master/LICENSE.md | **REFERENCE ONLY** for design, never republish or embed outside terms. |
| **PyElastica / discrete elastic rods** | Cosserat rod mechanics + stretching/bending/twist physical baseline; DER experimental reference | https://github.com/GazzolaLab/PyElastica ; specific license/subdependencies require qualification before code reuse. https://github.com/millag/DiscreteElasticRods | **RESEARCH** numerical verification; not a replacement renderer. |
| **MonoHair (CVPR 2024)** | Photo/video driven human hair strand reconstruction (high-fidelity scalp/hair), not a physics solver | https://github.com/KeyuWu-CS/MonoHair ; model/training rights separate; human model assumptions not automatically equine | **RECONSTRUCTION research**, no unqualified person/pony-transfer assumptions. |
| **NVIDIA Warp** | Apache-2.0 accelerated simulation framework; GPU CUDA ecosystem, not itself packaged groom | https://github.com/NVIDIA/warp ; separately licensed NVIDIA libmathdx in distribution | **OPTIONAL engine adapter** for sovereign CUDA future, not required for $0 CPU qualification. |
| **Houdini Hair & Fur** | Industry groom pattern: guide groom, generate, deform, simulation + painted attributes | https://www.sidefx.com/docs/houdini/fur/index.html ; proprietary application | **PRIOR ART reference**, not an open runtime dependency. |

Primary Blender developer source: https://code.blender.org/2026/07/geometry-nodes-physics/ ; experimental node details: https://developer.blender.org/docs/features/nodes/xpbd_solver/ ; Chinese manual https://docs.blender.org/manual/zh-hans/5.4/modeling/geometry_nodes/simulation/hair_dynamics.html ; French manual https://docs.blender.org/manual/fr/5.2/modeling/geometry_nodes/simulation/hair_dynamics.html ; Spanish https://docs.blender.org/manual/es/latest/modeling/geometry_nodes/simulation/xpbd_solver.html . This survey intentionally avoids pretending every result is independently maintained or licensed for commercial integration.

## Reusable primitives — separate data from solvers and renderers

1. **Identity/fibers:** stable `groom_id`, `follicle_id`, `group_id`, immutable canonical skin-triangle barycentric coordinates, rest curve, per-segment material frame/quaternion, widths/taper; measured fiber length/diameter, melanin/pheomelanin/reflectance, guard-vs-undercoat class, random seed; no stochastic resampling each animation frame.
2. **Anatomy and anchors:** rest source mesh + inverse bind matrices + time-varying root surface position/normal/tangent; bone/skin weights and surface motion velocities. Separate the pony's fixed identity from time/season-specific pelt.
3. **Structure:** per-curve centerline and cross-section; stretch/shear, bend/twist, anisotropic stiffness/curvature/torsion; damping, mass, wind drag, gravity and inertia. Prefer orientation-based Cosserat/XPBD for long hair; stiff short fur rides deformed surface with lightweight procedural bending.
4. **Sparse dynamics:** independent guide groups by region and owning bone, limited solver steps, root pinning and continuous rest frame; follower/interpolated render hairs inherit guide deformation without multiplying physics cost.
5. **Collision:** skinned body surface SDF/BVH with a **signed/closed-mesh** validity gate, correct shell/fur offset, cloth/tack/cross-strand interactions, swept contacts and friction. Triangle overlap and nearest distance are early *falsifiers*, not proof of nonpenetration or pressure.
6. **Appearance/LOD:** root-to-tip thickness and melanin/roughness variation, clumps/flyaways, frizz/curl and wetness; hair curves and strand shader for high-quality Blender, lightweight generated cards/mesh/skeletal morphs for GLB, and validated per-distance LOD. Control shader alpha sorting/transparency without claiming GLB can simulate XPBD.
7. **Lifecycle:** region-specific seasonal length/density/guard-undercoat ratio, growth/shedding, clipping, age/breed state, stable follicle identity for persistent hairs, explicit birth/death of shedding fibers; separated character identity, timestamped phenotype and groom style.

## Required invariants / hostile gates

- **Structural:** nonnegative finite, SI-unit geometry; unique stable follicle IDs; barycentric+skin-weight sums = 1 within explicit tolerance; valid source triangle/bone; root lies on evaluated target surface within a measured bound; unchanged follicle identity over frames.
- **Material and numeric:** positive segment length/radius; tapered finite tips; controlled maximum stretch and quaternion normalization; fixed/mapped time steps, bounded mass/damping and a finite solver residual. Candidate should not be accepted solely because a hard displacement clip prevents visible instability; report fractional clipping and source-mesh penetration by region.
- **Contact:** root/first-quarter near-skin contact is expected; deeper crosses are separate; detect exact distal and tip-zone crossings as well as signed penetration, dynamic sweeps, self-intersection, cloth interference. Test positive/negative/near-tangent/rapid motion and articulated tail.
- **Temporal:** first/last poses, no frame swap/teleport, continuous velocity and acceleration, physical lag and settling as wind stops; seasonal state must not randomly regenerate textures or follicle locations frame-to-frame.
- **Scientific:** validation performance (false alarms/omissions, regression across frames, runtime and hardware) is versioned; quantitative RED and unknown are distinct from CI/source-build success. Visual multiple views and independent acceptance always required.
- **Provenance/access:** original synthetic public materials only on public $0 runner; reference/personal protected media remain under private Drive/authorized RDTE, with binary SHA ledger and source-asset ownership. License+notice gate per imported source/dependency/sample. Never import an engine-specific sample model as our pony merely because library code is permissive.

## Red/blue decision and release gates

**RED:** Stay pinned to Blender 4.5.15 and keep patching our custom strips => existing 88.8% clamp saturation and full 48f mane/forelock tip-zone crossings likely persist; jumping directly to experimental Blender 5.2 node may break reproducibility, silently reconfigure sculpt/binds or violate cost limits; assuming TressFX vendor demo art is MIT is unsafe; copying Unity source under Companion License into generic engine is risky; USD curves are not supported by raw glTF strands; native green is not biology green.

**BLUE:** Introduce an isolated SHADOW backend that identifies exact Blender 5.2.3 release with SHA256, validates presence of experimental XPBD API and native hair-curve primitives on tiny synthetic source, emits immutable JSON capability receipt. No source replace/production upgrade. Qualify an explicit source-follicle/curve adapter against original 30j, then staged A/B: identical source baseline vs 5.2 physics, compare 48f root error, rod length, contact, residual, clamp percentage, image similarity to reference on authorized side, CPU/RAM/runtime; require independent engineer+visual red team before default switch. Evaluate MIT TressFX only if a real-time player requires native GPU support.

**Stop rules:** Experimental capability absent => keep existing 4.5 path; capability present but physics not yet executed => no solver admission; simulation controls pass but visual/contact science RED => retain frozen #330 and scientifically rejected variants for audit; only accepted source and signed rights can progress into main/owner release.

## Interfaces for three audiences

- Human: Blender groom/curve authoring and actual face/side/rear animated review + an evidence matrix with explanations.
- Automation: source-bound public GitHub Actions (separate version-pinned capability/contract/native A/B jobs), deterministic JSON receipts, SHA checks, distinct SOURCE/ENGINEERING/SCIENTIFIC outcomes.
- Agent: machine-readable manifest and schema, exact `owner/ref/head`, finite normalized parameters, simulation choices/assumptions, gate result, next runnable baton in DLE. Design remains independent of Blender/Unreal/Unity and optional GPU vendor library.

## Next committed independent workcells

A. Offline independent source-groom contract + hostile inputs, preserving stable hair identity and source/frame invariants, pure Go tooling if executable validator built.
B. Blender 5.2.3 SHA-verified sandbox capability probe (NO production source upgrade or claim of real hair simulation).
C. Backend A/B only after A+B pass: native 48f animated root/curve sim, exact comparison vs frozen #330, collision/clamp/visual and GPU/CPU resource evidence. Existing #329 4.5 source remains canonical pending owner adoption; #312 remains sole repository hygiene owner.
