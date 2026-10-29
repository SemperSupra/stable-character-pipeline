"""W4a negative controls: timing contract, original source shape and falsification."""
import tempfile
import unittest
import wave
from pathlib import Path
from w4_boundary import (CASES, CASE_FRAMES, OFFSETS, RATE, create_wav,
                         offset_for_case, shift_error)

class TestW4Boundary(unittest.TestCase):
    def test_exact_injected_offsets_six_times(self):
        self.assertEqual([offset_for_case(i) for i in range(CASES)],list(OFFSETS)*6)
    def test_invalid_case(self):
        for i in (-1, CASES):
            with self.assertRaises(ValueError):
                offset_for_case(i)
    def test_positive_shift(self):
        self.assertEqual(shift_error(255,511,256),0)
        self.assertEqual(shift_error(255,1280,1025),0)
    def test_wrong_shift_rejected(self):
        self.assertEqual(shift_error(255,280,256),-231)
        self.assertGreater(abs(shift_error(255,280,256)),1)
    def test_nonnumeric_fails_closed(self):
        with self.assertRaises(ValueError):
            shift_error(None,255,0)
        with self.assertRaises(ValueError):
            shift_error(1,2,1.5)
    def test_wav_real_impulse_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"original.wav"
            create_wav(path,shifted=True)
            with wave.open(str(path),"rb") as wav:
                self.assertEqual((wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes()),(1,2,RATE,CASES*CASE_FRAMES))
                for i in range(CASES):
                    wav.setpos(i*CASE_FRAMES)
                    buf=wav.readframes(OFFSETS[i%7]+2)
                    onset=int.from_bytes(buf[2*OFFSETS[i%7]:2*OFFSETS[i%7]+2],"little",signed=True)
                    self.assertEqual(onset,14745)
                    self.assertTrue(all(v==0 for v in buf[:2*OFFSETS[i%7]]))
    def test_no_clobber_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"fixture.wav"
            create_wav(path,shifted=False)
            with self.assertRaises(FileExistsError):
                create_wav(path,shifted=True)
if __name__=="__main__":
    unittest.main()
