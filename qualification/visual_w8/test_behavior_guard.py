"""W8 behavioural admission guard hostile fixture, no invented video-model evidence."""
import copy,hashlib,json,math,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/"walk_w7a"))
from approach_source import generate
from behavior_guard import audit,CAMERAS,ACTORS,SIDES

def fixture():
    source=(json.dumps(generate("forward"),sort_keys=True)+"\n").encode()
    sh=hashlib.sha256(source).hexdigest()
    blend="b"*64
    native={"source_sha256":sh,"blend_sha256":blend,"rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC"}
    cameras=[];checks=[];views={}
    for cam in CAMERAS:
        video=(cam.encode()*300)[:2500]
        digest=hashlib.sha256(video).hexdigest()
        cameras.append({"camera":cam,"video_sha256":digest})
        checks.append({"camera":cam,"video_sha256":digest,"status":"PASS_L1_VIDEO_ONLY"})
        views[cam]={"video":video,"qa":{"schema":"scp.visualqa.l1_video.v1",
                 "source_sha256":digest,"frames_decoded":24,"video":{"rate":"12/1"},
                 "status":"PASS_L1_VIDEO_ONLY","failures":[]}}
    render={"schema":"scp.walk_w6a_proxy_multiview.v1","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "source_motion_sha256":sh,"original_w5d_blend_sha256":blend,
            "cameras":cameras,"profile":"forward",
            "W8_arm_motion":"ACTUAL_KEYED_RIGID_UPPER_PROXY_24FRAME",
            "torso_arm_skinning":"NOT_DEFORM_RIGGED",
            "natural_human_behavior":"UNKNOWN_NO_INDEPENDENT_NORMATIVE_MODEL"}
    frames=[]
    for t in range(24):
        frame={"frame":t,"actors":[]}
        for actor in ACTORS:
            arms=[]
            for j,side in enumerate(SIDES):
                sign=1 if j==0 else -1
                arms.append({"side":side,
                   "upper_arm_x_rad":.28*math.sin(2*math.pi*t/12)*sign,
                   "hand_local_y":.20*math.sin(2*math.pi*t/12)*sign})
            frame["actors"].append({"id":actor,"arms":arms})
        frames.append(frame)
    upper={"schema":"scp.walk_w8a_observed_upper_proxy.v1",
           "source_motion_sha256":sh,"original_blend_sha256":blend,"frames":frames}
    rollup={"source_motion_sha256":sh,"source_blend_sha256":blend,
            "profile":"forward","cameras":checks,"status":"PASS_ALL_REQUIRED_VIEWS_L1_ONLY"}
    return [source,native,render,upper,rollup,views]

class BehaviorGuard(unittest.TestCase):
    def setUp(self):
        self.args=fixture()
    def get(self):return audit(*self.args)
    def red(self,code):
        with self.assertRaisesRegex(ValueError,code):self.get()
    def test_positive_source_motion_not_a_human_pass(self):
        r=self.get()
        self.assertEqual(r["source_arm_motion"],"PASS_ACTUAL_BLENDER_RIGID_UPPER_PROXY_ONLY")
        self.assertEqual(r["status"],"FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED")
        self.assertEqual(r["independent_vision_video_behavior_critic"],"NOT_RUN_NO_ADMITTED_MODEL")
    def test_negative_true_L1_still_red(self):
        cam=CAMERAS[0]
        self.args[5][cam]["qa"]["status"]="FAIL"
        self.args[5][cam]["qa"]["failures"]=["FREEZE_SPAN_DETECTED"]
        self.args[4]["cameras"][0]["status"]="FAIL"
        self.args[4]["status"]="FAIL_L1_ANY_REQUIRED_VIEW"
        self.assertEqual(self.get()["status"],"FAIL_L1_AND_FULLBODY_PROXY_UNQUALIFIED")
    def test_false_l1_status_forgery(self):
        self.args[5][CAMERAS[0]]["qa"]["status"]="FAIL"
        self.red("L1_STATUS_CROSSWALK")
    def test_stale_video_sha(self):
        self.args[5][CAMERAS[0]]["video"]+=b"x"
        self.red("DIFFERENT_VIDEO")
    def test_missing_camera(self):
        self.args[5].pop(CAMERAS[1])
        self.red("MISSING_REQUIRED_VIDEO")
    def test_false_skinned_human(self):
        self.args[2]["torso_arm_skinning"]="HUMAN_SKINNED_PASS"
        self.red("FALSE_NATURAL_HUMAN_PROMOTION")
    def test_source_identity_mismatch(self):
        self.args[3]["source_motion_sha256"]="0"*64
        self.red("SOURCE_DIGEST")
    def test_model_claim_forgery(self):
        self.args[2]["natural_human_behavior"]="PASS"
        self.red("FALSE_NATURAL_HUMAN_PROMOTION")
    def test_static_source_arms(self):
        for f in self.args[3]["frames"]:
            for a in f["actors"]:
                for arm in a["arms"]:arm["upper_arm_x_rad"]=0
        self.red("NATIVE_ARM_NOT_AUTHORED")
    def test_wrong_arm_sign(self):
        self.args[3]["frames"][3]["actors"][0]["arms"][0]["upper_arm_x_rad"]=-.28
        self.red("NATIVE_ARM_NOT_AUTHORED")
    def test_nonfinite_arm(self):
        self.args[3]["frames"][1]["actors"][0]["arms"][0]["upper_arm_x_rad"]=float("nan")
        self.red("NONFINITE")
    def test_wrong_frame(self):
        self.args[3]["frames"][11]["frame"]=7
        self.red("UPPER_FRAME_CLOCK")
    def test_false_camera_rollup(self):
        self.args[4]["status"]="PASS_HUMAN_ACCEPTED"
        self.red("ROLLUP")
    def test_wrong_original_blend(self):
        self.args[4]["source_blend_sha256"]="c"*64
        self.red("BLEND_CUSTODY")
    def test_wrong_actor_order(self):
        self.args[3]["frames"][1]["actors"][0]["id"]=ACTORS[1]
        self.red("UPPER_ARM_SET")
if __name__=="__main__":unittest.main()
