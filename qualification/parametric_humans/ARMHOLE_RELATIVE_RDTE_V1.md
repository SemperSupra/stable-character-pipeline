# R009 — actor-specific armhole corrective trial (2026-11-07)

**Status: CPU technical *relative* improvement for Juniper only; garment collision / realism / release NOT ACCEPTED.** No third-party scans, private Naomi/Alison source, external textures, or protected vendor models used. Source is original fictional Aster/Juniper and permitted, source-pinned MakeHuman CC0 body geometry. All bodies, armatures, animations and previous clothing mesh assets remain immutable in the source GLB library.

## Why this work was done

The earlier fitted MakeHuman35 wardrobe had apparently clear **vertices** at the bodice, but independent triangle-vs-triangle testing revealed crossing surfaces during every frame. Prior broad radial expansions of the bodices created more crossings. To localize the problem, the original triangle contact IDs were inspected; contact pairs cluster at the bodice upper armhole seams (approximately local y=1.34 m, x=±0.18 m). This is *not* a proof that the garment is natural or wearable.

## Localized hypothesis and adversarial selection

A bounded smoothstep field enlarges only the ±x shoulder/armhole band around x≈0.184 m, y≈1.345 m, preserving other garment slots. Trials were generated with deterministic source SHA binding; the source GLB's BIN prefix remains identical and source mesh is retained. Topology, UV, joints, weights, rig hierarchy, animation and other garments stay unchanged. Each changed mesh receives fresh glTF POSITION and NORMAL accessors and cannot overwrite the original source. Candidate mesh quality rejects inverted faces and excess relative edge stretch.

- Uniform 5 mm armhole displacement: sampled Aster bodice crossings 84→76, Juniper 62→74, **REJECTED** because Juniper worsens.
- Uniform 10 mm: sampled Aster 84→86, Juniper 62→36, **REJECTED** because Aster worsens.
- Actor-specific 5 mm Aster + 10 mm Juniper: sampled 9 poses **PASS_RELATIVE_ONLY**, but full 73-pose paired contact gate finds **three newly increased Aster crossings** at frames 18, 37 and 66. Full candidate Aster 693→652, Juniper 516→292 crossing pairs, but **RED_REGRESSION** despite aggregate benefit. Preserved as negative evidence.
- **Juniper-only 10 mm, Aster truly unchanged**: rest plus all 72 CPU-skinned poses; Aster bodice 693→693 and Juniper 516→292 pairs (**43.4% fewer**). Aster skirt 1721→1721, Juniper skirt 1317→1317; trim and footwear 0→0 observed crossing pairs. Signed vertex fraction unchanged for all actors/slots; top/trim/shoe vertex penetration 0 in this proxy, skirts remain nonzero. The independent paired comparator reports **PASS_RELATIVE_ONLY, 73 individual improvements, 0 regressions**, with complete 73-frame evidence.

The full run was executed as nine separately measured source-hash-identical chunks after a monolithic VTK invocation exceeded the local execution timeout. The fail-closed stdlib assembler verifies every frame appears once, actor/slot semantics, source hash equality, and all scientific approval flags. A valid 73-pose joined receipt is checked against the independent signed-distance sample series.

## Engineering limits and next gate

The Juniper bodice still has **292 crossing pairs**, in all 73 sampled states, and Aster's original bodice still has 693. Skirt crossings persist. Zero detected footwear/trim *surface* crossings does not prove clearance, pressure or shoe-ground contact; no full volumetric simulation was executed. Static armhole overlay reveals a very simplified tube bodice, not human-realistic patterning. This candidate is a reversible research comparison, **not a replacement of the wardrobe master**.

Next: reauthor actual shoulder armhole seam/straps (or sleeved upper garment), especially the four repeating source shoulder faces; reauthor hip/thigh skirt yoke and skin-weight distribution; independently validate native Blender 72-frame deformed triangle-level contact, ground contact, physics, face and body realism and human acceptance. Preserve owner wardrobe branch #337 and separate native 72-frame validator branch #340. Do not create parallel controllers, overwrite source, or merge/release/CPE.

## Reproduction

From `qualification/parametric_humans`, on a locally authorized original-only source admitted with SHA256 `a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739`:

```
python3 -m unittest -v test_contact_pose_batch_v1 test_armhole_profile_contract_v1 test_armhole_actor_specific_v1
SCP_MH35_FITTED_SOURCE=/path/to/source.glb python3 -m unittest -v test_armhole_actor_specific_v1
python3 armhole_actor_specific_v1.py --input /path/to/source.glb --out /tmp/juniper-armhole.glb --receipt /tmp/juniper-armhole.json --aster 0 --juniper 0.01
```

Run `compute_armhole_chunk_v1.py` with `--index 0..8`, then `contact_pose_batch_v1.py` with the nine ordered receipts. Use the existing `observe_makehuman35_garment_v0.py` and `triangle_vertex_contact_gate_v1.py` for paired signed per-vertex validation. NumPy/SciPy/VTK are only required for the actual owner-local geometry/CPU witness; the source-free contract and assembler tests require Python stdlib only.

Keep binary GLBs and full sensitive provenance/source-bound evidence in the existing owner-private Drive wardrobe research folder. Only source/test/contracts/compact false-approval-safe scientific receipt belong in Git. Existing #336 stack remains draft/unmerged and its parent-base drift remains HELD.
