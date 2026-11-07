# R009 72-frame signed garment-contact witness — 2026-11-07

- Exact source: self-authored Aster/Juniper + CC0 MakeHuman 35-joint candidate with reversible fitted garments. This source is original fictional characters; it contains no protected Naomi/Alison data.
- Baseline source: `aster_juniper_cloth_clearance_hybrid_trim_v0.glb` SHA-256 `366fc2964e0e156988b0207735d89b8dbba18d6b92d0ac453e0d4fc7846fe99f` in the predecessor Drive research ZIP.
- Exact 72-frame source-bound signed-distance CPU evaluation, plus rest: 73 states ×2 actors ×4 slots = 584 calibrated actor-slot states. Original five sparse witness frames reproduce exactly; replayed with refactored shared evaluator and compared entire detailed reports exactly.
- **Pass as narrow metric**: fitted bodice and trim have 0% vertex embedding >5mm in all 72 animation frames.
- **Scientific failures**: skirt embeds up to 2.50% (Aster) / 1.875% (Juniper) at particular frames; footwear embeds up to 20.0% on both characters and is >1% embedded in all 72 frames. Projection and shoe scaling prototypes did not yield acceptable geometry.
- **Not a collision-free cloth result**: vertex signed distances miss triangle crossings, friction and fabric thickness; the character's gait, skin weights and realism remain unaccepted. Native Blender evaluated BVH, garment normals/inversion bounds, accurate feet/hands, signed triangle overlap and visual signoff remain pending.
- Hygiene: do not duplicate existing 6KB evaluator. Extend its frame-selection gate and keep a small independent exact-source wrapper. Git stores tests/scripts/summary; Drive stores full 365KB per-frame receipts and plots. No merge/close/release/CPE or parent-base drift acceptance.

## Local reproduction

```sh
python -m unittest -v test_observe_makehuman35_garment_72_v1
python observe_makehuman35_garment_72_v1.py --glb aster_juniper_cloth_clearance_hybrid_trim_v0.glb --out /tmp/72frame-signed-contact.json
```

Dependencies: Python3, NumPy, SciPy, VTK, source-original helper modules in existing PR; actual source GLB withheld from public CI as a large research artifact. Public CI may check source syntax without claiming the actual source-bound numerical test ran there.
