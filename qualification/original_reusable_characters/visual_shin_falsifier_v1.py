"""Source-specific Blender PNG shin-visibility regression falsifier; stdlib only.

Pinned to source-original Aster Workbench 720x480 start-front camera/palette.
Does NOT establish human realism, anatomical fit, safety or cloth collision.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

SCHEMA = "scp.r009.native_shin_exposure_falsifier.v1"
ROI = (295,320,410,480)
WIDTH,HEIGHT=720,480
MAX_EXPOSED=20
MIN_SLATE=9000

def unpack_png(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("INVALID_PNG_SIGNATURE")
    pos=8;header=None;idat=bytearray();ended=False
    while pos+12<=len(raw):
        size=struct.unpack_from(">I",raw,pos)[0]
        typ=raw[pos+4:pos+8]
        end=pos+12+size
        if size>16<<20 or end>len(raw):
            raise ValueError("PNG_CHUNK_BOUND")
        blob=raw[pos+8:pos+8+size]
        crc=struct.unpack_from(">I",raw,pos+8+size)[0]
        if zlib.crc32(typ+blob)&0xffffffff!=crc:
            raise ValueError("PNG_CRC_FAIL")
        if typ==b"IHDR":
            if header is not None or len(blob)!=13:
                raise ValueError("PNG_DUPLICATED_OR_BAD_IHDR")
            header=struct.unpack(">IIBBBBB",blob)
            if header!=(WIDTH,HEIGHT,8,6,0,0,0):
                raise ValueError("NONCOMPARABLE_PNG_VIEW")
        elif typ==b"IDAT":
            if header is None:raise ValueError("PNG_MISSING_IHDR")
            idat.extend(blob)
        elif typ==b"IEND":
            ended=True
            if size!=0 or end!=len(raw):
                raise ValueError("PNG_TRAILING_OR_BAD_IEND")
            break
        pos=end
    if not ended or not idat:
        raise ValueError("PNG_MISSING_IDAT_OR_IEND")
    try:
        inflater=zlib.decompressobj()
        scan=inflater.decompress(bytes(idat),(WIDTH*4+1)*HEIGHT+1)
        scan+=inflater.flush()
    except zlib.error as e:
        raise ValueError("PNG_ZLIB_ERROR") from e
    stride=WIDTH*4
    if not inflater.eof or len(scan)!=(stride+1)*HEIGHT:
        raise ValueError("PNG_DECOMPRESSED_LENGTH")
    rows=[];previous=bytearray(stride);offset=0
    for _ in range(HEIGHT):
        filter_type=scan[offset];offset+=1
        current=bytearray(scan[offset:offset+stride]);offset+=stride
        if filter_type>4:
            raise ValueError("PNG_UNKNOWN_FILTER")
        if filter_type:
            for i in range(stride):
                left=current[i-4] if i>=4 else 0
                up=previous[i];upleft=previous[i-4] if i>=4 else 0
                if filter_type==1:prediction=left
                elif filter_type==2:prediction=up
                elif filter_type==3:prediction=(left+up)//2
                else:
                    p=left+up-upleft
                    a,b,c=abs(p-left),abs(p-up),abs(p-upleft)
                    prediction=left if a<=b and a<=c else (up if b<=c else upleft)
                current[i]=(current[i]+prediction)&255
        rows.append(bytes(current));previous=current
    return rows

def measure(path):
    rows=unpack_png(path)
    x0,y0,x1,y1=ROI
    warm=0;slate=0
    for y in range(y0,y1):
        row=rows[y]
        for x in range(x0,x1):
            r,g,b,a=row[x*4:x*4+4]
            if a==0:continue
            if r*100>g*120 and g*100>b*104 and r>65:warm+=1
            if r<120 and g>r+6 and b>g+4 and b<150:slate+=1
    if slate<MIN_SLATE:
        raise ValueError("INVALID_CAMERA_PALETTE_OR_PANT_REGION")
    return {
        "schema":SCHEMA,"source_png_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "roi":list(ROI),"witness":"ASTER_ORIGINAL_720x480_WORKBENCH_START_FRONT_SHIN_ONLY",
        "source_palette_fixed":True,"warm_exposure_pixels":warm,"slate_pant_pixels":slate,
        "threshold_warm_exposure_pixels":MAX_EXPOSED,
        "source_specific_regression_detected":warm>MAX_EXPOSED,
        "human_visual_accepted":False,"physical_cloth_accepted":False,
        "independent_camera_calibrated":False,"release_approved":False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args()
    output=Path(a.out)
    if Path(a.input).resolve()==output.resolve() or output.exists():
        raise ValueError("REFUSE_OVERWRITE_SOURCE_OR_RECEIPT")
    r=measure(a.input)
    with output.open("x",encoding="utf-8") as f:
        f.write(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("R009_NATIVE_SHIN_VISUAL_FALSIFIER "+json.dumps(r,sort_keys=True))
    if r["source_specific_regression_detected"]:
        raise ValueError("FIRST_RED_EXPOSED_SHIN_SOURCE_REGRESSION")

if __name__=="__main__":
    main()
