# R009 Aster/Juniper — Independent human realism / basemesh workcells

Date 2026-11-06. Status: synthetic code tests and actual source-only topology/degenerate repair PASS. Human realism, native Blender motion, cloth collision, MakeHuman retargeting, and release remain HELD.

## Independent batches

1. `sculpt_topology_gate_v1.py` + tests: read-only source-hash admission, topology island count, zero-area faces, unused vertex and normalized joint-weight checks. Actual original-classic GLB: 34 body mesh islands/actor (30 in main body primitive); provisional sculpt: 31 body mesh islands/actor (8 main +19 new plus 4 eye islands). Declaring an accepted continuous human surface here would be wrong. Actual sculpt still carries 6,710 unused vertices/actor.
2. `sculpt_triangle_repair_v1.py` + tests + `build_repair_four.py`: source-pinned, non-destructive index-only removal of exactly 144 zero-area body triangles/actor across each of four outfit GLBs. Total 1,152 source-derived zero-area faces removed in 8 character/outfit combinations. All 4 repaired files independently re-read via the actual glTF accessor/topology observer; remaining zero-area triangle count for full body = 0 per actor. This does not fix disconnection or source buffer inefficiency; output binary grows because the original glTF buffer is retained.
3. `basemesh_admission_v1.py` + tests: source-pinned MakeHuman CC0 `base.obj` topology and licensing admission primitive. Official GitHub blob SHA1 `d26635e9326e3cca30778fd7b9c00062b03cce09`, repo commit `a8bc2d54ff0ac92e78ff71431b1023eda42bf482`. Actual GitHub source fetched READ-ONLY and independently parsed in an isolated connector workcell: 19,158 vertices, 18,486 quads, 139 groups, of which 13,378 quads and 13,380 referenced vertices are visible body. The 5,108 remaining quads are helpers, joint markers, etc. **Asset was NOT yet downloaded into the local Blender workcell or imported/retargeted.** The parser requires exact source bytes and can be run on authorized public GitHub Actions/Blender later. No raw CC0 OBJ is bundled here.

## Real tests

`PYTHONPATH=<folder-containing-sculpt_human_v1.py>:$PWD SCP_SCULPT_QUALIFICATION_ROOT=/mnt/data python -m unittest -v test_basemesh_admission_v1 test_sculpt_topology_gate_v1 test_sculpt_triangle_repair_v1`

The test harness has 24 tests (11 basemesh source-free, 5 topology source-free, 2 local corpus-bound topology, 3 repair source-free, 3 local corpus-bound repair), all passing in this private sandbox. With no local GLB source, the 5 corpus-bound tests must skip and MUST NOT be mistaken for real source qualification.

## Boundaries

- These are owner-original fictional Aster and Juniper inputs. Naomi/Alison protected source is not included.
- Core MakeHuman graphic assets CC0; MakeHuman AGPL and MPFB GPL code not vendored.
- No rig topology swap, texture, cloth physics, facial expression, human likeness, medical/surgical validation, or 72-frame native Blender acceptance.
- Original 4 sculpt v1 source GLBs unchanged; only independent derivatives in `repaired/`.
- Git/DLE should track the code, receipt hashes and durable baton. Private Drive holds the large four GLB binaries, source bundle and QA receipts. PR #336 remains draft; merge/release/CPE and base SHA drift are still held.
