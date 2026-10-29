"""Prospective adversarial controls for batched W4b trajectory qualification."""
import tempfile
import unittest
import wave
from pathlib import Path
from w4b_movement import (BLOCK, BLOCKS_PER_CASE, CASES, FRAMES_PER_CASE,
                          MODES, RATE, MOVING_THRESHOLD, make_source, pose, stage_profile, wrap)
class W4BControlTests(unittest.TestCase):
    def test_modes_closed(self):
        with self.assertRaises(ValueError):pose("invented",0,0,0)
        with self.assertRaises(ValueError):pose("static",0,0,12)
    def test_wrapped_azimuth(self):
        self.assertEqual(wrap(180.0),-180.0)
        self.assertAlmostEqual(pose("yaw_left_75",170,2,4)[0],95)
        self.assertAlmostEqual(pose("yaw_left_75",170,2,8)[0],-115)
        self.assertAlmostEqual(pose("yaw_right_75",170,2,4)[0],-115)
    def test_range_phases(self):
        self.assertEqual([pose("range_2_to_20",0,0,i)[2] for i in (0,3,6,9)],[10.0,2.0,20.0,20.0])
    def test_unmodified_control(self):
        for mode in MODES:
            self.assertEqual(pose(mode,20,5,0),(20.0,5.0,10.0))
    def test_real_original_source_and_silent_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.wav"
            make_source(path)
            with wave.open(str(path),"rb") as wav:
                self.assertEqual((wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes()),
                    (1,2,RATE,CASES*FRAMES_PER_CASE))
                for case in (0,7,41):
                    wav.setpos(case*FRAMES_PER_CASE+9*BLOCK)
                    self.assertEqual(wav.readframes(3*BLOCK),bytes(6*BLOCK))
                wav.setpos(3*BLOCK)
                self.assertNotEqual(wav.readframes(1),bytes(2))
    def test_refuse_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.wav"
            make_source(path)
            with self.assertRaises(FileExistsError):make_source(path)
    def test_stage_rejects_silent_or_lfe(self):
        channels=6
        samples=[0.0]*(FRAMES_PER_CASE*channels)
        with self.assertRaises(ValueError):stage_profile(samples,channels,0,0)
        for i in range(BLOCK,3*BLOCK):samples[i*channels+3]=.5
        with self.assertRaises(ValueError):stage_profile(samples,channels,0,0)
    def test_motion_threshold_positive(self):
        a=[.8,.6,0,0,0,0]
        b=[.2,.979795897,0,0,0,0]
        self.assertGreater(max(abs(x-y) for x,y in zip(a,b)),MOVING_THRESHOLD)
if __name__=="__main__":unittest.main()
