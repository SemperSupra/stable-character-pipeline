# MMD public format and motion workcell

This **independent** public workcell produces an original synthetic PMX triangle (one weighted center bone), two-keyframe VMD motion (0→30 frames), and VPD pose. There are no downloaded character models, dances, real-person assets, private images, or media. It does not import private human pipeline source or flora/mechanica files.

## Reproduce

- MMD Tools v4.5.14, **immutable source** commit `f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14`, GPL-3.0-or-later
- Python 3.11+; no Blender required for the first parser/serializer gate
- Run `python3 mmd/qualification/probe.py --source vendor/mmd-tools --out mmd-output`
- Public workflow: `.github/workflows/mmd-public-qualification.yml`
- Outputs: `synthetic_triangle.pmx`, `synthetic_center_motion.vmd`, `synthetic_center_pose.vpd`, `qualification.json` with SHA256 and negative controls
- The workflow repeats generation from scratch and compares byte-identical native outputs; artifact is stored for 14 days and can be downloaded from Actions.

## Candidate catalog / qualification status

| Candidate | Formats and role | Headless | License / boundaries | Current gate |
| --- | --- | --- | --- | --- |
| MMD Tools 4.5.14 | PMD/PMX models, VMD motion, VPD poses | Parser Python; Blender extension | GPL-3.0-or-later; separate rights for every external model or motion | Synthetic format gate to execute |
| Blender 4.5 LTS | Rig, camera, render, glTF interchange | `-b --python` | GPL; must verify real add-on registration and compatibility | UNTRIED |
| MikuMikuRig | MMD-to-Rigify adaptation | Blender candidate | Verify transitive license | UNTRIED |
| MMD Tools Append | Rig and morph helper | Blender candidate | Verify transitive license | UNTRIED |
| MMDBridge | Native MMD physics/IK compatibility | Windows/native dependency | Do not claim Linux support without a rep | HOLD |
| VRM/UniVRM | Humanoid interchange | Blender candidate | Validate exact version and deformation fidelity | UNTRIED |

**Pass is narrowly scoped.** Parser round-trip and bad-magic detection are *not* evidence that rigging, pose motion, retarget, IK, physics, constraints, morphs, fingers, hair, body soft tissue, facial expressions, fabric, or visual outputs work. MMD Tools' own README warns that Blender IK and physics differ from native MMD.

## Follow-on READY work

1. Run a Blender >=4.2 CPU workcell (not an older Ubuntu apt build) to import the PMX and inspect bone/mesh topology. Export Blender-native `.blend` and `.glb` with inspected scale/axes.
2. Load native VMD and VPD through real Blender MMD Tools operator, inspect sampled transforms and render a contact sheet, not merely generate a movie.
3. Falsify adversarial metadata, malformed weights and interpolation, Unicode bone names, and cross-version PMX/PMD/VMD/VPD compatibility.
4. Evaluate editable sources, motion catalogs, convert-to/convert-from BVH/FBX/VRM/glTF, foot contacts, IK, expressive face/hands and physics separately.
5. For candidate external MMD models and motions, catalog author, source, URL, exact hash, redistribution license, commercial-use restrictions, attribution, model/motion pairing and audience access. No public redistribution until separately authorized.

Every element must be reproducible using $0 public CPU GitHub Actions, with bounded jobs and no credentials or third-party assets. Do not merge, deploy or release without explicit authorization.

## G4 animated interchange workcell (candidate)

The independent Go-compatible admission receipt is separate from Blender output.
\`mmd/qualification/interchange_probe.py\` uses the real MMD Tools Blender
importer and original PMX/VMD fixture to generate 31 consecutive CPU-rendered
PNG frames, animated GLB and an editable BLEND. \`verify_interchange.py\` parses
the GLB independently without importing Blender, verifies a moving skinned
joint with finite timestamps and valid binary offsets, compares rendered PNG
pixels and tests negative-control malformed GLBs. GitHub Actions encodes a
yuv420p H.264 MP4 with \`+faststart\` and verifies it with ffprobe.
Only a completely green independent job qualifies this workcell. Motion quality,
native MMD physical fidelity, retargeting, expressive morphs and rights for
external MMD assets remain separate qualification gates.

## Timing alignment gate

Blender's native MMD Tools VMD import uses scene frames 1–31 for source
VMD 0–30; our first glTF export consequently ran 0.033333–1.033333 s,
while the independent headless mmd2gltf converter exported 0.0–1.0 s.
Rather than author a bespoke timestamp patcher, use the upstream Blender
glTF option \`export_anim_slide_to_zero=True\`. G4's binary inspector
requires a 0.0–1.0 s animation for this exact 30-frame fixture; G5's
independent comparison requires exact time-origin and endpoint agreement.
A different duration requires its own fixture-specific schedule; these
checks are not a general-purpose motion normalizer.

## G7 articulated weighted rig — research-only workcell

Original synthetic three-bone PMX ribbon (center, arm, wrist), eight vertices
over three connected segments, four BDEF1 + four BDEF2 weighted vertices.
Two original VMD bone quaternion rotations at frames 0 and 30, verified with
the actual MMD Tools serializer and Blender importer. Independent geometry
acceptance requires roots stay anchored, tip skin actually moves, and *both*
arm/wrist quaternions rotate. Native glTF export is inspected for two
independently animated skinned-joint rotation channels, bounded accessors,
0.0–1.0 s origin and normalized quaternion keys. Three genuine CPU-rendered
diagnostic frames are visually checked and assembled into a contact sheet.
The original .blend, .glb, .pmx and .vmd are retained with machine-readable
receipts; no third-party character/model/motion assets, no claim of MMD toon,
IK, Bullet physics, human anatomy or soft-body fidelity.

## Verified G9 vertex morph workcell (2026-10-27)

- **Original assets only:** `mmd/qualification/morph_fixture.py` generates a 4×4 geometry grid (16 vertices, 18 triangles) with Japanese MMD PMX morphs `まばたき` and `笑い`, each with four vertex offsets. VMD keys at frames 0/15/30 encode Blink [0,1,0] and Smile [0,.35,1].
- **Native Blender observation:** `morph_blender.py` uses actual pinned MMD Tools and Blender 4.5. Select the imported **mesh or model root**, not the armature alone, to import actual VMD morph curves. Call `bpy.context.scene.frame_set(0)` **before** invoking the upstream VMD importer: it anchors keys to the current scene frame (normally frame1), so failing this creates a hidden one-frame slip. Embedded bpy workers must preserve failure tracebacks before `os._exit(1)` to avoid shutdown hangs.
- **Independent interface:** `verify_morph.py` checks actual GLB POSITION morph targets and animated weight channels in native Blender vs the independently pinned MIT `mmd2gltf` CLI, checks both weight values/time origin, and rejects absent targets / NaN weights. Blender samples 31 frames; the direct converter keeps 3 original keys, both span 0–1s. Diagnostic PNG contact sheet checks actual imported geometry, **not** face realism.
- **Public evidence:** isolated workflow `.github/workflows/mmd-morph-parity.yml`, [successful run 40455150395](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455150395), evidence artifact `12711664118`, 14-day retention. First-frame-shift failure remains in issue #19. No likeness/makeup/styling/person-state assertions.

## Verified G10 MMD IK workcell and falsified Blender default (2026-10-27)

- **Original IK source:** `ik_fixture.py` creates a fictional four-bone leg (`腰` → `ひざ` → `足首` plus `足ＩＫ` controller), PMX target index2 and IK links [1,0], 24 source iterations, and authored controller translations at VMD frames0/30; no human models or community motions.
- **G10a source preservation:** `verify_ik.py` independently reads actual mmd2gltf GLB `extras.mmd.ik` and skin hierarchy, with negative tests on damaged parent and links. Isolated [successful run 40455687379](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455687379), original asset/reference artifact `12711259553`.
- **G10b real source converter target tracking:** `.github/mmd-ik/verify_contact.py` reconstructs glTF world joint transforms by full quaternion Hamilton multiplication, measured ankle-to-controller distance at original 0/15/30 frames, comparing enabled vs `--no-ik`. Reproduced using independent SciPy Rotation mathematics. IK enabled errors [0,.015721,.033370] vs disabled [0,.201556,.403113]; acceptance requires <.05 source units and ≥50% improvement at both moving frames. [Successful run 40456000406](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456000406), receipt artifact `12712169140`.
- **G10c real Blender:** direct imported PMX constraints are **insufficient** as evidence of solver correctness. Original import default leaves hip and knee tail ends disconnected from the next bone heads and showed errors ~1.82–1.99 units. The upstream MMD Tools operator option **`fix_ik_links=True`** makes the bone head/tail chain Blender-suitable; the corrected original-source Blender import evaluated frame0/15/30 IK goal errors [2.40e−7,3.41e−7,1.45e−6]. [Successful run 40456662219](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456662219) is authoritative for the corrected Blender source and editable `.blend`; artifact `12712981080`.
- **G10d cross-engine gate:** `.github/mmd-ik-cross/compare.py` deliberately fails when either absolute goal error or cross-engine delta exceeds .05 units. Earlier [run 40456565154](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456565154) RED was real under unaligned Blender chain, preserved as negative evidence. Corrected reference to G10c run 40456662219 yielded [run 40456784554](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456784554) **GREEN**, maximum observed cross-engine error difference .03337 source units; receipt artifact `12712661688`.
- **Caution:** an initial throwaway local diagnostic had a missing quaternion Hamilton-product term and incorrectly overstated IK error. Independent second-math-engine verification is a required anti-falsification practice. Goal tracking is **not** physical ground collision, realistic gait or native MikuMikuDance Bullet/CCD equivalence.
- **Efficiency and rights:** all isolated jobs use $0 public hosted CPU. The expensive original G1–G7 workflow is scoped to its inputs, not every MMD experiment. GitHub Artifacts expire after 14 days; source fixture + workflow are durable in the public unmerged branch. Do not mirror any third-party character, motion or texture without per-asset rights admission. No merge, release or deploy.
