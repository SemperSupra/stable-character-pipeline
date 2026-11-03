#!/usr/bin/env python3
"""Independent synthetic foot marker ↔ authored foot state H264 observer.

Compares decoded clean and separate debug H264 at projected source ankle
positions in all 72 frames. Authored stance flags are NOT measured forces,
human biomechanics, species-specific ROM, or protected-person acceptance.
"""
import argparse,hashlib,json,math,pathlib,subprocess,sys
N,W,H,FPS=72,480,270,12
ACTORS=("CobaltOriginal","MarigoldOriginal")
SOURCE="1e56d63873b83dc33ea8f510932d1df0e09acfc66e9dae8880f2ae91658d5e86"
def digest(b):return hashlib.sha256(b).hexdigest()
def require(ok,code):
    if not ok:raise ValueError(code)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(v):
    d=math.sqrt(sum(x*x for x in v))
    if d<1e-8:raise ValueError("DEGENERATE_CAMERA")
    return tuple(x/d for x in v)
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def project(point,cam):
    forward=norm(sub(cam["target"],cam["position"]))
    right=norm(cross(forward,(0,0,1)))
    up=norm(cross(right,forward))
    d=sub(point,cam["target"])
    return ((.5+dot(d,right)/9.6)*W,
            (.5-dot(d,up)/(9.6*H/W))*H)
def decode(path):
    cmd=("ffmpeg","-hide_banner","-loglevel","error","-i",str(path),
         "-f","rawvideo","-pix_fmt","rgb24","-vsync","0","pipe:1")
    b=subprocess.run(cmd,check=True,capture_output=True).stdout
    require(len(b)==N*W*H*3,"H264_FRAME_CLOCK_NOT_72")
    stride=W*H*3
    return [memoryview(b)[i*stride:(i+1)*stride] for i in range(N)]
def marker_pixels(debug,clean,c,stance):
    cx,cy=c
    x0=max(0,int(cx)-10);x1=min(W,int(cx)+11)
    y0=max(0,int(cy)-10);y1=min(H,int(cy)+11)
    if x1<=x0 or y1<=y0:return 0
    found=0
    for y in range(y0,y1):
        for x in range(x0,x1):
            at=3*(y*W+x)
            dr,dg,db=int(debug[at]),int(debug[at+1]),int(debug[at+2])
            cr,cg,cb=int(clean[at]),int(clean[at+1]),int(clean[at+2])
            diff=max(abs(dr-cr),abs(dg-cg),abs(db-cb))
            if stance:
                colored=dg>56 and dg>1.22*dr and dg>1.20*db
            else:
                colored=dr>72 and dg>45 and dr>1.03*dg and dg>1.25*db
            if diff>30 and colored:found+=1
    return found
def observe(tracebytes,clean,debug,mode):
    require(digest(tracebytes)==SOURCE,"UNADMITTED_ORIGINAL_SYNTHETIC_TRACE_BYTES")
    t=json.loads(tracebytes)
    require(t.get("source_class")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC" and
            t.get("private_r009")=="HELD_NOT_ACCEPTED","RIGHTS_OR_PROTECTED_PRODUCT_CLAIM")
    require(t.get("actor_ids")==list(ACTORS) and t.get("fps")==FPS and
            len(t.get("frames",[]))==N,"SOURCE_CLOCK_OR_ACTOR_INCONSISTENT")
    require(len(clean)==len(debug)==N,"SOURCE_VIDEO_CLOCK_MISMATCH")
    if mode=="alias_clean":debug=clean
    if mode=="shift_clock":debug=debug[1:]
    if mode=="false_human":t["private_r009"]="ACCEPTED"
    if mode=="erase_debug":debug=clean
    require(t["private_r009"]=="HELD_NOT_ACCEPTED","FALSE_HUMAN_PRODUCT_PROMOTION")
    require(len(debug)==N,"DEBUG_CLOCK_TRUNCATED")
    require(any(clean[i].tobytes()!=debug[i].tobytes() for i in range(N)),"DEBUG_OVERLAY_ALIAS_OR_MISSING")
    counts={a:{"contact_visible":0,"swing_visible":0,"total_visible":0,
               "labels_contact":0,"labels_swing":0,"frames_any_visible":0} for a in ACTORS}
    for i in range(N):
        row=t["frames"][i]
        require(row.get("frame")==i and abs(row.get("time_seconds",-100)-i/FPS)<1e-8,"TRACE_FRAME_TIME_FORGED")
        for a in ACTORS:
            view=row["actors"][a]
            perframe=0
            for side in ("left","right"):
                foot=view["feet"][side]
                stance=foot["contact"]
                require(type(stance) is bool,"NONBOOLEAN_CONTACT_LABEL")
                require(foot["lift_m"]>=0,"SOURCE_LIFT_INVALID")
                c=project(foot["ankle"],t["cameras"]["front"])
                num=marker_pixels(debug[i],clean[i],c,stance)
                category="contact" if stance else "swing"
                counts[a]["labels_"+category]+=1
                if num>=2:
                    counts[a][category+"_visible"]+=1
                    counts[a]["total_visible"]+=1
                    perframe+=1
            if perframe:counts[a]["frames_any_visible"]+=1
    # Fail closed, not every source marker must be visible through anatomy.
    # Record actual per-frame and state coverage; no inference of physical contact.
    for a,v in counts.items():
        require(v["frames_any_visible"]>=48,"MARKER_OBSERVABILITY_INSUFFICIENT:"+a+":"+str(v))
        require(v["contact_visible"]>=18,"CONTACT_DEBUG_VISIBILITY_MISSING:"+a+":"+str(v))
        require(v["swing_visible"]>=12,"SWING_DEBUG_VISIBILITY_MISSING:"+a+":"+str(v))
    return {"schema":"scp.r009.public-debug-foot-video-observer.v1",
            "status":"PASS_AUTHORED_SYNTHETIC_DEBUG_MARKER_VISIBILITY_ONLY",
            "source_sha256":SOURCE,"views":["front_clean","front_debug"],"frames":N,
            "inspected_source_foot_labels":N*len(ACTORS)*2,
            "per_actor_observation_counts":counts,
            "source_contact_flags":"SELF_AUTHORED_NOT_MEASURED_FORCE",
            "real_ground_reaction":"UNKNOWN","human_JCS_ROM":"UNKNOWN",
            "protected_R009":"HELD_NOT_ACCEPTED","CPE":"NOT_PROMOTED"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--front",required=True)
    p.add_argument("--debug",required=True);p.add_argument("--out",required=True)
    p.add_argument("--fault",choices=("baseline","alias_clean","erase_debug","shift_clock","false_human"),default="baseline")
    p.add_argument("--capabilities",action="store_true")
    a=p.parse_args()
    if a.capabilities:
        print(json.dumps({"schema":"scp.r009.debug-foot-agent-capabilities.v1",
                          "actions":["inspect_original_synthetic","observe_source_and_video"],
                          "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
                          "private_R009":"HELD"}))
        return
    try:
        tracebytes=pathlib.Path(a.source).read_bytes()
        clean=decode(a.front);debug=decode(a.debug)
        r=observe(tracebytes,clean,debug,a.fault)
        r["clean_media_sha256"]=digest(pathlib.Path(a.front).read_bytes())
        r["debug_media_sha256"]=digest(pathlib.Path(a.debug).read_bytes())
        with pathlib.Path(a.out).open("x",encoding="utf8") as f:
            json.dump(r,f,sort_keys=True,indent=2);f.write("\n")
        print(json.dumps(r,sort_keys=True))
    except (ValueError,KeyError,IndexError,TypeError,subprocess.CalledProcessError) as exc:
        print("DEBUG_FOOT_VIDEO_REJECT:"+str(exc),file=sys.stderr)
        raise SystemExit(2)
if __name__=="__main__":main()
