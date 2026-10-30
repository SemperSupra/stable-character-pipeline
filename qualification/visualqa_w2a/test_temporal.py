"""Independent W2A adversarial real-video and source-clock tests."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from temporal import frame_difference, decode_actual, analyze, read_source, sha


class TemporalWitnessTests(unittest.TestCase):
    def create(self, root, source):
        path=root/"actual.mp4"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-f","lavfi","-i",source,
                        "-pix_fmt","yuv420p","-c:v","libx264",str(path)],check=True,timeout=45)
        return path

    def input(self,root,video):
        source_sha=hashlib.sha256(b"staged-original-blend").hexdigest()
        base=[{"actor":"A","leg":"Left","hip":[0,0,2],"knee":[0,0.3,1],"ankle":[0,0,0]},
              {"actor":"A","leg":"Right","hip":[1,0,2],"knee":[1,0.3,1],"ankle":[1,0,0]}]
        frames=[]
        for tick, dx in ((0,0.0),(12,0.3),(23,0.6)):
            p=json.loads(json.dumps(base))
            for leg in p:
                for name in ("hip","knee","ankle"):
                    leg[name][0]+=dx
            frames.append({"tick":tick,"poses":p})
        witness={"schema":"scp.visualqa.l2_knee_input.v1",
                 "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
                 "source_sha256":source_sha,"frames":frames}
        native={"source_rights":witness["rights"],"blend_sha256":source_sha,
                "video_sha256":sha(video)}
        w,n=root/"poses.json",root/"native.json"
        w.write_text(json.dumps(witness));n.write_text(json.dumps(native))
        return w,n

    def test_byte_level_motion_and_noise(self):
        self.assertEqual(frame_difference(bytes([0]*16),bytes([0]*16))["mean_abs_gray"],0)
        self.assertEqual(frame_difference(bytes([0]*16),bytes([1]*16))["fraction_pixels_delta_gt8"],0)
        self.assertEqual(frame_difference(bytes([0]*16),bytes([100]*16))["fraction_pixels_delta_gt8"],1)

    def test_actual_moving_h264_and_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);video=self.create(root,"testsrc2=size=128x72:rate=12:duration=2")
            w,n=self.input(root,video)
            result=analyze(video,w,n,root/"w2a.json")
            self.assertEqual(result["status"],"OBSERVED_RESEARCH_ONLY")
            self.assertEqual(result["frames_decoded"],24)
            self.assertEqual(len(result["source_vs_pixel_intervals"]),2)
            self.assertEqual(len(result["per_frame_transition"]),23)
            self.assertTrue((root/"w2a.json").exists())

    def test_frozen_actual_h264_is_observed_not_promoted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);video=self.create(root,"color=c=black:s=128x72:r=12:d=2")
            w,n=self.input(root,video)
            result=analyze(video,w,n,root/"w2a.json")
            self.assertEqual(result["suspect_intervals"],2)
            self.assertEqual(result["anatomical_acceptance"],"UNKNOWN_NOT_PERFORMED")

    def test_wrong_video_hash_abstains_with_error(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);video=self.create(root,"testsrc2=size=128x72:rate=12:duration=2")
            w,n=self.input(root,video)
            native=json.loads(n.read_text());native["video_sha256"]="0"*64;n.write_text(json.dumps(native))
            with self.assertRaisesRegex(ValueError,"CUSTODY"):
                analyze(video,w,n,root/"w2a.json")

    def test_forged_source_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);video=self.create(root,"testsrc2=size=128x72:rate=12:duration=2")
            w,n=self.input(root,video)
            data=json.loads(w.read_text());data["frames"][1]["tick"]=0;w.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"FRAME_CLOCK"):
                read_source(w,video,n)


if __name__=="__main__":
    unittest.main()
