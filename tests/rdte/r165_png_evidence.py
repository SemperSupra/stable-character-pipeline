"""Original public-safe PNG chunk / image-payload qualification helper.

This is independent evidence tooling, not a private renderer or a general PNG
decoder. A matching IDAT payload proves identical compressed image data, NOT
universal equality of decoded RGBA across distinct encodings/color profiles.
"""
import hashlib
from pathlib import Path
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_FILE = 16 * 1024 * 1024
MAX_CHUNKS = 4096


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def inspect_png(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_FILE or not raw.startswith(SIGNATURE):
        raise ValueError("invalid or over-budget PNG input")
    pos, chunks, image, dimensions = len(SIGNATURE), 0, [], None
    texts, seen_ihdr, seen_iend = {}, False, False
    while pos < len(raw):
        if chunks >= MAX_CHUNKS or pos + 12 > len(raw):
            raise ValueError("truncated or excessive PNG chunks")
        size = struct.unpack(">I", raw[pos:pos + 4])[0]
        kind = raw[pos + 4:pos + 8]
        end = pos + 12 + size
        if size > MAX_FILE or end > len(raw):
            raise ValueError("PNG chunk exceeds input boundary")
        body = raw[pos + 8:pos + 8 + size]
        crc_found = struct.unpack(">I", raw[pos + 8 + size:end])[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc_found:
            raise ValueError("PNG chunk CRC mismatch")
        if not all((65 <= k <= 90) or (97 <= k <= 122) for k in kind):
            raise ValueError("invalid PNG chunk type")
        if not seen_ihdr and kind != b"IHDR":
            raise ValueError("IHDR must be first")
        if kind == b"IHDR":
            if seen_ihdr or size != 13:
                raise ValueError("invalid repeated IHDR")
            width, height = struct.unpack(">II", body[:8])
            if not (1 <= width <= 8192 and 1 <= height <= 8192):
                raise ValueError("invalid PNG dimensions")
            dimensions = (width, height)
            seen_ihdr = True
        elif kind == b"IDAT":
            if seen_iend:
                raise ValueError("image payload after IEND")
            image.append(body)
        elif kind == b"tEXt":
            k, sep, value = body.partition(b"\x00")
            if sep and len(k) <= 80:
                texts[k.decode("latin-1")] = value.decode("latin-1")
        elif kind == b"IEND":
            if seen_iend or size != 0:
                raise ValueError("invalid IEND")
            seen_iend = True
            if end != len(raw):
                raise ValueError("trailing PNG bytes")
        chunks += 1
        pos = end
    if not seen_ihdr or not seen_iend or not image:
        raise ValueError("PNG missing required chunks")
    return {
        "file_sha256": sha256(raw),
        "idat_sha256": sha256(b"".join(image)),
        "dimensions": dimensions,
        "chunks": chunks,
        "text": texts,
    }


def compare_payloads(first: bytes, second: bytes) -> dict:
    a, b = inspect_png(first), inspect_png(second)
    return {
        "identical_file": a["file_sha256"] == b["file_sha256"],
        "identical_idat": a["idat_sha256"] == b["idat_sha256"],
        "same_dimensions": a["dimensions"] == b["dimensions"],
        "changed_text_keys": sorted(k for k in set(a["text"]) | set(b["text"])
                                    if a["text"].get(k) != b["text"].get(k)),
    }


def inspect_file(path: str) -> dict:
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_FILE:
        raise ValueError("untrusted PNG input path")
    return inspect_png(p.read_bytes())
