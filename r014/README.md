# R014 MPFB native female/male source-admission bakeoff

Independent experimental branch. Executes the official, **pinned** `makehumancommunity/mpfb2` source in a disposable Blender 4.5.16 public GitHub Actions runner. The bundled base meshes, rigs, and targets are CC0 per upstream LICENSE.md; extension source is GPLv3. No external contributed asset packs, real-person imagery, private model files, R002 bytes, or identity sources are used.

The workflow attempts to construct two neutral adult parametric bodies with the official MPFB `HumanService.create_human` / `add_builtin_rig` APIs, save a native scene, export a structural GLB and then reopen the scene in a fresh process.

Success would demonstrate only a functional anatomically grounded model **foundation**, not photorealism, facial/hand performance, local soft-tissue material physics, commercial-ready skin/hair or 4K video. Failures must be preserved without waiving gates.

License authority: https://github.com/makehumancommunity/mpfb2/blob/6ff1eb358f6c1959ced77e79e6dd2406d9a71f49/LICENSE.md
Private product authority: https://github.com/SemperSupra/stable-character-pipeline-private/issues/138
Draft branch only: no merge or production adoption until independent review.
