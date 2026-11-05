"""Original synthetic equine 30-joint anatomy; tentative mechanical bounds.

No numeric limit here claims an experimentally measured normal ROM. Published
horse 3D kinematics include detailed fetlock results, but those are NOT
interchangeable with carpus/stifle/hock. Fail closed on wrong topology.
"""
import math

# Degrees relative to Blender bone local rest frame. Enforced in Blender IK
# as engineering hard stops; independent 3D position ROM observer is authority.
LIMITS={
  "upper":   {"x":(-95.,95.), "z":(-12.,12.)},
  "forearm": {"x":(-105.,105.),"z":(-12.,12.)},
  "stifle":  {"x":(-100.,100.),"z":(-12.,12.)},
  "lower":   {"x":(-105.,105.),"z":(-12.,12.)},
}
TWIST_MAX_DEG=10.0
JOINTS=("front_L_forearm","front_R_forearm","hind_L_stifle","hind_R_stifle")

def chain(prefix,side,x,y,height):
    if prefix not in ("front","hind") or side not in ("L","R"):
        raise ValueError("not named equine limb")
    if prefix=="front":
        elbow=(x+.012,y,.612)
        carpus=(x-.006,y,.432)
        fetlock=(x+.012,y,.26)
        middle="forearm"
        a=(x,y,height)
        return [
          (f"{prefix}_{side}_upper","body",a,elbow),
          (f"{prefix}_{side}_{middle}",f"{prefix}_{side}_upper",elbow,carpus),
          (f"{prefix}_{side}_lower",f"{prefix}_{side}_{middle}",carpus,fetlock),
          (f"{prefix}_{side}_fetlock",f"{prefix}_{side}_lower",fetlock,(x+.03,y,.12)),
          (f"{prefix}_{side}_hoof",f"{prefix}_{side}_fetlock",(x+.03,y,.12),(x+.04,y,.035)),
        ]
    stifle=(x+.06,y,.610)
    hock=(x-.078,y,.432)
    fetlock=(x+.012,y,.26)
    return [
      (f"{prefix}_{side}_upper","body",(x,y,height),stifle),
      (f"{prefix}_{side}_stifle",f"{prefix}_{side}_upper",stifle,hock),
      (f"{prefix}_{side}_lower",f"{prefix}_{side}_stifle",hock,fetlock),
      (f"{prefix}_{side}_fetlock",f"{prefix}_{side}_lower",fetlock,(x+.03,y,.12)),
      (f"{prefix}_{side}_hoof",f"{prefix}_{side}_fetlock",(x+.03,y,.12),(x+.04,y,.035)),
    ]

def validate_structure(specs):
    names=[q[0] for q in specs]
    if len(names)!=30 or len(set(names))!=len(names):
        raise ValueError("expected exactly 30 unique named bones")
    lookup={s[0]:s for s in specs}
    for required in JOINTS:
        if required not in lookup:raise ValueError("missing anatomy "+required)
    for name,parent,head,tail in specs:
        if parent and parent not in lookup:raise ValueError("missing parent "+name)
        if not all(math.isfinite(v) for v in (*head,*tail)):
            raise ValueError("nonfinite joint")
        length=math.dist(head,tail)
        if not .05<length<.90:raise ValueError("zero or implausible rest bone "+name)
    for side in ("L","R"):
        for prefix in ("front","hind"):
            seq=chain(prefix,side,.4 if prefix=="front" else -.48,
                      -.2 if side=="L" else .2,.81 if prefix=="front" else .78)
            for a,b in zip(seq,seq[1:]):
                if math.dist(a[3],b[2])>1e-8:raise ValueError("break in joint centers")
                if b[1]!=a[0]:raise ValueError("bad kinematic parent")
    return True
