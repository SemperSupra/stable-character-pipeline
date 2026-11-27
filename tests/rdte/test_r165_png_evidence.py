"""Synthetic-only negative qualification of public PNG evidence reader."""
import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

path = Path(__file__).with_name("r165_png_evidence.py")
spec = importlib.util.spec_from_file_location("r165_png_evidence", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def chunk(kind, body):
    return (struct.pack(">I", len(body)) + kind + body +
            struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff))


def png(note=b"first", pixels=b"\x00\x10\x20\x30"):
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (m.SIGNATURE + chunk(b"IHDR", ihdr) +
            chunk(b"tEXt", b"Date\x00" + note) +
            chunk(b"IDAT", zlib.compress(pixels)) +
            chunk(b"IEND", b""))


class PNGEvidenceTests(unittest.TestCase):
    def test_valid_metadata_separation(self):
        first, second = png(b"day1"), png(b"day2")
        x = m.compare_payloads(first, second)
        self.assertFalse(x["identical_file"])
        self.assertTrue(x["identical_idat"])
        self.assertTrue(x["same_dimensions"])
        self.assertEqual(x["changed_text_keys"], ["Date"])

    def test_detect_modified_image_payload(self):
        x = m.compare_payloads(png(pixels=b"\x00\x10\x20\x30"),
                               png(pixels=b"\x00\x10\x20\x31"))
        self.assertFalse(x["identical_idat"])

    def test_reject_corruption(self):
        data = bytearray(png())
        data[-18] ^= 1
        with self.assertRaises(ValueError):
            m.inspect_png(bytes(data))

    def test_reject_missing_and_trailing_data(self):
        for data in (png()[:-4], png() + b"junk", b"bad", b""):
            with self.subTest(data=data[-8:]):
                with self.assertRaises(ValueError):
                    m.inspect_png(data)

    def test_reject_duplicate_ihdr(self):
        data = png()
        ihdr = data[8:33]
        with self.assertRaises(ValueError):
            m.inspect_png(data[:33] + ihdr + data[33:])

    def test_reject_missing_idat(self):
        good = png()
        ihdr = good[8:33]
        with self.assertRaises(ValueError):
            m.inspect_png(m.SIGNATURE + ihdr + chunk(b"IEND", b""))

    def test_reject_unbounded_file(self):
        with self.assertRaises(ValueError):
            m.inspect_png(m.SIGNATURE + b"x" * (m.MAX_FILE + 1))

    def test_reject_bad_ihdr_order(self):
        with self.assertRaises(ValueError):
            m.inspect_png(m.SIGNATURE + chunk(b"tEXt", b"x\x00y") + png()[8:])


if __name__ == "__main__":
    unittest.main()
