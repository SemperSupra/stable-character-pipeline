"""Independent source/skin/joint/animation witness for original-only 35-joint v2."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from humanization_v2 import generate
from rig35_v2 import main_expand
from verify_original_glb import decode, accessory

def witness(path):
    raw=Path(path).read_bytes()
    d,b=decode(raw)
    if d.get("extras",{}).get("rig_profile")!="ORIGINAL_FUNCTIONAL_35JOINT_RESEARCH":
        raise ValueError("BAD_RIG_PROFILE")
    if d["extras"].get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("BAD_SOURCE_CLASS")
    if d["extras"].get("human_gait_acceptance")!="UNKNOWN":
        raise ValueError("FALSE_HUMAN_GAIT_PASS")
    if len(d.get("skins",[]))!=2 or len(d.get("meshes",[]))!=2:
        raise ValueError("BAD_DUAL_SOURCE_COUNT")
    edited={}
    for actor,skin,mesh in zip(("AsterOriginal","JuniperOriginal"),d["skins"],d["meshes"]):
        if len(skin["joints"])!=35 or len(set(skin["joints"]))!=35:
            raise ValueError("BAD_35_JOINT_COUNT")
        matrices=accessory(d,b,skin["inverseBindMatrices"])
        if len(matrices)!=35:raise ValueError("BAD_INVERSE_BIND")
        names=[d["nodes"][n]["name"] for n in skin["joints"]]
        prefixes=[f"{actor}_clavicle_{x}" for x in ("L","R")]
        prefixes += [f"{actor}_{a}_{x}" for x in ("L","R") for a in ("heel","ball","toe")]
        prefixes += [f"{actor}_finger{i}_{side}" for side in ("L","R") for i in range(5)]
        if not all(x in names for x in prefixes):raise ValueError("MISSING_FUNCTIONAL_EXTRA_BONE")
        weighted=set()
        for prim in mesh["primitives"]:
            attrs=prim["attributes"]
            pos=accessory(d,b,attrs["POSITION"])
            joints=accessory(d,b,attrs["JOINTS_0"])
            weights=accessory(d,b,attrs["WEIGHTS_0"])
            if len(pos)!=len(joints) or len(pos)!=len(weights):
                raise ValueError("SKIN_VERTEX_LENGTH")
            for xyz,ja,wa in zip(pos,joints,weights):
                if not all(math.isfinite(x) for x in xyz+wa):raise ValueError("NONFINITE")
                if abs(sum(wa)-1)>1e-5:raise ValueError("WEIGHT_SUM")
                for index,weight in zip(ja,wa):
                    if index>=35:raise ValueError("OUT_OF_RANGE")
                    if index>=17 and weight>0:weighted.add(index)
        for role in ("clavicle","heel","ball","toe","finger"):
            if not any(names[j].split(actor+"_")[-1].startswith(role) for j in weighted):
                raise ValueError("UNWEIGHTED_CONTROL:"+role)
        edited[actor]=sorted(names[i] for i in weighted)
    animation=d["animations"][0]
    channels=animation["channels"]
    controls={d["nodes"][c["target"]["node"]]["name"] for c in channels}
    for actor in edited:
        for name in edited[actor]:
            if name not in controls:raise ValueError("UNANIMATED_WEIGHTED_CONTROL:"+name)
    if len(channels)<58:raise ValueError("INSUFFICIENT_ANIMATION")
    return {"sha256":hashlib.sha256(raw).hexdigest(),
            "weighted_extra_controls":edited,"frame_count":72,"science":"UNKNOWN"}

class Rig35Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.old=Path(cls.tmp.name)/"base17.glb"
        cls.new=Path(cls.tmp.name)/"augmented35.glb"
        generate(cls.old)
        cls.receipt=main_expand(cls.old,cls.new)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_exact_rig_and_glb_source(self):
        result=witness(self.new)
        self.assertEqual(result["frame_count"],72)
        self.assertEqual(self.receipt["per_actor_joints"],35)
        self.assertNotEqual(self.receipt["original_sha256"],self.receipt["derived_sha256"])
    def test_determinism(self):
        again=Path(self.tmp.name)/"again35.glb"
        main_expand(self.old,again)
        self.assertEqual(self.new.read_bytes(),again.read_bytes())
    def test_missing_extra_joint_is_rejected(self):
        from rig35_v2 import glb_pack
        raw=self.new.read_bytes()
        d,b=decode(raw)
        d["skins"][0]["joints"].pop()
        bad=Path(self.tmp.name)/"bad.glb"
        bad.write_bytes(glb_pack(d,b))
        with self.assertRaisesRegex(ValueError,"BAD_35_JOINT_COUNT"):witness(bad)
    def test_fabricated_science_pass_rejected(self):
        from rig35_v2 import glb_pack
        d,b=decode(self.new.read_bytes())
        d["extras"]["human_gait_acceptance"]="PASS"
        bad=Path(self.tmp.name)/"fabricated.glb"
        bad.write_bytes(glb_pack(d,b))
        with self.assertRaisesRegex(ValueError,"FALSE_HUMAN_GAIT_PASS"):witness(bad)
if __name__=="__main__":unittest.main()
