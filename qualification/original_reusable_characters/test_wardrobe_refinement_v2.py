"""Adversarial qualification for additive R009 A1/A3/A5 candidate."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from modular_wardrobe_v1 import ACTORS, PRESETS
from test_modular_wardrobe_v1 import witness
from verify_original_glb import decode, accessory
from wardrobe_refinement_v2 import build,continuous_figure,SHOULDER_GUSSET_RINGS,SHOULDER_GUSSET_SIDES,trouser_hip_inset,knee_cap_to_source_joint
from wardrobe_portable_export_v2 import export

class RefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.source=cls.root/"source.glb"
        cls.manifest=cls.root/"source.json"
        cls.receipt=build(cls.source,cls.manifest)
        cls.m=json.loads(cls.manifest.read_text())
        cls.d,cls.bb=decode(cls.source.read_bytes())
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_workflow_recovery_fails_on_duplicate_or_truncated_steps(self):
        """Regression against the actual duplicated/truncated workflow first RED."""
        path=Path(__file__).resolve().parents[2]/".github/workflows/r009-original-wardrobe-refinement-v2.yml"
        content=path.read_text(encoding="utf-8")
        self.assertEqual(content.count("\n      - name: Fresh source-only adversarial"),1)
        self.assertEqual(content.count("\n      - name: Build immutable v2 original"),1)
        self.assertEqual(content.count("\n      - name: A2 72-frame native"),1)
        self.assertEqual(content.count("uses: actions/upload-artifact@v4"),1)
        self.assertEqual(content.count("          if grep -Ev "),1)
        self.assertEqual(content.count("git merge-base --is-ancestor"),1)
        self.assertEqual(content.count("sha256sum -c SHA256SUMS"),1)
        self.assertNotIn("\n r009-evidence/changed_paths.txt; then",content)
        self.assertIn("' r009-evidence/changed_paths.txt; then",content)
        self.assertIn("permissions:\n  contents: read",content)
        self.assertEqual(sum(line.startswith("      - name: ") for line in content.splitlines()),6)

    def test_correct_hip_thigh_and_knee_against_exact_original_joint_rest(self):
        from humanization_v2 import v1 as source
        for side in ("L","R"):
            hip=source.POS["hip_"+side]
            knee=source.POS["knee_"+side]
            self.assertAlmostEqual(knee[1],.49,places=6)
            moved,radius,active=trouser_hip_inset(
                "slatePants",hip,knee,.113,"hip_"+side,"knee_"+side)
            self.assertTrue(active)
            self.assertAlmostEqual(moved[1],.794,places=6)
            self.assertGreater(moved[1],.72)
            self.assertLess(moved[1],hip[1])
            self.assertEqual(radius,.106)
            original,mr,changed=trouser_hip_inset(
                "skinWarm",hip,knee,.097,"hip_"+side,"knee_"+side)
            self.assertFalse(changed)
            self.assertEqual(original,hip)
            self.assertEqual(mr,.097)
            c,rs,modified=knee_cap_to_source_joint(
                "slatePants",(hip[0],.34,.006),(.077,.108,.074),"knee_"+side)
            self.assertTrue(modified)
            self.assertEqual(c,knee)
            self.assertEqual(rs,(.078,.086,.076))
            untouched,ur,unchanged=knee_cap_to_source_joint(
                "skinWarm",(hip[0],.34,.006),(.077,.108,.074),"knee_"+side)
            self.assertFalse(unchanged)
            self.assertEqual(untouched,(hip[0],.34,.006))
            self.assertEqual(ur,(.077,.108,.074))
        before=(source.Geometry.tube,source.Geometry.ellipsoid)
        continuous_figure(0)
        self.assertIs(source.Geometry.tube,before[0])
        self.assertIs(source.Geometry.ellipsoid,before[1])
        self.assertTrue(self.receipt["trouser_upper_thigh_tube_starts_inset"])
        self.assertTrue(self.receipt["original_source_kneecaps_aligned_to_joint_rest"])

    def test_shoulder_gusset_source_geometry_and_non_destructive_skin_weights(self):
        from humanization_v2 import v1 as h17
        count=len(SHOULDER_GUSSET_RINGS)*SHOULDER_GUSSET_SIDES
        for which,material in ((0,"coralJacket"),(1,"tealJacket")):
            g=continuous_figure(which)
            coat=g.parts[material]
            all_n=len(coat["p"])//3
            self.assertGreater(all_n,2*count)
            self.assertEqual(len(coat["j"]),4*all_n)
            self.assertEqual(len(coat["w"]),4*all_n)
            self.assertEqual(len(coat["n"]),3*all_n)
            for sign,side,offset in ((-1,"L",all_n-2*count),
                                     (1,"R",all_n-count)):
                self.assertGreater(offset,0)
                local=list(range(offset,offset+count))
                vertices=[coat["p"][3*i:3*i+3] for i in local]
                self.assertTrue(all(sign*v[0] > .10 for v in vertices))
                self.assertTrue(all(1.25 < v[1] < 1.45 for v in vertices))
                shoulder=h17.JIDX["shoulder_"+side]
                chest=h17.JIDX["chest"]
                for i in local:
                    self.assertEqual(coat["j"][4*i:4*i+2],[chest,shoulder])
                    w=coat["w"][4*i:4*i+4]
                    self.assertTrue(all(0<=v<=1 for v in w))
                    self.assertAlmostEqual(sum(w),1.,places=6)
                    normal=coat["n"][3*i:3*i+3]
                    self.assertAlmostEqual(math.sqrt(sum(v*v for v in normal)),1.,places=5)
                first=coat["w"][4*offset]
                last=coat["w"][4*(offset+count-1)]
                self.assertGreater(first,last,
                                   "continuously transfer skin influence chest to shoulder")
                expected=2*(len(SHOULDER_GUSSET_RINGS)-1)*SHOULDER_GUSSET_SIDES
                tris={tuple(coat["i"][k:k+3]) for k in range(0,len(coat["i"]),3)
                      if all(offset<=v<offset+count for v in coat["i"][k:k+3])}
                self.assertEqual(len(tris),expected)
            self.assertFalse(self.receipt["full_body_watertight"])

    def test_same_rig_and_slots_without_promotion(self):
        result=witness(self.source,self.manifest)
        self.assertEqual(result["joints_each"],35)
        self.assertFalse(result["human_visual_accepted"])
        self.assertTrue(self.m["separate_new_geometry_for_alternate"])
        self.assertTrue(self.receipt["contiguous_trunk_neck_head_loft"])
        self.assertTrue(self.receipt["weighted_shoulder_sleeve_root_gussets"])
        self.assertFalse(self.receipt["shoulder_or_body_watertight"])
        self.assertFalse(self.receipt["full_body_watertight"])
        self.assertEqual(self.d["extras"]["wardrobe_contract"]["schema"],
                         "scp.original_wardrobe.v1")
        self.assertFalse(self.m["release_approved"])

    def test_alternate_is_new_geometry_not_a_material_only_clone(self):
        for actor in ACTORS:
            slots=self.m["actor_slots"][actor]
            for old,new in (("top","alt_top"),("bottom","alt_bottom")):
                sig=self.d["meshes"][slots[old]["mesh"]]["primitives"]
                alt=self.d["meshes"][slots[new]["mesh"]]["primitives"]
                self.assertNotEqual(sig,alt)
                self.assertNotEqual(
                    sum(self.d["accessors"][p["attributes"]["POSITION"]]["count"] for p in sig),
                    sum(self.d["accessors"][p["attributes"]["POSITION"]]["count"] for p in alt))
                for prim in alt:
                    positions=accessory(self.d,self.bb,prim["attributes"]["POSITION"])
                    self.assertTrue(all(math.isfinite(v) for xyz in positions for v in xyz))
            self.assertEqual(self.m["cut_styles"][actor]["alt_top"],
                             "cropped_sleeveless_vest_v2")
            self.assertEqual(self.m["cut_styles"][actor]["alt_bottom"],
                             "flared_calf_length_culottes_v2")

    def test_full_body_and_independent_portable_selection(self):
        for index, pair in enumerate((
            ("unclothed","unclothed"),("signature","alternate"),
            ("alternate","signature"),("alternate","alternate"))):
            choices=dict(zip(ACTORS,pair))
            glb=self.root/f"portable_{index}.glb"
            receipt=self.root/f"portable_{index}.json"
            result=export(self.source,self.manifest,glb,receipt,choices)
            d,bb=decode(glb.read_bytes())
            for actor in ACTORS:
                root=next(n for n in d["nodes"] if n["name"]==actor+"_SceneRoot")
                active={slot for slot,entry in self.m["actor_slots"][actor].items()
                        if entry["node"] in root["children"]}
                self.assertEqual(active,set(PRESETS[choices[actor]]) &
                                 set(self.m["actor_slots"][actor]))
                self.assertIn("body",active)
                self.assertEqual(active,set(result["active_layers"][actor]))
            self.assertTrue(result["source_geometry_preserved"])
            self.assertEqual(result["portable_export_contract"],
                             "scp.r009.original_wardrobe_portable_export.v2")
            self.assertEqual(d["skins"],self.d["skins"])
            self.assertEqual(d["animations"],self.d["animations"])
            self.assertEqual(d["meshes"],self.d["meshes"])
            for actor in ACTORS:
                slots=self.m["actor_slots"][actor]
                unwanted=set(slots)-set(PRESETS[choices[actor]])
                self.assertEqual(set(result["inactive_mesh_bindings_removed"][actor]),
                                 unwanted)
                for slot,entry in slots.items():
                    node=d["nodes"][entry["node"]]
                    if slot in unwanted:
                        self.assertNotIn("mesh",node,
                                         "Blender imports inactive orphan meshes")
                        self.assertNotIn("skin",node)
                    else:
                        self.assertIn("mesh",node)
                        self.assertIn("skin",node)

            self.assertEqual(hashlib.sha256(glb.read_bytes()).hexdigest(),
                             result["derived_sha256"])

    def test_portable_export_rejects_output_reuse_and_mutations(self):
        outputs=self.root/"first-v2.glb",self.root/"first-v2.json"
        selected={a:"unclothed" for a in ACTORS}
        original_sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
        export(self.source,self.manifest,*outputs,selected)
        with self.assertRaisesRegex(FileExistsError,
                                    "REFUSE_OVERWRITE_EXISTING_PORTABLE_OUTPUT"):
            export(self.source,self.manifest,*outputs,selected)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),
                         original_sha)
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_RECEIPT_OVERWRITE_REFUSED"):
            export(self.source,self.manifest,self.source,self.root/"forbid.json",
                   selected)

    def test_output_immutability_and_manifest_falsifier(self):
        with self.assertRaisesRegex(ValueError,"IMMUTABLE_OUTPUT_EXISTS"):
            build(self.source,self.root/"changed-manifest.json")
        with self.assertRaisesRegex(ValueError,"OUTPUT_PATH_COLLISION"):
            build(self.root/"same.glb",self.root/"same.glb")
        fake=json.loads(self.manifest.read_text())
        fake["derived_sha256"]="0"*64
        bad=self.root/"bad_manifest.json"
        bad.write_text(json.dumps(fake))
        with self.assertRaisesRegex(ValueError,"SOURCE_MANIFEST_SHA_MISMATCH"):
            export(self.source,bad,self.root/"forged.glb",
                   self.root/"forged.json",{a:"signature" for a in ACTORS})

if __name__=="__main__":unittest.main()
