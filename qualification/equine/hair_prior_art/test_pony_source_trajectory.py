import copy
import math
import unittest
from pony_source_trajectory import classify,SCHEMA

def fixture():
    guides=[]
    for region,ids in {"mane":(20,21),"forelock":(500,600),"tail":(750,1000)}.items():
        for card in ids:
            root=(.25,0.,.8)
            bone=("head" if card==20 else "neck") if region=="mane" else (
                "tail_2" if card==750 else "tail_3") if region=="tail" else "head"
            guides.append({"card_id":card,"region":region,"owner_bone":bone,
                "samples":[{"frame":f,"root_m":list(root),"tip_m":[.25,0.,.6]} for f in range(1,49)]})
    return {"schema":SCHEMA,"source_kind":"original_synthetic","source_blend_sha256":"a"*64,"rig":"PonyRig30",
            "cards_total":1050,"vertices_per_card":10,"fps":24,"frames":48,
            "guides":guides,"visual_science_hold":"KEEP"}
class Tests(unittest.TestCase):
    def test_source_valid_is_not_science(self):
        a=fixture();r=classify(a)
        self.assertEqual(r["verdict"],"PASS_REAL_SOURCE_GEOMETRY_ONLY")
        self.assertFalse(r["physical_hair_simulation_proven"])
        self.assertFalse(r["release_admission"])
        self.assertEqual(r,classify(a))
    def test_hostile_missing_fake_source_and_motion(self):
        attacks=[
         lambda x:x["guides"].pop(),
         lambda x:x["guides"][0]["samples"].pop(),
         lambda x:x["guides"][0]["samples"][9].update(frame=8),
         lambda x:x["guides"][0]["samples"][9].update(root_m=[math.nan,0,1]),
         lambda x:x["guides"][0]["samples"][9].update(root_m=[9,0,0]),
         lambda x:x["guides"][0].update(card_id=750),
         lambda x:x.update(source_kind="unvetted_person_photo"),
         lambda x:x.update(rig="PonyRig25"),
         lambda x:x.update(visual_science_hold="PASS"),
         lambda x:x["guides"][0].update(owner_bone="unknown"),
        ]
        for i,fn in enumerate(attacks):
            with self.subTest(i=i):
                x=fixture();fn(x)
                with self.assertRaises(ValueError):classify(x)
    def test_no_silent_extra_source_metadata(self):
        x=fixture();x["private_path"]="/secret"
        with self.assertRaises(ValueError):classify(x)
if __name__=="__main__":unittest.main()
