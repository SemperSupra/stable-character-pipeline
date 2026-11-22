"""Hostile source↔native timebase admission, no synthetic 12Hz promotion."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from clock_contract import validate


class NativeClockControls(unittest.TestCase):
    def test_full_360_exact(self):
        p=validate(list(range(360)))
        self.assertEqual(p["last_source_sample_time_s"],round(359/60,9))
        self.assertEqual(p["video_duration_seconds"],6.0)
        self.assertEqual(p["tail_sample_indices"],[356,357,358,359])
        self.assertEqual(p["status"],"HOLD_NATIVE_KEYS_ONLY")

    def test_scene_keyframes_starting_at_one_still_maps_correctly(self):
        self.assertEqual(validate(list(range(1,361)))["target_frames"],360)

    def test_legacy_72_decimated_keys_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OR_EXTRA"):
            validate(list(range(72)))

    def test_last_four_omitted_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OR_EXTRA"):
            validate(list(range(356)))

    def test_forged_padded_tail_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_TARGET_FRAME_GAPS"):
            validate(list(range(356))+[355,355,355,355])

    def test_misindexed_early_frame_rejected(self):
        data=list(range(360))
        data[1]=2
        with self.assertRaisesRegex(ValueError,"SOURCE_TARGET_FRAME_GAPS"):
            validate(data)

    def test_legacy_fps_rejected(self):
        with self.assertRaisesRegex(ValueError,"FPS_NOT_60"):
            validate(list(range(360)),12)

    def test_nonfinite_and_type_rejected(self):
        for value in (math.nan, math.inf, True, None):
            times=list(range(360))
            times[200]=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,"NONFINITE_NATIVE_FRAME"):
                validate(times)

    def test_unapproved_origin_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_TARGET_INDEX_ORIGIN"):
            validate(list(range(5,365)))


if __name__=="__main__":
    unittest.main()
