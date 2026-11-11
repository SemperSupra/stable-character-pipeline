#!/usr/bin/env python3
"""Generate rights-original, internally moving 160x120 RGB24 PPM then encode H.264."""
import pathlib
import subprocess
import sys
out = pathlib.Path(sys.argv[1]).resolve()
if not out.exists():out.mkdir(parents=True)
for variant in ('stable','flicker','cut','black'):
    source=out / (variant+'-source')
    source.mkdir(exist_ok=True)
    for i in range(36):
        base={'stable':90,'flicker':(60 if i%2 else 140),
              'cut':(75 if i<18 else 165),'black':0}[variant]
        pixels=bytearray([base,base,base]*160*120)
        if variant!='black':
            for y in range(45,55):
                for x in range(5+i,15+i):
                    off=(y*160+x)*3
                    pixels[off:off+3]=bytes((230,230,230))
        (source/f'frame-{i:03d}.ppm').write_bytes(b'P6\n160 120\n255\n'+pixels)
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-framerate','12',
                    '-i',str(source/'frame-%03d.ppm'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                    str(out/(variant+'.mp4'))],check=True,timeout=25)
