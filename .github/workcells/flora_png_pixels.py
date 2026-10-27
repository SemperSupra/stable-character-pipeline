#!/usr/bin/env python3
"""Dependency-free canonical digest of actual decoded PNG pixels.

Contract scp.png.rgba8.v1 = SHA256(b"scp.png.rgba8.v1\0" +
  width,height as two uint32 big-endian + decoded row-major RGBA8 bytes).
Ignore PNG metadata and DEFLATE encoding; preserve alpha to avoid masking drift.
Bounded baseline accepts only 8-bit, noninterlaced RGB/RGBA PNG.
"""
import hashlib
import struct
import zlib
from pathlib import Path

MAGIC = b"\x89PNG\r\n\x1a\n"
DOMAIN = b"scp.png.rgba8.v1\x00"
MAX_FILE = 10_000_000
MAX_PIXELS = 2_073_600


def decode(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_FILE or not raw.startswith(MAGIC):
        raise ValueError("invalid or oversize PNG file")
    pos, size, width, height, bpp, idat, seen_end = 8, len(raw), 0, 0, 0, bytearray(), False
    saw_ihdr, saw_idat = False, False
    while pos < size:
        if pos + 12 > size:
            raise ValueError("truncated PNG chunk")
        n = struct.unpack_from(">I", raw, pos)[0]
        if n > MAX_FILE or pos + n + 12 > size:
            raise ValueError("oversize or truncated PNG chunk")
        typ = raw[pos+4:pos+8]
        payload = raw[pos+8:pos+8+n]
        stored = struct.unpack_from(">I", raw, pos+8+n)[0]
        if zlib.crc32(typ + payload) & 0xffffffff != stored:
            raise ValueError("PNG chunk CRC mismatch")
        pos += n + 12
        if not saw_ihdr:
            if typ != b"IHDR" or n != 13:
                raise ValueError("missing initial PNG IHDR")
            width, height, depth, color, compression, filter_method, interlace = struct.unpack(">IIBBBBB",payload)
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ValueError("invalid PNG image dimensions")
            if depth != 8 or color not in (2, 6) or (compression,filter_method,interlace)!=(0,0,0):
                raise ValueError("unsupported PNG format (requires 8-bit RGB/RGBA noninterlaced)")
            bpp = 4 if color == 6 else 3
            saw_ihdr = True
        elif typ == b"IHDR":
            raise ValueError("duplicate IHDR")
        elif typ == b"IDAT":
            saw_idat = True
            if len(idat) + n > MAX_FILE:
                raise ValueError("oversize compressed PNG image")
            idat.extend(payload)
        elif typ == b"IEND":
            if n != 0 or not saw_idat or pos != size:
                raise ValueError("invalid PNG IEND")
            seen_end = True
            break
        elif typ[0] & 32 == 0:
            raise ValueError("unsupported critical PNG chunk")
    if not seen_end or not saw_idat:
        raise ValueError("incomplete PNG")
    stride = width * bpp
    needed = height * (stride + 1)
    decompress = zlib.decompressobj()
    scanlines = decompress.decompress(bytes(idat), needed + 1)
    scanlines += decompress.flush(needed + 1 - len(scanlines))
    if len(scanlines) != needed or not decompress.eof or decompress.unused_data:
        raise ValueError("corrupt or unbounded PNG scanline data")
    rgba = bytearray(width * height * 4)
    prior = bytearray(stride)
    for y in range(height):
        offset = y * (stride + 1)
        filter_type = scanlines[offset]
        row = bytearray(scanlines[offset+1:offset+1+stride])
        if filter_type > 4:
            raise ValueError("unsupported PNG scanline filter")
        for i in range(stride):
            a = row[i-bpp] if i >= bpp else 0
            b = prior[i]
            c = prior[i-bpp] if i >= bpp else 0
            if filter_type == 1:
                predictor = a
            elif filter_type == 2:
                predictor = b
            elif filter_type == 3:
                predictor = (a+b)//2
            elif filter_type == 4:
                p = a+b-c
                da, db, dc = abs(p-a), abs(p-b), abs(p-c)
                predictor = a if da<=db and da<=dc else b if db<=dc else c
            else:
                predictor = 0
            row[i] = (row[i] + predictor) & 255
        start = y * width * 4
        if bpp == 4:
            rgba[start:start+width*4] = row
        else:
            for x in range(width):
                rgba[start+4*x:start+4*x+3] = row[3*x:3*x+3]
                rgba[start+4*x+3] = 255
        prior = row
    return width, height, bytes(rgba)


def pixel_receipt(path):
    w,h,rgba=decode(path)
    return {"algorithm":"scp.png.rgba8.v1", "width":w, "height":h,
            "rgba8_sha256": hashlib.sha256(DOMAIN + struct.pack(">II", w, h) + rgba).hexdigest()}


def verify_images(folder, names, receipt_field):
    """Independent file custody + RGBA equality gate; no Pillow or Blender needed."""
    import json
    folder=Path(folder)
    receipt=json.loads((folder / receipt_field).read_text())
    for name in names:
        key=name.rsplit("/",1)[-1].removesuffix(".png")
        name_key=key[3:] if key.startswith("ab_") else key[11:] if key.startswith("diagnostic_") else key
        path=folder/name
        expected_file=(receipt["views_sha256"] if "views_sha256" in receipt else receipt["diagnostic_views"])[name_key]
        expected_rgba=(receipt["views_rgba8"] if "views_rgba8" in receipt else receipt["diagnostic_rgba8"])[name_key]
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected_file:
            raise ValueError("file custody hash mismatch: "+name)
        decoded=pixel_receipt(path)
        if decoded!=expected_rgba:
            raise ValueError("canonical decoded RGBA digest mismatch: "+name)
    return len(names)
