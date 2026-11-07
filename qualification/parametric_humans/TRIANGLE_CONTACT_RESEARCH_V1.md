# R009 MakeHuman35 — full 72f triangle collision falsifier and dual-metric gate

**2026-11-07 • technical research • source-original Aster/Juniper + MakeHuman core CC0 body**

## Source and provenance

The exact source is the independently archived 2-actor GLB `footwear_cross_section_opening_v1.glb`, SHA-256 `a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739`. The file has one 35-joint skin per fictional actor, 72 source animation frames and independently skinned removable garment nodes. The generator does **not** use Naomi or Alison meshes. The corresponding MakeHuman visible-body source is a separately admitted CC0 original, not a license grant for any unrelated assets.

The CPU observer `triangle_surface_bvh_v1.py` reads glTF accessors, evaluates world-to-actor-local linear-blend skinning, and sends the actual deformed body and garments to VTK's `vtkCollisionDetectionFilter` in all-contacts mode. It runs source SHA checks, 35-joint namespace checks and preserves all source bytes.

## Independently observed full sampling

The complete run contains **rest + all 72 animated frames**, for two actors and four slots (584 actor-slot states). Aggregated triangle contact pairs:

| Slot | Aster pairs | Aster frames crossing / 73 | Juniper pairs | Juniper frames crossing / 73 |
| --- | ---: | ---: | ---: | ---: |
| `costume_top` | 693 | 73 | 516 | 73 |
| `costume_bottom` | 1721 | 59 | 1317 | 51 |
| `costume_trim` | 0 | 0 | 0 | 0 |
| `footwear` | 0 | 0 | 0 | 0 |

**First scientific RED:** Previously recorded zero bodice embedded vertices does not mean zero surface intersections: bodice triangles cross in every evaluated state. A zero triangle count also does not exclude complete enclosure, adjacent surface tangency, or other cloth failures.

## Independent radial fit hypotheses: rejected

A separate non-destructive source-pinned trial is retained as `garment_radial_trial_v1.py`. Original meshes and binary buffers remain intact, with individual new candidate nodes. In an initial eight-pose triangle audit, outward 6% and 12% bodice grades increased Aster crossings from 75 to 300/1051 and Juniper from 54 to 338/1014. Reject both bodice grades.

For paired **nine-pose** triangle/signed-vertex evaluations of skirt grades:

| Case | Aster skirt contact pairs | Juniper skirt contact pairs | Coupled acceptance |
| --- | ---: | ---: | --- |
| Original | 160 | 126 | baseline, already failing |
| 8% radial | 65 | 82 | RED: 7 worse actor/pose/metric cells |
| 14% radial | 16 | 6 | RED: 10 worse actor/pose/metric cells |

The paired signed test additionally found Juniper rest-pose penetration and worse sample averages under the seemingly favorable grades. `triangle_vertex_contact_gate_v1.py` matches SHA, actors, garment slots, frame clocks and sign calibration and rejects **any** triangle crossing or vertex inclusion regression. Its `PASS_RELATIVE_ONLY` is not cloth acceptance. Test controls include crossings, separated surfaces, coincident faces, invalid triangles, NaNs, wrong source hashes, mismatched frames, false scientific approval, and the two *actual* rejected radial cases.

## Reproduction and limits

Numerical requirements: Python 3, NumPy, SciPy, VTK 9.6 or compatible, plus the existing `costume_garment_v1`, `sculpt_human_v1`, `retarget_makehuman_v0`, and `observe_makehuman35_motion_v0` sibling producers. Exact source is kept under **owner-private Drive custody**, not public GitHub. In the repo workcell, pass original-only exact GLB through `R009_MH35_GLB` for actual-source tests; otherwise public source-only unit tests run with scientific source-dependent tests explicitly skipped.

```sh
python3 -m unittest -v test_triangle_surface_bvh_v1 test_triangle_vertex_contact_gate_v1
python3 triangle_surface_bvh_v1.py --input <verified-source.glb> --expected-sha256 a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739 --receipt triangle_bvh_73frame_v1.json --all-72
```

CPU evaluated animation is not native Blender evaluated mesh, physically simulated cloth, force/pressure, signed penetration volume, garment/body continuous collision response, natural gait, photorealism, identity, source publication, or CPE release. Native 72f validation of *this MakeHuman replacement* remains held. The previously separate adventure garment native PR #340 tests a different base/model cut; its success does not substitute for this test. Keep upstream PR #308 / child #336 base-SHA drift and owner merge/release holds intact. No changes should be made to original producer, main, or protected private real-person sources during this batch.

**Next executable owner baton:** A genuine garment top pattern replacement and pelvic/leg yoke skirt topology+weights redesign, using this two-metric falsifier at all 72 frames, and native Blender full triangle-collision/strain before visual acceptance. Avoid broad radial grading and arbitrary vertex projection.
