"""Synthetic unit tests for native PNG visual first-RED validator."""
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from visual_shin_falsifier_v1 import measure,unpack_png,SCHEMA,ROI,MAX_EXPOSED

def _chunk(kind,data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)

def _source_test_png(exposed=0,wrong_filter=False,width=720):
    if not 0<=exposed<=18000:raise ValueError("bad fixture")
    height=480
    rows=[]
    n=0
    for y in range(height):
        row=bytearray()
        for x in range(width):
            if 295<=x<410 and 320<=y<480:
                if n<exposed:
                    rgba=(160,105,80,255)
                else:
                    rgba=(60,75,85,255)
                n+=1
            else:
                rgba=(129,136,144,255)
            row.extend(rgba)
        rows.append(bytes([5 if wrong_filter and y==0 else 0])+row)
    raw=zlib.compress(b"".join(rows),6)
    header=struct.pack(">IIBBBBB",width,height,8,6,0,0,0)
    return b"\x89PNG\r\n\x1a\n"+_chunk(b"IHDR",header)+_chunk(b"IDAT",raw)+_chunk(b"IEND",b"")

class SourceVisualFalsifierTests(unittest.TestCase):
    def test_first_failure_positive_and_clean_negative_controls(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"test.png"
            for n in (0,MAX_EXPOSED,MAX_EXPOSED+1,396,798):
                p.write_bytes(_source_test_png(exposed=n))
                result=measure(p)
                self.assertEqual(result["schema"],SCHEMA)
                self.assertEqual(result["roi"],list(ROI))
                self.assertEqual(result["warm_exposure_pixels"],n)
                self.assertGreater(result["slate_pant_pixels"],9000)
                self.assertEqual(result["source_specific_regression_detected"],n>MAX_EXPOSED)
                self.assertFalse(result["human_visual_accepted"])
                self.assertFalse(result["physical_cloth_accepted"])
                self.assertFalse(result["release_approved"])

    def test_wrong_image_scope_crc_bad_filter_and_incomplete_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"test.png"
            for raw,expected in (
                (b"no png","INVALID_PNG_SIGNATURE"),
                (_source_test_png(width=719),"NONCOMPARABLE_PNG_VIEW"),
                (_source_test_png(wrong_filter=True),"PNG_UNKNOWN_FILTER"),
                (_source_test_png()[:-7],"PNG_CHUNK_BOUND"),
            ):
                p.write_bytes(raw)
                with self.assertRaisesRegex(ValueError,expected):
                    unpack_png(p)
            raw=bytearray(_source_test_png())
            raw[25]^=1
            p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,"PNG_CRC_FAIL"):
                unpack_png(p)

    def test_camera_moved_to_empty_gray_scope_not_false_green(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"test.png"
            raw=_source_test_png()
            # Pixel reader must reject user-supplied size, not silently pass.
            p.write_bytes(raw.replace(b"\x00\x00\x02\xd0",b"\x00\x00\x02\xcf",1))
            with self.assertRaises(ValueError):
                measure(p)

if __name__=="__main__":
    unittest.main(verbosity=2)
