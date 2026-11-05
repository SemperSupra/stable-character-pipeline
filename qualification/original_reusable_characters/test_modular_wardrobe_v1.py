"""Independent wardrobe interoperability, source/custody and negative controls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from modular_wardrobe_v1 import build,ACTORS,PRESETS,SLOTS
from verify_original_glb import decode,accessory

def witness(glb,manifest):
    raw=Path(glb).read_bytes()
    d,b=decode(raw)
    m=json.loads(Path(manifest).read_text())
    if m.get("schema")!="scp.original_wardrobe_manifest.v1":
        raise ValueError("BAD_MANIFEST_SCHEMA")
    if hashlib.sha256(raw).hexdigest()!=m["derived_sha256"]:
        raise ValueError("SOURCE_DIGEST_MISMATCH")
    contract=d["extras"].get("wardrobe_contract",{})
    if contract.get("schema")!="scp.original_wardrobe.v1":
        raise ValueError("MISSING_WARDROBE_CONTRACT")
    if len(d["skins"])!=2 or any(len(x["joints"])!=35 for x in d["skins"]):
        raise ValueError("INVALID_SHARED_SKELETON")
    if len(d["animations"])!=1 or len(d["animations"][0]["channels"])<60:
        raise ValueError("ANIMATION_MISSING")
    if m["presets"]!={k:list(v) for k,v in PRESETS.items()}:
        raise ValueError("WRONG_PRESETS")
    byname={x["name"]:i for i,x in enumerate(d["nodes"])}
    for i,actor in enumerate(ACTORS):
        slots=m["actor_slots"][actor]
        required={"body","hair","top","bottom","footwear","alt_top","alt_bottom"}
        if not required.issubset(slots):raise ValueError("MISSING_BODY_OR_GARMENT")
        for slot,meta in slots.items():
            node_name=actor+"_Wardrobe_"+slot
            if node_name not in byname or byname[node_name]!=meta["node"]:
                raise ValueError("SLOT_NODE_MISMATCH")
            node=d["nodes"][meta["node"]]
            if node["skin"]!=i or node["mesh"]!=meta["mesh"]:
                raise ValueError("GARMENT_DIFFERENT_SKELETON")
            prims=d["meshes"][node["mesh"]]["primitives"]
            if not prims:raise ValueError("EMPTY_GARMENT")
            for p in prims:
                attrs=p["attributes"]
                joints=accessory(d,b,attrs["JOINTS_0"])
                weights=accessory(d,b,attrs["WEIGHTS_0"])
                if len(joints)!=len(weights):raise ValueError("MISSING_SKIN_WEIGHT")
                for js,ws in zip(joints,weights):
                    if any(j>=35 and v>0 for j,v in zip(js,ws)):
                        raise ValueError("INVALID_BONE_INDEX")
                    if abs(sum(ws)-1)>1e-5:raise ValueError("BAD_WEIGHT_SUM")
        # Verify original source has an actual body covered by separate garment:
        # fully skinned bare legs, feet, arms, torso, neck and head.
        body=d["meshes"][slots["body"]["mesh"]]
        y=[]
        for p in body["primitives"]:
            ys=[xyz[1] for xyz in accessory(d,b,p["attributes"]["POSITION"])]
            y.extend(ys)
        if not (min(y)<.025 and max(y)>1.77):
            raise ValueError("NOT_FULL_BODY_BASE")
        if slots["body"]["mesh"]==slots["top"]["mesh"]:
            raise ValueError("CLOTHING_NOT_SEPARATE")
    return {"schema":"scp.original_wardrobe_independent.v1",
      "source_sha256":hashlib.sha256(raw).hexdigest(),
      "actor_count":2,"joints_each":35,
      "layers":{a:sorted(m["actor_slots"][a]) for a in ACTORS},
      "presets":m["presets"],"animation_frames":72,
      "human_visual_accepted":False}

class WardrobeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.glb=Path(cls.tmp.name)/"wardrobe.glb"
        cls.m=Path(cls.tmp.name)/"wardrobe.json"
        build(cls.glb,cls.m)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_full_body_clothing_distinct_shared_rig(self):
        self.assertEqual(witness(self.glb,self.m)["joints_each"],35)
    def test_base_and_two_outfits_are_separable(self):
        m=json.loads(self.m.read_text())
        self.assertEqual(set(m["presets"]["unclothed"]),{"body","hair"})
        self.assertNotIn("top",m["presets"]["unclothed"])
        self.assertIn("alt_top",m["presets"]["alternate"])
        self.assertNotIn("top",m["presets"]["alternate"])
        self.assertIn("top",m["presets"]["signature"])
        self.assertNotIn("alt_top",m["presets"]["signature"])
    def test_independent_manifest_tamper_fails(self):
        altered=json.loads(self.m.read_text())
        altered["derived_sha256"]="0"*64
        fail=Path(self.tmp.name)/"tampered.json"
        fail.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,"SOURCE_DIGEST_MISMATCH"):
            witness(self.glb,fail)
    def test_garment_must_share_armature(self):
        from rig35_v2 import glb_pack
        doc,bb=decode(self.glb.read_bytes())
        m=json.loads(self.m.read_text())
        target=m["actor_slots"]["AsterOriginal"]["top"]["node"]
        doc["nodes"][target]["skin"]=1
        bad=Path(self.tmp.name)/"bad.glb"
        bad.write_bytes(glb_pack(doc,bb))
        m["derived_sha256"]=hashlib.sha256(bad.read_bytes()).hexdigest()
        manifest=Path(self.tmp.name)/"bad.json"
        manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,"GARMENT_DIFFERENT_SKELETON"):
            witness(bad,manifest)
    def test_deterministic_export(self):
        target=Path(self.tmp.name)/"repeat.glb"
        manifest=Path(self.tmp.name)/"repeat.json"
        build(target,manifest)
        self.assertEqual(target.read_bytes(),self.glb.read_bytes())

if __name__=="__main__":
    unittest.main()
