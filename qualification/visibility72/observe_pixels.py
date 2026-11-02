#!/usr/bin/env python3
"""Independent RGB-pixel visibility screen for ORIGINAL synthetic park clips.
Not identity, anatomical, physical-contact, protected-source or CPE acceptance.
Uses decoded clean H264 pixels, separately from declared synthetic source.
"""
import argparse, hashlib, json, math, pathlib, statistics, subprocess, sys

WIDTH, HEIGHT, N, FPS = 480, 270, 72, 12
ACTORS = ("CobaltOriginal", "MarigoldOriginal")
VIEWS = ("front", "oblique")
def digest(b): return hashlib.sha256(b).hexdigest()
def unit(x):
    d=math.sqrt(sum(v*v for v in x))
    if d < 1e-9: raise ValueError("DEGENERATE_CAMERA")
    return tuple(v/d for v in x)
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def project(pt, camera):
    eye=tuple(camera["position"]); target=tuple(camera["target"])
    f=unit(sub(target,eye)); right=unit(cross(f,(0,0,1))); up=unit(cross(right,f))
    d=sub(pt,target)
    return ((.5+dot(d,right)/9.6)*WIDTH,
            (.5-dot(d,up)/(9.6*HEIGHT/WIDTH))*HEIGHT)
def decode(path):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-i",str(path),
         "-f","rawvideo","-pix_fmt","rgb24","-vsync","0","pipe:1"]
    result=subprocess.run(cmd,capture_output=True,check=True)
    size=WIDTH*HEIGHT*3
    if len(result.stdout)!=size*N: raise ValueError("NOT_EXACTLY_72_DECODED_RGB_FRAMES")
    return [result.stdout[i*size:(i+1)*size] for i in range(N)]
def color_count(frame, center, actor, blackout=False):
    cx,cy=center
    x0=max(0,int(cx)-35);x1=min(WIDTH,int(cx)+36)
    y0=max(0,int(cy)-45);y1=min(HEIGHT,int(cy)+46)
    if x1<=x0 or y1<=y0: raise ValueError("ACTOR_OUT_OF_FRAME")
    if blackout: return 0
    count=0
    for y in range(y0,y1):
        for x in range(x0,x1):
            i=(y*WIDTH+x)*3
            r,g,b=frame[i],frame[i+1],frame[i+2]
            if actor=="MarigoldOriginal":
                good=r>65 and g>28 and r>1.22*g and g>1.22*b
            else:
                good=g>45 and b>55 and g>1.6*r and b>1.65*r and b>.78*g
            if good:count+=1
    return count
def observe(source, paths, fault):
    if source.get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or source.get("private_r009")!="HELD_NOT_ACCEPTED":
        raise ValueError("RIGHTS_OR_PROTECTED_PRODUCT_CLAIM")
    if source.get("fps")!=FPS or source.get("frame_count")!=N or source.get("actor_ids")!=list(ACTORS):
        raise ValueError("SOURCE_CLOCK_OR_ACTOR_MISMATCH")
    if len(source.get("frames",[]))!=N or set(source.get("cameras",{}))!=set(VIEWS):
        raise ValueError("SOURCE_FRAME_CAMERA_MISSING")
    clips={view:decode(paths[view]) for view in VIEWS}
    if fault=="alias_camera":clips["oblique"]=clips["front"]
    if fault=="short_clock":clips["front"]=clips["front"][:-1]
    if len(clips["front"])!=N or len(clips["oblique"])!=N:raise ValueError("FRAME_COUNT_FALSE_ACCEPT")
    if digest(b"".join(clips["front"]))==digest(b"".join(clips["oblique"])):
        raise ValueError("TWO_VIEWS_PIXEL_ALIAS")
    counts={}
    for view in VIEWS:
        camera=source["cameras"][view]
        for actor in ACTORS:
            key=view+"/"+actor
            values=[]
            for i,frame in enumerate(clips[view]):
                record=source["frames"][i]
                if record["frame"]!=i or abs(record["time_seconds"]-i/FPS)>1e-8:
                    raise ValueError("SOURCE_FRAME_CLOCK_FORGERY")
                bone=record["actors"][actor]["bones"]["torso"]
                center=tuple((p+q)/2 for p,q in zip(bone["head"],bone["tail"]))
                xy=project(center,camera)
                values.append(color_count(frame,xy,actor,
                    blackout=fault=="occlude" and view=="oblique" and actor=="MarigoldOriginal" and i==36))
            med=statistics.median(values)
            if med<12:raise ValueError("UNKNOWN_OR_UNOBSERVABLE_ACTOR_PALETTE:"+key+":"+str(med))
            if min(values)<max(10,int(.28*med)):
                raise ValueError("VISUAL_OCCLUSION_OR_ACTOR_DROPOUT:"+key+":"+str(min(values)))
            counts[key]={"frames_observed":N,"min_roi_pixels":min(values),
                         "median_roi_pixels":med,"max_roi_pixels":max(values)}
    return {"schema":"scp.r009.public-allframe-clean-visibility.v1",
            "status":"PASS_ORIGINAL_SYNTHETIC_RGB_VISIBILITY_ONLY",
            "frame_count":N,"observed_clean_views":list(VIEWS),
            "decoded_rgb_sha256":{v:digest(b"".join(clips[v])) for v in VIEWS},
            "roi_color_counts":counts,"source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "authentic_person_identity":"NOT_VERIFIED","human_anatomy_ROM_JCS":"UNKNOWN",
            "camera_independent_issuer":"UNKNOWN","private_R009":"HELD_NOT_ACCEPTED",
            "CPE":"NOT_PROMOTED"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--trace",required=True);p.add_argument("--front",required=True)
    p.add_argument("--oblique",required=True);p.add_argument("--out",required=True)
    p.add_argument("--fault",choices=("baseline","occlude","alias_camera","short_clock"),default="baseline")
    a=p.parse_args()
    try:
        sourcebytes=pathlib.Path(a.trace).read_bytes()
        report=observe(json.loads(sourcebytes),{"front":pathlib.Path(a.front),"oblique":pathlib.Path(a.oblique)},a.fault)
        report["trace_sha256"]=digest(sourcebytes)
        with pathlib.Path(a.out).open("x") as f:json.dump(report,f,sort_keys=True,indent=2);f.write("\n")
        print(json.dumps(report,sort_keys=True))
    except (ValueError,KeyError,IndexError,subprocess.CalledProcessError) as e:
        print("VISIBILITY_FAIL_CLOSED:"+str(e),file=sys.stderr);sys.exit(2)
if __name__=="__main__":main()
