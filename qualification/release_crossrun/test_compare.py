import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location("crossrun",Path(__file__).with_name("compare.py"))
crossrun=importlib.util.module_from_spec(spec)
spec.loader.exec_module(crossrun)

def encoded(root, label, color):
    path=root/(label+".mp4")
    subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-f","lavfi",
        "-i",f"color=c={color}:s=64x64:r=12:d=0.5",
        "-c:v","libx264","-pix_fmt","yuv420p",str(path)],check=True,capture_output=True,timeout=30)
    return path.read_bytes()

def archive(root, name, source_rights="ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            oblique="black", tamper_video=False, fullbody="FAIL_ABSTRACT_LIMBS_ONLY"):
    source=(json.dumps({"schema":"scp.walk_w7a_original_approach.v1","rights":source_rights},
                       sort_keys=True)+"\n").encode()
    glb=b"original self-authored synthetic GLB"
    blend=b"original self-authored synthetic blend"
    video={"OriginalFront":encoded(root,name+"front","black"),
           "OriginalOblique":encoded(root,name+"oblique",oblique)}
    witness={"source_sha256":crossrun.sha(source),
             "glb_sha256":crossrun.sha(glb),
             "blend_sha256":crossrun.sha(blend),
             "video_sha256":{k:crossrun.sha(v) for k,v in video.items()},
             "full_body":fullbody,
             "private_r009":"NOT_RUN_NOT_ADMITTED"}
    media=root/(name+"-media.zip")
    evidence=root/(name+"-evidence.zip")
    with zipfile.ZipFile(media,"w") as z:
        z.writestr("original_synthetic_24frame_skinned.glb",glb)
        z.writestr("original_source_grounded_24frame_native.blend",blend)
        for camera,raw in video.items():
            if camera=="OriginalOblique" and tamper_video:raw=raw+b"changed"
            z.writestr("rendered/"+camera+".mp4",raw)
    with zipfile.ZipFile(evidence,"w") as z:
        z.writestr("forward/source.json",source)
        z.writestr("receipt/witness.json",json.dumps(witness))
        z.writestr("receipt/release-admission.json",json.dumps({"status":"UNKNOWN","code":"DRAFT_NOT_PROMOTED"}))
    return media,evidence

class OriginalCrossRunTests(unittest.TestCase):
    def test_same_source_clean_front_and_oblique_drift(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,ae=archive(p,"baseline");b,be=archive(p,"candidate",oblique="white")
            report=crossrun.compare(a,ae,b,be)
            self.assertEqual(report["status"],"OBSERVED_DECODED_DRIFT_NOT_SCIENTIFIC_ACCEPTANCE")
            self.assertEqual([x["frames_total"] for x in report["cameras"]],[6,6])
            self.assertEqual(report["cameras"][0]["frames_equal_rgb"],6)
            self.assertLess(report["cameras"][1]["frames_equal_rgb"],6)
            self.assertGreater(report["cameras"][1]["max_rgb_delta"],0)
            self.assertEqual(report["private_r009"],"NOT_RUN_NOT_ADMITTED")
    def test_identical_pixels_do_not_claim_human_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,ae=archive(p,"baseline");b,be=archive(p,"candidate")
            report=crossrun.compare(a,ae,b,be)
            self.assertEqual(report["status"],"DECODED_FRAMES_EQUAL_NOT_SCIENTIFIC_ACCEPTANCE")
            self.assertEqual(report["human_behavior"],"FAIL_ABSTRACT_LIMBS_ONLY")
    def test_video_sha_tamper_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,ae=archive(p,"baseline");b,be=archive(p,"candidate",tamper_video=True)
            with self.assertRaisesRegex(ValueError,"ORIGINAL_VIDEO_SHA_DISAGREES_WITH_WITNESS"):
                crossrun.compare(a,ae,b,be)
    def test_wrong_source_rights_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,ae=archive(p,"baseline");b,be=archive(p,"candidate",source_rights="PRIVATE")
            with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_SCHEMA"):
                crossrun.compare(a,ae,b,be)
    def test_false_natural_behavior_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,ae=archive(p,"baseline");b,be=archive(p,"candidate",fullbody="PASS")
            with self.assertRaisesRegex(ValueError,"SOURCE_OR_FIRST_FAILURE_NOT_PRESERVED"):
                crossrun.compare(a,ae,b,be)
    def test_different_native_source_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,ae=archive(p,"baseline");b,be=archive(p,"candidate",source_rights="ORIGINAL_SELF_AUTHORED_SYNTHETIC")
            with zipfile.ZipFile(be,"a") as z:
                z.writestr("forward/source.json",b"replaced")
            with self.assertRaisesRegex(ValueError,"DUPLICATE_ORIGINAL_ZIP_MEMBER"):
                crossrun.compare(a,ae,b,be)

if __name__=="__main__":unittest.main()
