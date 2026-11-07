# R009 original Aster/Juniper human-sculpt research v1 (2026-11-06)

Status: `GEOMETRY_TECHNICAL_PASS`, `HUMAN_REALISM_FAIL`, `MOTION_AND_CLOTH_UNQUALIFIED`, `RELEASE_HOLD`.

## Provenance

- Only the four exact source-original 35-joint Aster/Juniper costume GLBs authored in this project are inputs. Each input is SHA-256 pinned in `output/sculpt_batch_receipt.json`, obtained from the existing private Drive source-original modular wardrobe custody.
- No Naomi, Alison, photographed people, vendor mesh, downloaded anime mesh, confidential binary, or private identity source is used.
- Original source GLB bytes stay untouched; all exported sculpt files are derivatives with original binary data copied unchanged as the prefix of the derived glTF buffer.
- This is *not* an anatomical, artistic likeness, natural gait, garment collision, or photorealism acceptance.

## Actual sculpt edits performed

1. Inspect exact glTF mesh connected components; the original body has 30 separate surface components, including distinct capped arms, forearms, thighs, calves, palms, fingers, and face details.
2. Remove triangles of 4 arm, 4 leg, 12 hand, and 2 ear surface components per actor **only in the derived index buffer**. Retain source geometry accessors and original source asset independently.
3. Insert two new blended-weight continuous arm envelopes (shoulder to wrist), two anatomically tapered legs (hip to ankle), wrists/palms/finger tubes, rounded ears, and trapezius neckline; add 6,512 geometry triangles and 3,660 vertices per actor.
4. Moderately reshape 108 mandible vertices, 626 nose vertices and 313 lip-region vertices per actor; make the original eye surface less spherical and rework the skirt contour for hip clearance. The first additive facial experiment produced a muzzle-like defect; the final correction removed that added geometry. Preserve its failed image in the evidence package.
5. Preserve 2 existing skins with 35 joints each, all animation tracks, original source-only asset identity, all four costume cuts, and original material/name/wardrobe node definitions. No new rig, no incompatible extra interface.
6. Independently import all four generated GLBs via trimesh, assert exact source structure, run source-pinned replay twice, and keep visual QA and all test receipts.

## Reproduction

From `sculpt_batch` with Python 3.10+ and the two already admitted exact source files available:

```sh
python -m unittest -v test_sculpt_human_v1
python build_all.py --input-dir /path/to/source-original-costume-glbs
python render_all_styles.py  # VTK + trimesh + Pillow for local QA only
```

The generator `sculpt_human_v1.py` itself requires only standard-library Python and its imported sibling `costume_garment_v1.py` from public PR #336. `build_all.py` additionally uses trimesh for independent reader qualification. The eight corpus-bound tests fail closed to SKIP when their exact source fixture is unavailable on a clean public runner (provide it with `SCP_SCULPT_TEST_FIXTURE`); three hostile source-free controls always execute. Source-specific full-suite qualification requires an independently admitted local fixture.

Local validation: 11/11 unit/hostile tests PASS (three source-free, eight corpus-bound); 4/4 independent GLB source/native-structure import PASS; 4/4 deterministic byte-identical generator replay PASS. Blender 4.5.15 native motion/cloth tests NOT_RUN in this local workcell.

## Observed REDs and reasons not to accept

- First source facial sculpt stacked multiple ellipsoids into a cartoon-like nose and lips (REJECTED). Final pass removes them but retains visually stylized head/hair; **face aesthetics still FAIL**.
- Body is still procedural and uses multiple adjacent disconnected lofts, not a uniform quad-only subdividable anatomical topology.
- Real shoulders, elbow/knee joint centers, tendon/joint-surface bending, heel/toe force and tissue/cloth pressure are not verified.
- Skirt/hip clearance was improved by a bounded source-original radial adjustment but native full-motion garment collision remains not qualified.
- Material, hair grooming, eyes, eyelashes, teeth and high-resolution skin texture remain stylized.
- Original Aster and Juniper have intentionally different construction (male and female). Wardrobe fit must remain body-specific.

## Next engineering program

**P0 — realistic basemesh replacement:** Qualify MakeHuman/MPFB *core assets only* with exact asset version/hash and rights (`CC0` for core), separating GPL/AGPL program source from exported artwork. Test one native Blender generated character, original source provenance, unit scale, A-pose, normalized skin, facial/hand quad topology, and texture materials. Blender Studio has a reference CC-BY realistic male base that may be useful as a separate topology calibration candidate; no external assets acquired in this batch.

**P1 — rig topology and weight transfer:** Build a validated old-35-bone to target human rig mapping; preserve reversible source identity, body morphology parameters, separate clothing shells, and existing animation semantics. Explicitly measure surface projection correspondence confidence, missing joint mappings, topology degeneracy/inversion, weighted-skin discontinuities at shoulder/elbow/knee/ankle, facial topology, and 72-frame deformed vertex/contact statistics.

**P2 — proper character look development:** Refine and bake skin PBR, realistic orbital/eyelid shape, facial expression weights, scalp/groom, hair collision, hands, nails, lips/teeth, and realistic clothing layering. Produce consistent multi-camera before/after views and human visual inspections as acceptance evidence.

**P3 — multi-model reuse:** Port the qualified garment templates to Rocketbox and separately to admitted Alison/Naomi copies, with provenance and real-person/private model rights boundaries unchanged.

## Storage and hygiene

- Git / DLE: schemas, tests, generator, source hashes, small evidence receipt, owner decisions, active baton (add to existing public #336 only after code owner review; avoid parallel duplicate PRs).
- Owner-private Drive: full derived GLB, visual PNG, source packaging/large ZIP; exact SHA and original source custody index. No protected original Naomi/Alison bytes in public.
- Do not merge/close/release/CPE-promote merely because a synthetic technical test passes. No private Actions minutes were consumed.
