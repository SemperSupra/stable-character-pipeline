"""Hostile independent W8 crosswalk fixture; actual native execution is separate."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/"walk_w7a"))
from approach_source import generate
from crosswalk import audit,RIGHTS,ACTORS,LEGS

def fixture(profile):
    source=generate(profile)
    source_raw=(json.dumps(source,sort_keys=True)+"\n").encode()
    sh=hashlib.sha256(source_raw).hexdigest()
    receipt={"source_sha256":sh,"blend_sha256":"a"*64,
             "rights":RIGHTS,"frame_count":24}
    native={"schema":"scp.walk_w8_native_sixbone_joint_observation.v1",
            "source_sha256":sh,"blend_sha256":"a"*64,"rights":RIGHTS,
            "profile":profile,"fps":12,
            "native_evaluation":"ACTUAL_BLENDER_EVALUATED_ARMATURE_NOT_BIOLOGICAL",
            "observations":[]}
    sole=[]
    for t in range(24):
        n={"tick":t,"actors":[]};f={"frame":t,"actors":[]}
        for ai,actor in enumerate(source["actors"]):
            o={"id":actor["id"],"bones":6,"legs":[]}
            w={"name":actor["id"],"legs":[]}
            for sl in actor["frames"][t]["legs"]:
                o["legs"].append({"id":sl["id"],"hip":list(sl["hip"]),
                    "knee":list(sl["knee"]),"ankle":list(sl["ankle"]),
                    "foot_head":list(sl["ankle"]),"foot_tail":list(sl["toe"]),
                    "leg_bone_count":3})
                w["legs"].append({"id":sl["id"],"state":sl["state"],
                    "heel":list(sl["heel"]),"toe":list(sl["toe"])})
            n["actors"].append(o);f["actors"].append(w)
        native["observations"].append(n);sole.append(f)
    return source_raw,receipt,native,sole

class W8ROM(unittest.TestCase):
    def setUp(self):
        self.args=list(fixture("forward"))
    def ok(self):
        return audit(*self.args)
    def red(self,code):
        with self.assertRaisesRegex(ValueError,code):self.ok()
    def test_source_fixture_forward(self):
        x=self.ok()
        self.assertEqual(x["status"],"PASS_SYNTHETIC_NATIVE_SOURCE_KINEMATICS_ONLY")
        self.assertEqual(x["biological_jcs"],"UNKNOWN_NO_SOURCE_APPROVED_ANATOMICAL_FRAME")
    def test_source_fixture_outward(self):
        self.args=list(fixture("outward"));self.assertEqual(self.ok()["frames"],24)
    def test_wrong_native_source_hash(self):
        self.args[2]["source_sha256"]="f"*64;self.red("IMMUTABLE_SHA")
    def test_wrong_blend_hash(self):
        self.args[2]["blend_sha256"]="0"*64;self.red("IMMUTABLE_SHA")
    def test_lost_native_bone(self):
        self.args[2]["observations"][0]["actors"][0]["bones"]=5;self.red("SIX_BONE")
    def test_wrong_observed_knee(self):
        self.args[2]["observations"][3]["actors"][0]["legs"][0]["knee"][2]+=.04
        self.red("JOINT_MISMATCH")
    def test_reversed_native_knee(self):
        knee=self.args[2]["observations"][6]["actors"][0]["legs"][0]["knee"]
        hip=self.args[2]["observations"][6]["actors"][0]["legs"][0]["hip"]
        knee[1]=2*hip[1]-knee[1];self.red("JOINT_MISMATCH")
    def test_fake_timestamp(self):
        self.args[2]["observations"][12]["tick"]=11;self.red("TICK_OR_ACTOR")
    def test_fake_source_clock(self):
        s=json.loads(self.args[0]);s["actors"][0]["frames"][9]["time_den"]=30
        self.args[0]=(json.dumps(s,sort_keys=True)+"\n").encode()
        self.args[1]["source_sha256"]=hashlib.sha256(self.args[0]).hexdigest()
        self.args[2]["source_sha256"]=self.args[1]["source_sha256"]
        self.red("EXACT_CLOCK")
    def test_reversed_leg_homology(self):
        self.args[2]["observations"][7]["actors"][0]["legs"][0]["id"]="Right"
        self.red("LEG_ID")
    def test_false_foot_label(self):
        self.args[3][5]["actors"][0]["legs"][0]["state"]="swing" \
           if self.args[3][5]["actors"][0]["legs"][0]["state"]=="stance" else "stance"
        self.red("LEG_ID_OR_CONTACT_LABEL")
    def test_wrong_heel(self):
        self.args[3][4]["actors"][0]["legs"][0]["heel"][0]+=.015
        self.red("SOURCE_NATIVE_FOOT")
    def test_static_actors(self):
        s=json.loads(self.args[0])
        for actor in s["actors"]:
            first=actor["frames"][0]["root_x"]
            for f in actor["frames"]:f["root_x"]=first
        self.args[0]=(json.dumps(s,sort_keys=True)+"\n").encode()
        self.args[1]["source_sha256"]=hashlib.sha256(self.args[0]).hexdigest()
        self.args[2]["source_sha256"]=self.args[1]["source_sha256"]
        self.red("NOT_APPROACHING")
    def test_wrong_native_claim(self):
        self.args[2]["native_evaluation"]="HUMAN_BIOLOGICAL_JCS_PASS"
        self.red("UNAUTHORIZED")
    def test_no_nonfinite(self):
        self.args[2]["observations"][2]["actors"][0]["legs"][0]["hip"][1]=float("nan")
        self.red("NONFINITE_JOINT")
    def test_absent_frame(self):
        self.args[2]["observations"].pop();self.red("FRAME_COVERAGE")
if __name__=="__main__":unittest.main()
