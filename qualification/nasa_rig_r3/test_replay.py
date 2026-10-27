"""Offline fail-closed replay source admission and temporal invariants."""
import json
import tempfile
import unittest
from pathlib import Path

from replay_source import (
    EXPECTED_PHOTO_SHA256,
    EXPECTED_VIDEO_SHA256,
    MODEL_SHA256,
    SOURCES,
    analyze,
    verify_native_receipt,
)


def proof():
    return {
        "status": "OBSERVED_VIDEO_AND_INDEPENDENT_PHOTO_POSES_NOT_RIG",
        "media": {name: {"bytes": SOURCES[name]["bytes"], "sha1": SOURCES[name]["sha1"],
                          "sha256": digest}
                  for name, digest in (("video", EXPECTED_VIDEO_SHA256),
                                       ("photo", EXPECTED_PHOTO_SHA256))},
        "model": {"sha256": MODEL_SHA256},
        "video_frames": 30,
        "independent_photo_landmarks": 33,
    }


class ReplayTests(unittest.TestCase):
    def test_immutable_source_provenance(self):
        verify_native_receipt(proof())

    def test_no_short_or_mutated_source(self):
        for name in ("video", "photo"):
            rec = proof()
            rec["media"][name]["sha256"] = "0"*64
            with self.assertRaisesRegex(ValueError, "source original SHA"):
                verify_native_receipt(rec)
            rec = proof()
            rec["media"][name]["bytes"] -= 1
            with self.assertRaisesRegex(ValueError, "source original SHA"):
                verify_native_receipt(rec)

    def test_model_and_observation_rights_independent(self):
        rec = proof()
        rec["model"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "model weights"):
            verify_native_receipt(rec)
        rec = proof()
        rec["status"] = "FAILED_FIRST_ERROR"
        with self.assertRaisesRegex(ValueError, "not independently observed"):
            verify_native_receipt(rec)

    def test_source_timestamps_and_missingness(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "receipt.json").write_text(json.dumps(proof()))
            frames = [{"frame": i, "source_video_offset_ms": 11000 + i * 1000,
                       "landmarks2d": ([{"x": .5, "y": .5, "z": 0, "visibility": 1}]*33
                                       if 3 <= i <= 9 else [])}
                      for i in range(30)]
            (out / "video_landmarks.json").write_text(json.dumps(frames))
            receipt = analyze(out)
            self.assertEqual(receipt["longest_contiguous_detected_frames"], 7)
            self.assertFalse(receipt["bit_identical_observations_to_r2"])
            frames[10]["source_video_offset_ms"] += 500
            (out / "video_landmarks.json").write_text(json.dumps(frames))
            with self.assertRaisesRegex(ValueError, "timestamps drifted"):
                analyze(out)
            frames[10]["source_video_offset_ms"] -= 500
            frames[5]["landmarks2d"] = frames[5]["landmarks2d"][:12]
            (out / "video_landmarks.json").write_text(json.dumps(frames))
            with self.assertRaisesRegex(ValueError, "partial skeleton"):
                analyze(out)


if __name__ == "__main__":
    unittest.main()
