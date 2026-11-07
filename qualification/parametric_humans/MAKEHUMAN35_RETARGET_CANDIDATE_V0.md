# R009 MakeHuman CC0 to 35-joint research batch (2026-11-06)

Status: **technical prototype, not realism, cloth, anatomical, sex morphology, motion or release acceptance.** Source-original Aster/Juniper 35-joint glTF rig/costume; CC0 MakeHuman body-only source; no protected Naomi/Alison inputs.

- Source-pinned MakeHuman body-only OBJ SHA256 `378921118144289030c9dad2e274dadc7affd8ff394a2ac93d562252b6513de8`; body 13,380 geometric verts / 13,378 quads; 14,517 GLB vertices after necessary UV seam splits; 26,756 triangles.
- Original scripted classic adventurer original-source sculpt repair GLB SHA256 `5e86d299bffbeb478d1e4945aeaefd2692ccff67dd641ef84170122a283eca1a`.
- New candidate GLB SHA256 `57a4cfd1d9df7e6e2f7c2e44e68765a8ca4357895d5b075f9229b78a5bbcd36a`. All source geometry, material, 35-joint armatures, and 72-frame animation preserved in scene/library; original body mesh inactive, not destroyed; new CC0 candidate body visible.
- Weight proxy: 4 nearest *used source body* vertices, explicit proximity and 35-index normalization. Source pose source-forward +Z -> target-forward -Z; continuous arm/posture and feet offset; original body no retopology. Source MakeHuman target has arms and hands anteriorly shifted. Registration deliberately uncalibrated, cannot assign identity or infer morphology.
- Actor Aster is a technical provisional masculine-presentation adjustment of the female/default MakeHuman base, **not an accepted anatomically masculine body**. Owner's Master -> Aster alias remains provisional. Juniper retains feminine template but appearance likewise not accepted.
- Independent per-actor source-bound 72-frame CPU skin LBS diagnostic evaluated exactly 72/72 frames: both rest bind errors < 1e-4; 99th percentile edge-stretch worst frame ~1.28x (Aster) and 1.27x (Juniper); worst fraction >50% triangle-edge strain ~0.60/0.61%. This is not Blender nor proper gait/anatomy acceptance.
- Signed VTK surface evaluation calibrated against a torso interior and known exterior: original costume bodice REST vertices >5mm inside body: Aster 22.3%, Juniper 37.7%; original skirt 7.8%/8.4%; trim 37.0%/40.1%; footwear 19.7%/19.7%. First scientific RED retained.
- Reversible hybrid size-grade + signed surface clearance candidate repairs TOP/BOTTOM/TRIM: **0% >5mm penetration at REST for both actors**; sparse rest+four-source-animation-frame samples also stay near 0% for top/trim, <=2.8% for skirt. Original source garments remain as inactive library meshes, geometry/skin/animations retained. **Footwear still fails (~19.7% vertex sample inside body)** and no full 72-frame native cloth acceptance. The Aster dress cut must NOT be promoted as male clothing. Partial face reversal ~0.1% of top triangles remains a hold, as does grading cut fidelity.
- Static VTK frontal/side/face images represent REST geometry, not source-native Blender rendered, do not prove final skin deformation or identity. Hair gaps, false facial eyes, male morphology, original costume clipping, body/shoe mismatch require correction.

## Reproduce locally (no network; only files already admitted)

```sh
python3 -m unittest -v test_retarget_makehuman_v0 test_observe_makehuman35_motion_v0 test_fit_signed_clearance_v0
python3 retarget_makehuman_v0.py --source-glb <sha-pinned-original-classic.glb> --makehuman-obj <sha-pinned-body-only.obj> --output-glb candidate.glb --receipt candidate.json
python3 observe_makehuman35_motion_v0.py --glb candidate.glb --out cpu72.json
python3 observe_makehuman35_garment_v0.py --glb candidate.glb --expected-sha256 57a4cfd1d9df7e6e2f7c2e44e68765a8ca4357895d5b075f9229b78a5bbcd36a --out garment-signed.json
python3 fit_signed_clearance_v0.py --source candidate.glb --out hybrid.glb --receipt hybrid.json
```

Dependencies at research runtime: Python3, NumPy, SciPy, trimesh, VTK, Pillow. First production target should use calibrated native MPFB/MakeHuman skeleton and original MakeHuman gender/proportion morphs, not the provisional geometry transforms; native Blender 72f skin/garment visual QA and rigorous signed collision remain held.

## Repo custody / next DLE baton

- Git: scripts, tests, receipts, source SHA and CC0 reuse notice on preexisting draft R009 PR #336; no new branches/issues/workflows; guard source parent drift #308/#336, no merge/close/delete/release.
- Private Drive: full GLBs, two immutable source inputs, actual static screenshots and research bundle ZIP; verify upload/readback SHA. Do not redundantly upload the exact same ZIP twice.
- Next: bring in the **real official MakeHuman gender/shape target deltas** under exact Git blob/license pin, rebuild Aster male phenotype non-destructively; use a native rigging adapter (not nearest-neighbor) with meaningful joint calibration; build fitted outfit patterns with 72f BVH positive/negative tests; native six-view Blender review and motion validation. Hold until thresholds and human signoff.
