import tempfile
import unittest
from pathlib import Path
from compare_png import png_pixels, compare
import struct,zlib

def make_png(data,w=1,h=1,depth=8,ctype=6):
    sig=bytes.fromhex("89504e470d0a1a0a")
    def chunk(k,v):
        return struct.pack(">I",len(v))+k+v+struct.pack(">I",zlib.crc32(k+v)&0xffffffff)
    hdr=struct.pack(">IIBBBBB",w,h,depth,ctype,0,0,0)
    return sig+chunk(b"IHDR",hdr)+chunk(b"IDAT",zlib.compress(data))+chunk(b"IEND",b"")

class TestPNG(unittest.TestCase):
    def test_equal(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.png";b=Path(d)/"b.png"
            a.write_bytes(make_png(bytes([0,17,34,51,255])));b.write_bytes(a.read_bytes())
            self.assertEqual(compare(a,b)["rmse"],0)
    def test_different(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.png";b=Path(d)/"b.png"
            a.write_bytes(make_png(bytes([0,0,0,0,255])))
            b.write_bytes(make_png(bytes([0,255,0,0,255])))
            self.assertGreater(compare(a,b)["rmse"],0)
    def test_crc(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.png";p=bytearray(make_png(bytes([0,0,0,0,255])))
            p[-8]^=1;a.write_bytes(p)
            with self.assertRaises(ValueError):png_pixels(a)
    def test_alpha(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.png";a.write_bytes(make_png(bytes([0,0,0,0,0])))
            with self.assertRaises(ValueError):png_pixels(a)
if __name__=="__main__":unittest.main()
