"""Source-safe RC0 bridge adversarial cases; no Blender or private inputs."""
import importlib.util, json, hashlib, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("bridge",Path(__file__).with_name("bridge.py"))
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
def put(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x)+"\n")
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class BridgeTest(unittest.TestCase):
    def fixtures(self,root):
        p=root/"source";(p/"rendered").mkdir(parents=True)
        g=p/"original_synthetic_24frame_skinned.glb";g.write_bytes(b"original synthetic glb")
        f=p/"original_source_grounded_24frame_native.blend";f.write_bytes(b"original synthetic blend")
        binary=root/"releasegate-bin";binary.write_bytes(b"test-only release gate fixture")
        put(p/"source.json",{"schema":"scp.walk_w7a_original_approach.v1",
            "profile":"forward","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","fps_num":12,
            "actors":[{"id":"CobaltOriginal","frames":[{}]*24},{"id":"MarigoldOriginal","frames":[{}]*24}]})
        source=h(p/"source.json")
        put(p/"source_motion_receipt.json",{"source_sha256":source,
            "glb_sha256":h(g),"blend_sha256":h(f),"frame_count":24,"fps_num":12,
            "full_body":"FAIL_ABSTRACT_LIMBS_ONLY","human_anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM"})
        cam=[];observed=[]
        for name in ("OriginalFront","OriginalOblique"):
            v=p/"rendered"/(name+".mp4");v.write_bytes(("public synthetic "+name).encode())
            cam.append({"camera":name,"video_sha256":h(v),"frame_count":24})
            observed.append({"camera":name,"video_sha256":h(v),"status":"PASS_L1_VIDEO_ONLY"})
        put(p/"rendered/native_render_receipt.json",
            {"source_motion_sha256":source,"rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","cameras":cam})
        put(p/"rendered/independent_cross_camera_rollup.json",
            {"status":"PASS_ALL_REQUIRED_VIEWS_L1_ONLY","source_motion_sha256":source,"cameras":observed})
        return p,binary
    def test_source_safe_draft_with_real_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,b=self.fixtures(root)
            w,m=bridge.join(p,"a"*40,b,root/"out")
            self.assertEqual(m["phase"],"draft")
            self.assertEqual(m["gates"]["behavior"]["status"],"FAIL")
            self.assertEqual(w["private_r009"],"NOT_RUN_NOT_ADMITTED")
    def test_video_swap_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,b=self.fixtures(root)
            (p/"rendered/OriginalOblique.mp4").write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError,"VIDEO_SHA_L1_OR_CLOCK"):
                bridge.join(p,"a"*40,b,root/"out")
    def test_fullbody_false_pass_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,b=self.fixtures(root)
            receipt=bridge.read(p/"source_motion_receipt.json");receipt["full_body"]="PASS"
            put(p/"source_motion_receipt.json",receipt)
            with self.assertRaisesRegex(ValueError,"FIRST_FAILURE_NOT_PRESERVED"):
                bridge.join(p,"a"*40,b,root/"out")
    def test_wrong_rights_or_alias_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,b=self.fixtures(root)
            src=bridge.read(p/"source.json");src["rights"]="PRIVATE"
            put(p/"source.json",src)
            with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_PROFILE"):
                bridge.join(p,"a"*40,b,root/"out")
    def test_source_actor_casefold_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,b=self.fixtures(root)
            src=bridge.read(p/"source.json");src["actors"][1]["id"]="cobaltoriginal"
            put(p/"source.json",src)
            with self.assertRaisesRegex(ValueError,"SOURCE_ACTORS_OR_CLOCK"):
                bridge.join(p,"a"*40,b,root/"out")
if __name__=="__main__":unittest.main()
