#!/usr/bin/env python3
"""Non-overwriting, actor-isolated Juniper lower-hem source quality checks."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"original_reusable_characters"),
             str(HERE.parent/"human_fit_candidates")]
from modular_wardrobe_v1 import ACTORS,build
from parametric_morphology_v1 import apply as morph
from original_mage_outfits_v1 import add_original_outfits
from strict_mage_portable_v1 import export as strict
from fit_radial_ablations_v1 import apply as radial
from verify_original_glb import accessory,decode
from motion_hem_candidates_v1 import apply,OPTIONS,SCHEMA,atten,deform

class HemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        r=cls.root=Path(cls.tmp.name)
        build(r/"base.glb",r/"base.json")
        morph(r/"base.glb",r/"base.json",r/"morph.glb",
              r/"morph.json",r/"morph-rec.json")
        add_original_outfits(r/"morph.glb",r/"morph.json",
                             r/"author.glb",r/"author.json",r/"author-rec.json")
        strict(r/"author.glb",r/"author.json",
               r/"strict.glb",r/"strict.json",
               {a:"adventure" for a in ACTORS})
        radial(r/"strict.glb",r/"strict.json",
               r/"source.glb",r/"source.json","juniper_skirt_14")
        cls.raw=(r/"source.glb").read_bytes()
        cls.sha=hashlib.sha256(cls.raw).hexdigest()
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def derived(self,variant,name):
        r=self.root
        out,receipt=r/(name+".glb"),r/(name+".json")
        record=apply(r/"source.glb",r/"source.json",out,receipt,variant)
        self.assertEqual(record["schema"],SCHEMA+".receipt")
        self.assertEqual(record["source_sha256"],self.sha)
        self.assertEqual(record["derived_sha256"],
                         hashlib.sha256(out.read_bytes()).hexdigest())
        self.assertFalse(record["garment_clearance_accepted"])
        self.assertEqual((r/"source.glb").read_bytes(),self.raw)
        return out,record
    def test_all_four_actor_isolated_original_derivatives(self):
        source,bb=decode(self.raw)
        names={n["name"]:i for i,n in enumerate(source["nodes"])}
        meshid=source["nodes"][names["JuniperOriginal_Wardrobe_style_bottom"]]["mesh"]
        for v in OPTIONS:
            with self.subTest(variant=v):
                out,rec=self.derived(v,"case-"+v)
                doc,b=decode(out.read_bytes())
                for key in ("nodes","skins","animations","materials","meshes",
                            "bufferViews"):
                    self.assertEqual(source[key],doc[key],key)
                # POSITION bounds legitimately change when a skirt radius
                # changes; all accessor identity/layout fields stay fixed.
                target_positions={
                    prim["attributes"]["POSITION"]
                    for prim in source["meshes"][meshid]["primitives"]
                }
                for ai,(orig_acc,new_acc) in enumerate(zip(
                        source["accessors"],doc["accessors"])):
                    if ai in target_positions:
                        for k in set(orig_acc)|set(new_acc):
                            if k not in ("min","max"):
                                self.assertEqual(orig_acc.get(k),new_acc.get(k))
                    else:
                        self.assertEqual(orig_acc,new_acc)
                self.assertGreater(rec["changed_skirt_vertices"],50)
                self.assertEqual(doc["extras"]["juniper_motion_hem_trial"]["variant"],v)
                for k,mesh in enumerate(source["meshes"]):
                    for prim in mesh["primitives"]:
                        a=prim["attributes"]
                        for semantic in ("POSITION","NORMAL","JOINTS_0","WEIGHTS_0"):
                            aid=a[semantic]
                            before=accessory(source,bb,aid)
                            after=accessory(doc,b,aid)
                            if k==meshid and semantic in ("POSITION","NORMAL"):
                                if semantic=="POSITION":
                                    self.assertNotEqual(before,after)
                                    for xyz,xyz2 in zip(before,after):
                                        # This geometry touches no waist/collar (>0.91m Y-up)
                                        if xyz[1]>=OPTIONS[v][2]:
                                            self.assertEqual(xyz,xyz2)
                                        self.assertEqual(xyz[1],xyz2[1])
                            else:
                                self.assertEqual(before,after,v+":"+semantic)
    def test_same_variant_deterministic_bytes(self):
        a,x=self.derived("hem_06","det-1")
        b,y=self.derived("hem_06","det-2")
        self.assertEqual(a.read_bytes(),b.read_bytes())
        self.assertEqual(x["derived_sha256"],y["derived_sha256"])
    def test_no_overwrite_source(self):
        with self.assertRaisesRegex(ValueError,"HEM_SOURCE_OVERWRITE"):
            apply(self.root/"source.glb",self.root/"source.json",
                  self.root/"source.glb",self.root/"bad01.json","hem_03")
    def test_no_overwrite_existing_candidate(self):
        a,_=self.derived("hem_03","again")
        with self.assertRaisesRegex(FileExistsError,"HEM_REFUSE_EXISTING_OUTPUT"):
            apply(self.root/"source.glb",self.root/"source.json",
                  a,self.root/"again.json","hem_03")
    def test_reject_wrong_source_sha_and_preset(self):
        p=json.loads((self.root/"source.json").read_text())
        p["derived_sha256"]="f"*64
        x=self.root/"forged.json"; x.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError,"HEM_SOURCE_NOT_PINNED"):
            apply(self.root/"source.glb",x,
                  self.root/"bad02.glb",self.root/"bad02.json","hem_06")
        with self.assertRaisesRegex(ValueError,"HEM_VARIANT_UNKNOWN"):
            apply(self.root/"source.glb",self.root/"source.json",
                  self.root/"bad03.glb",self.root/"bad03.json","magic")
    def test_smooth_weight_taper_at_endpoints(self):
        for v,(grow,lo,hi) in OPTIONS.items():
            a,b=atten(hi+.01,lo,hi)
            self.assertEqual(a,0.);self.assertEqual(b,0.)
            c,d=atten(lo-.01,lo,hi)
            self.assertEqual(c,1.);self.assertEqual(d,0.)
            e,f=atten((lo+hi)/2,lo,hi)
            self.assertAlmostEqual(e,.5);self.assertLess(f,0.)
    def test_normal_renormalization_and_true_noop(self):
        # Construct a genuinely sized original ring fixture: deformation
        # must affect >50 vertices before the source tool permits output.
        coords=[((.2 if i%2 else -.2)+.001*i,.65,.15)
                for i in range(60)]+[(.22,1.1,.14)]
        normals=[(.8,.2,.56)]*len(coords)
        new,n,c=deform(coords,normals,.06,.66,.91)
        self.assertEqual(new[-1],coords[-1])
        self.assertEqual(n[-1],normals[-1])
        self.assertEqual(c,60)
        for v in n[:60]:
            self.assertAlmostEqual(sum(x*x for x in v),1.,places=5)

if __name__=="__main__":unittest.main()
