# R009 original geometric costume prototypes — Aster and Juniper

Status: **technical prototypes only**, not visually accepted, physically simulated, release-approved or ready to transfer automatically to real-source characters.

## Scope

Four project-original pattern archetypes reflecting general wardrobe families discussed for Lucy Heartfilia references, **without copying third-party garment models or textures**: `classic_adventurer`, `casual`, `tournament_bodice`, `high_collar_adventurer`.

The deterministic stdlib Python tool `costume_garment_v1.py` generates eight original-source fitted character/outfit instances (four combined 35-joint GLBs with both Aster and Juniper). Each variant retains exact original body/hair/footwear nodes and both preexisting skeletons and source animation. It excludes the original jacket, trouser and alternate garments from the visible scene graph without deleting original source data, and adds separate source-authored skinned top, skirt, belt and, for the high-collar variant, collar nodes. No authoring-time dependency on Blender or third-party meshes.

## Source and contract

- Authoritative built input: owner-private Drive Aster/Juniper master in *R009 Aster-Juniper Modular Wardrobe — 2026-11-05*, Google Drive file `11rRDgRF8j5OQvgf4s4eQs1qj0aXDhG3X`.
- Source bytes SHA-256 `470ec8fc159912e8ad2e30733a00c09785e11c1275c26936774690fe2807727b`. The importer requires an **exact** byte match, original synthetic provenance, 2 rigs × 35 joints, existing body, hair and footwear nodes; rejects substitutions.
- Open rings, double-sided material, simple linear skin weighting. The procedural skirt currently moves rigidly with the pelvis; genuine cloth motion, fabric strain, contact, swing, wrinkles, and colliders are **not implemented**.
- Editable morphology fitting parameters: `chest_scale`, `waist_scale`, `hip_scale`, `ease_m`, with bounds and non-finite/boolean rejection; these are **engineering adjustments**, not reliable anthropometric measurements.
- Output variants are standalone GLBs with reachable garment nodes. Original bytes are preserved in existing source node/mesh/skin/animation tables and the binary prefix. Unreferenced source jackets and trousers remain in binary for reversible custody. Do not advertise export compaction.

## Reproduce on an admitted local workcell

```sh
cd qualification/parametric_humans
python3 -m unittest -v test_costume_garment_v1
mkdir -p /tmp/r009-original-costumes
python3 costume_garment_v1.py --source /PRIVATE_OR_CUSTODY/master.glb --out-dir /tmp/r009-original-costumes
```

Tests: 6 available, five source-free; one extra exact-source test runs when `SCP_R009_WARDROBE_MASTER` points to the exact master. Strictly stdlib module for the source generator. Independent QA imported each GLB with `trimesh` and checked glTF table/source-prefix invariants. VTK three-dimensional static previews are diagnostics only, not a Blender-native test. Existing original puppet has visible shoulder/arm gaps.

## Reuse qualification lanes

1. **Aster / Juniper**: source-bound generated and tested. Native Blender 72-frame, multi-view garment deformation plus collision classification and human visual approval remain pending.
2. **Rocketbox F01/F02**: 80-bone rig; create explicit rig-rest and proportions adapter, verify exact MIT provenance, independently test fit. No supported wardrobe variant output yet.
3. **Alison, florah, Alina, Mei**: private-source admission/rights and source-format/bone maps separately required; no code should silently copy private meshes into the public original-only workflow.
4. **Naomi**: incomplete source scan body and foot/rig reconstruction; fit only against a marked **opaque technical proxy** until body/rig review, not as recovered hidden anatomy.

## Storage and provenance

Code, tests, documentation and small machine receipts belong in owning Git PR/DLE. Generated GLBs, preview images and large source-bound reproducibility ZIP belong in the existing owner-private Drive wardrobe folder with SHA-256 records and readback. No additional PRs, no private Actions minutes, and no merge/release/CPE. Restore first failures and do not close scientific holds based on synthetic geometry PASS.
