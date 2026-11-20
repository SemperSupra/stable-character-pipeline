#!/usr/bin/env python3
"""Strict stdlib PNG decoder and pixel metrics: no library version or provider metadata assumptions."""
import argparse
import json
import math
import struct
import zlib
from pathlib import Path

def png_pixels(path):
    src=Path(path).read_bytes()
    if not src.startswith(bytes.fromhex("89504e470d0a1a0a")):
        raise ValueError("bad PNG signature")
    cursor=8; data=bytearray(); dims=None
    while cursor<len(src):
        if cursor+12>len(src):raise ValueError("truncated chunk")
        size=int.from_bytes(src[cursor:cursor+4],"big");typ=src[cursor+4:cursor+8]
        end=cursor+12+size
        if end>len(src):raise ValueError("truncated chunk data")
        payload=src[cursor+8:cursor+8+size]
        crc=int.from_bytes(src[cursor+8+size:end],"big")
        if zlib.crc32(typ+payload)&0xffffffff!=crc:
            raise ValueError("PNG CRC failed")
        if typ==b"IHDR":
            w,h,depth,ctype,comp,flt,interlace=struct.unpack(">IIBBBBB",payload)
            if not(0<w<=4096 and 0<h<=4096 and depth==8 and ctype in (2,6) and comp==0 and flt==0 and interlace==0):
                raise ValueError("unsupported or unsafe PNG")
            dims=(w,h,3 if ctype==2 else 4)
        elif typ==b"IDAT": data.extend(payload)
        elif typ==b"IEND":break
        cursor=end
    if dims is None:raise ValueError("no IHDR")
    w,h,channels=dims; pitch=w*channels
    raw=zlib.decompress(data)
    if len(raw)!=(pitch+1)*h:raise ValueError("scanline length mismatch")
    prev=bytearray(pitch);pixels=bytearray()
    for y in range(h):
        line=raw[y*(pitch+1):(y+1)*(pitch+1)]
        filt=line[0];recon=bytearray(line[1:])
        if filt>4:raise ValueError("invalid PNG filter")
        for i in range(pitch):
            left=recon[i-channels] if i>=channels else 0
            up=prev[i]
            upperleft=prev[i-channels] if i>=channels else 0
            if filt==1: predict=left
            elif filt==2:predict=up
            elif filt==3:predict=(left+up)//2
            elif filt==4:
                p=left+up-upperleft
                a,b,c=abs(p-left),abs(p-up),abs(p-upperleft)
                predict=left if a<=b and a<=c else up if b<=c else upperleft
            else:predict=0
            recon[i]=(recon[i]+predict)&255
        pixels.extend(recon);prev=recon
    # Compare RGB only, and enforce fully opaque alpha where present.
    if channels==4 and any(pixels[i]!=255 for i in range(3,len(pixels),4)):
        raise ValueError("nonopaque alpha")
    rgb=bytes(pixels) if channels==3 else bytes(value for idx,value in enumerate(pixels) if idx%4!=3)
    return (w,h),rgb

def compare(a,b):
    dim_a,x=png_pixels(a);dim_b,y=png_pixels(b)
    if dim_a!=dim_b:raise ValueError("resolution drift")
    errors=sorted(abs(v-u)/255 for u,v in zip(x,y))
    if not errors:raise ValueError("no data")
    mse=sum(z*z for z in errors)/len(errors)
    return {"rmse":round(math.sqrt(mse),7),"p99_abs":round(errors[int((len(errors)-1)*.99)],7),
            "max_abs":round(errors[-1],7),"changed_samples":sum(z>0 for z in errors),"samples":len(errors)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True);p.add_argument("--max-rmse",type=float,default=.06)
    a=p.parse_args()
    root=Path(a.root)
    assert 0<=a.max_rmse<1
    assert all((root/("r095-"+version)).is_dir() for version in ("4.5.16","5.2.4","5.3.0"))
    rows=[]
    for challenger in ("5.2.4","5.3.0"):
        for frame in (1,12,24):
            metrics=compare(root/"r095-4.5.16"/("frame_%04d.png"%frame),root/("r095-"+challenger)/("frame_%04d.png"%frame))
            rows.append({"control":"4.5.16","challenger":challenger,"frame":frame,**metrics})
    adjacent=[]
    for frame in (1,12,24):
        metrics=compare(root/"r095-5.2.4"/("frame_%04d.png"%frame),root/"r095-5.3.0"/("frame_%04d.png"%frame))
        adjacent.append({"control":"5.2.4","challenger":"5.3.0","frame":frame,**metrics})
    result={"schema":"scp.r095.render-parity.v1","scope":"original-synthetic-cpu-cycles",
            "threshold_rmse":a.max_rmse,"measurements":rows,"adjacent_version_diagnostic":adjacent,
            "compatible":all(row["rmse"]<=a.max_rmse for row in rows),
            "mpfb":"HOLD","protected-character-identity":"HOLD","gait-physics":"HOLD","release":"HOLD"}
    print("R095_PIXEL_PARITY",json.dumps(result,sort_keys=True))
    if not result["compatible"]:raise SystemExit("R095_PIXEL_DRIFT_FAIL")
if __name__=="__main__":main()
