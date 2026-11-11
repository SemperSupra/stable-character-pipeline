import pathlib
import subprocess
import sys
import tempfile
import unittest
from temporal_pixels import analyze


class TemporalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = pathlib.Path(cls.temp.name)
        subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('make_cases.py')),str(cls.base)],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_stable_moving(self):
        self.assertEqual(analyze(self.base/'stable.mp4')['verdict'],'PASS')

    def test_flicker(self):
        self.assertEqual(analyze(self.base/'flicker.mp4')['findings'],['HIGH_FREQUENCY_LUMA_FLICKER'])

    def test_cut_abstention(self):
        self.assertEqual(analyze(self.base/'cut.mp4')['verdict'],'UNKNOWN')

    def test_black(self):
        self.assertEqual(analyze(self.base/'black.mp4')['verdict'],'FAIL')

    def test_missing_video(self):
        with self.assertRaises(Exception):analyze(self.base/'missing.mp4')

    def test_truncated_video(self):
        corrupt=self.base/'broken.mp4'
        corrupt.write_bytes((self.base/'stable.mp4').read_bytes()[:300])
        with self.assertRaises(Exception):analyze(corrupt)


if __name__=='__main__':unittest.main()
