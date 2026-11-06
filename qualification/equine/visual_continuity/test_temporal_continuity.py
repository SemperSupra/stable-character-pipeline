import importlib.util, pathlib, unittest
P=pathlib.Path(__file__).with_name('temporal_continuity.py')
spec=importlib.util.spec_from_file_location('temporal_continuity',P)
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
class FalsifierTest(unittest.TestCase):
    def test_smooth_frames_are_not_anatomy_claim(self):
        seq=[bytes([i]* (t.W*t.H)) for i in range(t.FRAMES)]
        r=t.continuity(seq)
        self.assertEqual(r['flagged_center_frames_zero_based'],[])
        self.assertEqual(r['distinct_frame_sha256'],48)
    def test_temporal_swap_while_all_frames_remain_distinct(self):
        seq=[bytes([i]* (t.W*t.H)) for i in range(t.FRAMES)]
        seq[12],seq[36]=seq[36],seq[12]
        r=t.continuity(seq)
        self.assertEqual(r['distinct_frame_sha256'],48)
        self.assertGreaterEqual(len(r['flagged_center_frames_zero_based']),3)
    def test_fails_closed_on_missing_frame(self):
        with self.assertRaises(ValueError): t.continuity([bytes(t.W*t.H)]*47)
    def test_fails_closed_on_bad_shape(self):
        with self.assertRaises(ValueError): t.continuity([bytes(t.W*t.H)]*47+[b'bad'])
    def test_fails_closed_on_wrong_video_sha(self):
        with self.assertRaises(ValueError): t.verify_media(P,'0'*64)
if __name__=='__main__':unittest.main()
