"""R077-B source-only false-acceptance coverage; no Blender/media in unit tests."""
import unittest
from render_full import check_frames
def fixture(n=72):return [{"frame":i,"sha256":format(i+1,"064x")} for i in range(n)]
class FrameContract(unittest.TestCase):
    def test_full_source_72(self):self.assertEqual(check_frames(fixture()),72)
    def test_short_video_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"FRAME_COUNT_NOT_72"):check_frames(fixture(3))
    def test_one_frame_missing(self):
        with self.assertRaisesRegex(RuntimeError,"FRAME_COUNT_NOT_72"):check_frames(fixture(71))
    def test_reordered_frames(self):
        f=fixture();f[3],f[4]=f[4],f[3]
        with self.assertRaisesRegex(RuntimeError,"FRAME_ORDER_OR_OMISSION"):check_frames(f)
    def test_static_frame_spoof(self):
        f=fixture()
        for row in f:row["sha256"]="0"*64
        with self.assertRaisesRegex(RuntimeError,"STATIC_OR_UNCHANGING_FRAMES"):check_frames(f)
    def test_real_blender_separator_argv_convention(self):
        # Blender injects engine switches before "--": parser must ignore them.
        import sys
        from unittest.mock import patch
        import render_full
        cmd=["blender","-b","--python","render_full.py","--","--saved","/missing.blend",
             "--saved-sha","a"*64,"--glb-sha","b"*64,"--frames","/unused","--out","/unused.json"]
        with patch.object(sys,"argv",cmd):
            with self.assertRaisesRegex(RuntimeError,"SOURCE_SAVED_BLEND_SHA_MISMATCH"):
                render_full.main()
    def test_bad_digest(self):
        f=fixture();f[6]["sha256"]="not-hash"
        with self.assertRaisesRegex(RuntimeError,"FRAME_HASH_INVALID"):check_frames(f)
    def test_first_last_identical(self):
        f=fixture();f[-1]["sha256"]=f[0]["sha256"]
        with self.assertRaisesRegex(RuntimeError,"STATIC_OR_UNCHANGING_FRAMES"):check_frames(f)
if __name__=="__main__":unittest.main()
