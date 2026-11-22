"""Adversarial data controls for a public-only PCM A/B technical witness."""
import math
import pathlib
import struct
import tempfile
import unittest
import wave

from verify_ab import qualify


class ABTechnicalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def wav(self, filename, *, pitch=440, gain=0.1, frames=48000, rate=48000, channels=2):
        p = self.root / filename
        with wave.open(str(p), "wb") as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            samples = [int(32767 * gain * math.sin(2 * math.pi * pitch * i / rate)) for i in range(frames)]
            writer.writeframes(b"".join(struct.pack("<h", x) * channels for x in samples))
        return p

    def test_real_difference_is_measured(self):
        old = self.wav("old.wav", pitch=440)
        new = self.wav("new.wav", pitch=550)
        receipt = qualify(old, new)
        self.assertGreater(receipt["difference_rms_fraction"], 0.01)
        self.assertEqual(receipt["perceptual_acceptance"], "NOT_TESTED")

    def test_identical_mix_is_rejected(self):
        old = self.wav("old.wav")
        with self.assertRaisesRegex(ValueError, "distinguishable"):
            qualify(old, old)

    def test_silence_is_rejected(self):
        old = self.wav("old.wav", gain=0)
        new = self.wav("new.wav", pitch=550)
        with self.assertRaisesRegex(ValueError, "silent"):
            qualify(old, new)

    def test_full_scale_is_rejected(self):
        old = self.wav("old.wav", gain=1.0, pitch=12000)
        new = self.wav("new.wav", pitch=550)
        with self.assertRaisesRegex(ValueError, "full-scale"):
            qualify(old, new)

    def test_truncated_timeline_is_rejected(self):
        old = self.wav("old.wav", frames=48000)
        new = self.wav("new.wav", pitch=550, frames=24000)
        with self.assertRaisesRegex(ValueError, "duration"):
            qualify(old, new)

    def test_wrong_sample_rate_is_rejected(self):
        old = self.wav("old.wav", rate=44100)
        new = self.wav("new.wav", pitch=550)
        with self.assertRaisesRegex(ValueError, "48 kHz"):
            qualify(old, new)

    def test_mono_is_rejected(self):
        old = self.wav("old.wav", channels=1)
        new = self.wav("new.wav", pitch=550)
        with self.assertRaisesRegex(ValueError, "stereo"):
            qualify(old, new)


if __name__ == "__main__":
    unittest.main()
