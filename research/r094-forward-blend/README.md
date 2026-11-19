# R094 — forward compatibility of saved 4.5.16 actual CC0-dressed MakeHuman scenes

**Gap:** R092 full-native 5.2.4 PR #664 and R093 5.3.0 PR #665 each passed exact source-bounded **same-version** native creation and Diffeomorphic retarget, comparing exactly to 4.5.16 source geometry and measured shoe contact. No previous work had demonstrated **opening an existing real 4.5.16 authored CC0-dressed .blend under a newer Blender.** Lightweight concurrent smoke PR #663 tested synthetic geometry but initially had a missing-camera fixture issue; this is a separate native source-file, unchanged binary, exact-asset bridge.

This workcell runs two independent disposable free public GitHub Actions jobs (newer targets 5.2.4 LTS and 5.3.0 stable), each:
1. Fetch official Blender 4.5.16 and exact newer standalone Linux binaries with publisher SHA256 manifests, and assert actual bpy version.
2. Fetch hash-pinned upstream official MPFB code + original-female MakeHuman CC0 core, build the genuine two 163-bone Aster/Juniper source scene under **4.5.16**.
3. Acquire exactly hash-pinned CC0 shirts/pants/shoes and attach 3 real skinned garments each using MPFB HumanService; save original .blend under 4.5.16 only.
4. Record at 4.5.16 actual evaluated body/garment vertex arrays' SHA256 and 163-bone pose matrices at frames 0/35/71, including 3 CC0 garments per actor and scene/source SHA.
5. In a separate headless **5.2.4/5.3.0 process**, open the **identical** .blend file, independently resample all that geometry and poses, verify exact bitwise agreement and source file hash, verify a Workbench camera-based render produces non-empty PNG. Fail closed on altered morphs, garment topology, action clock, or missing source.
6. Publish only JSON receipts, not raw .blend, CC0 meshes, source BVH, or rendered images.

**HOLD:** This is read-only forward-opening; saving from newer Blender and reopening under 4.5.16 (backward-read), EEVEE/Cycles visual equivalence, exact cloth physics, contact IK, photorealism, protected Naomi/Alison fit, and MVP remain NOT TESTED. Both 5.2 and 5.3 are fully qualified only for the operations exercised. Current 4.5.16 rollback anchor is immutable.

DLE: protected R009 private #23, public original/CC0 MVP #272, P0 five-bone stance #662, numerical qualification #650. Draft/unmerged, no paid minutes, no protected subject material.
