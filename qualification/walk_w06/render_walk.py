from pathlib import Path

import hashlib,json,subprocess,sys
from PIL import Image,ImageDraw
import imageio_ffmpeg
from gait import validate
from source_native import build,polygons

W,H=960,540
def project(p):
    return ((p[0]+3.9)/7.8*W,H-(p[1]+.15)/3*H)
def hull(points):
    pts=sorted(set((round(x,3),round(y,3)) for x,y in points))
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    return lower,upper
