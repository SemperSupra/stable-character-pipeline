#!/usr/bin/env python3
"""Adversarial tests for source-independent decoded PNG identity (stdlib only)."""
import hashlib
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from flora_png_pixels import decode, pixel_receipt, MAGIC


def chunk(typ, data):
    return struct.pack(">I",len(data)) + typ + data + struct.pack(">I",zlib.crc32(typ+data)&0xffffffff)


def fixture(pixels, compression=6, filter_kind=0, note=None, color=6):
    """Pixels as decoded RGBA; generate lossless PNG with independent encodings."""
    width,height=2,2
    bpp=4 if color==6 else 3
    rows=[]
    last=bytes(width*bpp)
    for y in range(height):
        vals=bytes(pixels[y*width*bpp:(y+1)*width*bpp])
        if filter_kind == 0:
            encoded=vals
        elif filter_kind == 1:
            encoded=bytes((vals[i]-(vals[i-bpp] if i>=bpp else 0))&255 for i in range(len(vals)))
        elif filter_kind == 2:
            encoded=bytes((vals[i]-last[i])&255 for i in range(len(vals)))
        else:
            raise ValueError("test encoder supports 0,1,2 only")
        rows.append(bytes((filter_kind,))+encoded)
        last=vals
    ihdr=struct.pack(">IIBBBBB",width,height,8,color,0,0,0)
    return (MAGIC+chunk(b"IHDR",ihdr) +
            (chunk(b"tEXt",note.encode()) if note else b"")+
            chunk(b"IDAT",zlib.compress(b"".join(rows),compression))+
            chunk(b"IEND",b""))


class Pixels(unittest.TestCase):
    BASE=bytes((10,20,30,255,30,20,10,0,0,20,40,127,200,120,255,255))

    def receipt(self, payload):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"fixture.png"
            p.write_bytes(payload)
            return pixel_receipt(p)

    def test_equivalent_deflate_metadata_and_scanline_filters(self):
        baseline=self.receipt(fixture(self.BASE,compression=1))
        for level in (0,1,9):
            for filter_kind in (0,1,2):
                variant=self.receipt(fixture(self.BASE,compression=level,
                                             filter_kind=filter_kind,
                                             note="PNG encode variation"))
                self.assertEqual(variant,baseline)
        self.assertEqual(baseline["algorithm"],"scp.png.rgba8.v1")

    def test_alpha_and_rgb_changes_rejected(self):
        baseline=self.receipt(fixture(self.BASE))
        for index in (0,3,7,13):
            changed=bytearray(self.BASE)
            changed[index]=(changed[index]+1)&255
            self.assertNotEqual(self.receipt(fixture(changed)),baseline)

    def test_rgb_is_canonically_opaque_rgba(self):
        opaque=bytearray(self.BASE)
        for i in (3,7,11,15):
            opaque[i]=255
        rgb=b"".join(opaque[i:i+3] for i in range(0,len(opaque),4))
        self.assertEqual(self.receipt(fixture(rgb,color=2)),
                         self.receipt(fixture(opaque,color=6)))

    def test_crc_corruption_rejected(self):
        bad=bytearray(fixture(self.BASE))
        bad[-5] ^= 1
        with self.assertRaises(ValueError):
            self.receipt(bad)

    def test_truncation_and_duplicate_trailing_data_rejected(self):
        data=fixture(self.BASE)
        for bad in (data[:-1],data+b"x",data[:23]):
            with self.assertRaises(ValueError):
                self.receipt(bad)

    def test_unsupported_palette_rejected(self):
        data=fixture(self.BASE)
        i=bytearray(data[16:29]);i[9]=3
        changed=MAGIC+chunk(b"IHDR",bytes(i))+data[33:]
        with self.assertRaises(ValueError):
            self.receipt(changed)

    def test_dimensions_bomb_rejected(self):
        data=fixture(self.BASE)
        badihdr=struct.pack(">IIBBBBB",50000,50000,8,6,0,0,0)
        changed=MAGIC+chunk(b"IHDR",badihdr)+data[33:]
        with self.assertRaises(ValueError):
            self.receipt(changed)


if __name__=="__main__":
    unittest.main()
