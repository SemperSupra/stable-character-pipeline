"""Adversarial actual H264 decoded-frame L1 tests: moving, black, frozen."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from qa_video import inspect


class ActualPixelObserverTests(unittest.TestCase):
    def video(self, root, name, source):
        output = root / (name + ".mp4")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi",
                        "-i", source, "-pix_fmt", "yuv420p", "-c:v", "libx264",
                        str(output)], check=True, timeout=45)
        return output

    def test_moving_source_passes_l1_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video = self.video(root, "moving", "testsrc2=size=128x72:rate=12:duration=2")
            result = inspect(video, root / "check")
            self.assertEqual(result["status"], "PASS_L1_VIDEO_ONLY", result)
            self.assertEqual(result["anatomy"], "UNKNOWN_NOT_MEASURED_FROM_PIXELS")
            self.assertEqual(result["frames_decoded"], 24)

    def test_black_video_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video = self.video(root, "black", "color=c=black:s=128x72:r=12:d=2")
            result = inspect(video, root / "check")
            self.assertEqual(result["status"], "FAIL", result)
            self.assertIn("VIDEO_STATIC_OR_REPEATED", result["failures"])

    def test_unchanging_nonblack_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video = self.video(root, "static", "color=c=white:s=128x72:r=12:d=2")
            result = inspect(video, root / "check")
            self.assertEqual(result["status"], "FAIL", result)
            self.assertIn("VIDEO_STATIC_OR_REPEATED", result["failures"])


if __name__ == "__main__":
    unittest.main()
