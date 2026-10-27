# W03 — `NODE_SKINNED_MESH_NON_ROOT` original synthetic GLB interoperability

**Authority:** [MMD public DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19); original unmerged draft PR #20, unchanged. W03 separate candidate [draft PR #33](https://github.com/SemperSupra/stable-character-pipeline/pull/33) on branch `qualification/mmd-w03-gltf-reimport-20261027`. No merges/releases/deployments, third-party motions/models, private human identities, paid compute or policy promotion.

## Discovery / prior art

[Khronos glTF Validator](https://github.com/KhronosGroup/glTF-Validator) recognized both original Blender-exported GLBs as formally valid (**zero glTF format errors**) but emitted the warning `NODE_SKINNED_MESH_NON_ROOT`. This is an interoperability **warning**, not a conformance-error exception. Do not silently change scene parenting solely to silence the diagnostic: preserving skinned mesh coordinate frames matters more than cosmetic zero-warning output.

This W03 workcell uses two independent **actual** upstream readers, not another bespoke byte parser:
- MIT [glTF-Transform `@gltf-transform/core@4.2.1`](https://gltf-transform.dev/modules/core/classes/NodeIO) native NodeIO and graph accessor APIs; inspect scene graph, skin joints, mesh morph targets, animation channels, parent/wrapper relationships.
- Genuine Blender bpy **4.5.0** `bpy.ops.import_scene.gltf` for full reimport into editable BLEND, bone/shape-key/action inventory and actual evaluated vertex positions at source frames **0, 15, 30**.
- Original G7/G9 fixtures only, pinned by **source artifact** and exact SHA256 against the *prior independent official Khronos* G11 proof, not mirrored or substituted by demo characters.

## Exact original inputs and previous standard evidence

| Source | Original Actions run | SHA256 of GLB | Native warning |
|---|---|---|---|
| G7 articulated ribbon `articulated_ribbon.glb` | [40451441477](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40451441477) | `e5aa5b2f068c83acbdefe1a204931e616a22b42d7c42d589b54249963ffec954` | `NODE_SKINNED_MESH_NON_ROOT` |
| G9 two-morph face grid `synthetic_face_morph.glb` | [40455150395](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455150395) | `a71aa6e0ac7c4b5a4e9c2e99da07f76d7dc6ca4be33d4068792c7f278e7ee5b9` | `NODE_SKINNED_MESH_NON_ROOT` |

Khronos evidence [run 40458065375](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40458065375), [source harness](https://github.com/SemperSupra/stable-character-pipeline/blob/qualification/mmd-public-20261027/.github/mmd-standards/validate.cjs), ZIP SHA256 `84ff074093109f21f49f0d07dbe3a2c597d86b1099a68710f2e6bd73f61577e2`; all original model and motion sources are synthetic/self-authored.

## First genuine public runner observation

[W03 $0 Ubuntu CPU Actions run 40549035079](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40549035079) terminal **SUCCESS**, native job `122347412108`; native logs and input SHA matches independently read.

| Measured property | glTF-Transform NodeIO | Blender bpy native import |
|---|---|---|
| G7 skin | one skin with **3 joints**, non-root skinned mesh, 9 animation channels | one armature with **3 bones**, armature modifier and one animation action |
| G7 geometry actual motion | document structure only; **not rendering** | frame 0/15/30 evaluated source mesh vertex hashes differ, bounds change |
| G9 morph | one skin with 1 joint, **2 morph targets**, 1 animated weights channel | one armature with 1 bone, 2 shape keys and one animation action |
| G9 evaluated deformation | document structure only; **not rendering** | original morph actual evaluated geometry changed at frame 0/15/30 |
| Negative controls | deliberately truncated GLB refused, deliberately removed in-memory skin loses required feature | frame-varying mesh-check contract added for next run |

Original public output artifact `public-mmd-w03-two-reader-reimport-evidence` **12754056441**, ZIP SHA256 `85524fb655804c5b296a9b2e848bceb65c3670ac4d889daa0dbc87207c948bdc`, retention 14 days; includes reimported editable BLEND files, independent reader JSON, Blender evaluation JSON, two-reader reconciliation, input digests, observed upstream package versions.

## Classification and limitations

**Qualified from observed data:** Both upstream readers accept original G7/G9 Blender-exported formally conformant GLBs despite the non-root skinned mesh warning and recover essential *synthetic* skin/morph/animation structures. Actual native Blender glTF reimport evaluates moving geometry across sampled frames. This falsifies the claim that the warning **necessarily** breaks these two tested readers.

**Not qualified:** All independent browser/WebGL/MMD-native viewers, material/toon/physics/soft body fidelity, full per-joint world-space trajectory or image parity with source, native MMD CCD, semantic rig control preservation, rights for arbitrary community PMX models/dances. We have **not demonstrated general equivalence** of non-root and root-skinned layouts, so do not automatically delete the warning or rewrite mesh parenting. glTF-Transform NodeIO is a structural document reader, not a rendered playback engine; Blender is a separate full import/playback implementation.

**Adversarial limitations:** Removing a skin binding in a temporary glTF-Transform in-memory document and truncating GLB bytes must fail. Blender checked non-empty imported mesh/armature/skin modifier, animation action and two genuine morph targets; the stronger final gate requires *each* adjacent pair of evaluated source sample frames to have different real geometry hashes. This is evidence for this synthetic fixture only, not physical-world motion.

## Three audience contract and next baton

- **Human:** this short finding, explicit rights/scope, native job logs and downloadable/editable BLEND evidence.
- **Automation:** reproducible isolated `.github/workflows/mmd-w03-gltf-reimport.yml` on $0 public CPU with immutable original Actions IDs/digests and machine-checkable JSON, PNG-free visual observations (evaluated vertices), SHA256 and falsifying controls.
- **Agent:** reader verdicts `PASS_INDEPENDENT_READER_STRUCTURAL_ONLY`, `PASS_BLENDER_REIMPORT_ONLY` and `PASS_TWO_INDEPENDENT_STRUCTURE_READERS` have declared *scope*, no implicit policy admission, native MMD or platform-wide compatibility guarantee.

**Baton:** validate stricter actual-motion gate on exact branch head, read native logs; record first failures, successful artifact and final warning classification in DLE #19; leave PR #33 draft/unmerged. Review if a third independent *rendering* engine (Babylon MMD/browser) exposes a true user-visible defect before considering any exporter root/hierarchy rewrite. W02 stays in separate stacked PR #30 under independent review. W19/W20 blind CPE research remains BLOCKED.
