# R036 — Official MPFB native rig and anatomy attachment

This is the first actual **upstream MPFB service/rig** demonstration, not a synthetic replacement of its character skeleton. It invokes `HumanService.create_human()` and `HumanService.add_builtin_rig(...,"default",import_weights=True)` from source pinned at `makehumancommunity/mpfb2@9de0707fdc88438d7c53a1a2ac7937d9221e2431` and checks the official skinned body geometry and native armature. It attaches two original **synthetic diagnostic anatomy proxies**, each weighted to a selected *actual* torso bone, moves the official rig, tests both external and internal evaluated vertex changes, renders source-geometry and isolated anatomy frames, saves/reopens scene and examines GLB skin/mesh structures.

Upstream code GPLv3; officially bundled core base/rig assets CC0; dependencies and any other community organs/assets have separate rights. Do NOT upload upstream source, generated scene or media in public artifact output. Source code is fetched by immutable Git SHA in a disposable standard public Actions CPU runner, not copied into this repository. No protected identity, private media, private Actions minutes, GPU requirements or credentials.

This workcell must NOT be considered an anatomically correct organ/muscle model, full MPFB skin material production, medical/physics validation, photorealism, cinematic quality, game-engine reimport or accessibility acceptance. It qualifies only true native MakeHuman mesh/rig binding if the independent Blender run passes.

## Required upstream primitives

- `HumanService.create_human()`: source basemesh with original morphology controls, masks and identity data layout.
- `HumanService.add_builtin_rig()`: official rig JSON definitions, authentic joint placement and bone weights.
- MPFB `HumanService.refit()`, skin, macro target, asset/pose/export-copy services: future morph/soft-tissue integration.
- Official `makehumancommunity/mpfb-mcp`: existing closed-vocabulary agent service with 42 tools, should be qualified for integration and reused if safe, not replaced by an arbitrary code-execution bridge.

Reference: https://github.com/makehumancommunity/mpfb2/blob/9de0707fdc88438d7c53a1a2ac7937d9221e2431/script_samples/03_adding_a_default_rig.py

## Acceptance progression
A narrow native pass requires stable official body+rig, observed posed skin and internal proxy motion, render visibility separation, independent Blender process reopen, GLB skin and multiple named meshes. Next: validate real anatomy source-to-bone + surface attachments across MakeHuman body morphs; independent visual QA/physics and render/engine exports with human+assistive, script/API, agent discovery and operator lifecycle. No merge, release or product quality promotion without separate review.
