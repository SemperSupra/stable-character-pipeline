# R014 Blender Studio CC0 sculpt → MPFB parametric rig dry-run

Research admission for two independent **adult synthetic** body presets. This workflow uses existing **public** GitHub Actions artifacts, not upstream MakeHuman's 281MB textures or private people/likeness files:

- Corrected MPFB neutral rig: run `43202169814`, artifact `13935772441`, female macro `0.0` and male macro `1.0`.
- Blender Studio authentic CC0 10,582-vertex multiresolution sculpt bases: run `43212080935`, artifact `13942066258`.

A static axis-aligned fit (with facing reversal bakeoff) and barycentric nearest source triangle transfers **up to four** source bone weights to each target sculpt vertex. It measures correspondence distance, skin influence coverage, and a small genuine upper-arm/upper-leg pose response, saves a native scene and neutral/posed renders **per actor**. This tests whether the candidate base is transportable to rigging, not whether it is realistically rigged.

**HOLD:** bounding boxes are not anatomical landmarks; high local errors can misassign fingers, eyelids, pelvic skin and neck. Unmodified original source meshes remain in Drive. This branch is independent, $0 public GHA (read-only source artifacts), disposable Blender, draft/unmerged and requires reviewed anatomy, texture/UV stability, actual glTF rig parity, volume/contact, reproductive anatomy, facial action controls and cinematic QA before any release.

User Drive custody: https://drive.google.com/drive/folders/19bzvrQ35DwIxdpftrDCjxezNLa2UQl-v

Private product DLE: https://github.com/SemperSupra/stable-character-pipeline-private/issues/138 .
