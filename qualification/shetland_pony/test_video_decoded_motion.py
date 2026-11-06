import json
import os
import tempfile
import unittest
from pathlib import Path
from video_decoded_motion import W,H,FRAMES,InvalidEvidence,inspect,observe_bytes

class DecodedVideoQA(unittest.TestCase):
    def setUp(self):
        self.frames=[bytes([i%256])*(W*H) for i in range(FRAMES)]

    def test_all_observed_frames(self):
        r=observe_bytes(self.frames)
        self.assertTrue(r["technical_motion_observed"])
        self.assertEqual(r["unique_decoded_frame_shas"],48)
        self.assertEqual(r["longest_exact_freeze_run"],1)

    def test_frozen_video_rejected(self):
        r=observe_bytes([bytes([17])*(W*H)]*FRAMES)
        self.assertFalse(r["technical_motion_observed"])
        self.assertEqual(r["longest_exact_freeze_run"],48)

    def test_partial_long_freeze_rejected(self):
        r=observe_bytes([bytes([17])*(W*H)]*38+self.frames[:10])
        self.assertFalse(r["technical_motion_observed"])

    def test_unique_one_pixel_noise_is_not_real_motion(self):
        frames=[]
        for i in range(FRAMES):
            frame=bytearray([17])*(W*H)
            frame[i]=i+1
            frames.append(bytes(frame))
        result=observe_bytes(frames)
        self.assertEqual(result["unique_decoded_frame_shas"],FRAMES)
        self.assertFalse(result["technical_motion_observed"])

    def test_wrong_frame_count_and_dimensions(self):
        for frames in (self.frames[:47],self.frames+[self.frames[-1]]):
            with self.assertRaisesRegex(InvalidEvidence,"frame count"):
                observe_bytes(frames)
        frames=list(self.frames);frames[17]=b"wrong"
        with self.assertRaisesRegex(InvalidEvidence,"geometry"):
            observe_bytes(frames)

    def test_forged_source_sha_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"diagnostic_video_receipt.json").write_text(json.dumps({
                "schema":"equine.motion.mp4.custody.v1","source_sha256":"a"*64,
                "videos":{v+".mp4":{"bytes":1000,"sha256":"a"*64,
                "decoded_frames":48,"source_render_unique_frames":48}
                for v in ("side","face","mane","tail")}}))
            (root/"diagnostic_frames_receipt.json").write_text(json.dumps({
                "schema":"equine.motion.fourviews.v1","source_sha256":"b"*64,
                "views":{v:{"frames":48} for v in ("side","face","mane","tail")}}))
            with self.assertRaisesRegex(InvalidEvidence,"SHA drift"):
                inspect(root)

    def test_native_generated_bytes_and_scientific_holds(self):
        artifact=os.environ.get("SCP_NATIVE_FOURVIEW_EVIDENCE")
        if not artifact:self.skipTest("native video bytes not in independent unit run")
        result=inspect(artifact)
        self.assertEqual(result["decoded_video_motion"],"TECHNICAL_VARIATION_OBSERVED")
        self.assertEqual(len(result["view_evidence"]),4)
        self.assertTrue(all(result["view_evidence"][v]["decoded_frames"]==48
                            for v in ("side","face","mane","tail")))
        self.assertFalse(result["visual_acceptance"])
        self.assertFalse(result["release_or_CPE_admission"])
        self.assertEqual(result["gait_hoof_contact"],"NOT_QUALIFIED")

if __name__=="__main__":unittest.main()
