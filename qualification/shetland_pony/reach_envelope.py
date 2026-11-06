"""The hoof target must lie INSIDE a three-link limb reach envelope.

This does not certify stance force/hoof contact or natural equine joint
orientation; it excludes deterministic singular/unreachable IK targets.
"""
import math
from equine_anatomy import chain
from footpaths import target,CYCLE_FRAMES

MIN_MARGIN_M=.014

def reach_margin(foot,frame):
    prefix,side=foot.split("_")
    x=.40 if prefix=="front" else -.48
    y=-.20 if side=="L" else .20
    height=.81 if prefix=="front" else .78
    specs=chain(prefix,side,x,y,height)
    segments=specs[:3]
    total=sum(math.dist(s[2],s[3]) for s in segments)
    f=target(frame,foot)
    head=segments[0][2]
    # Original armature world location includes the global walk-root X.
    foot_in_model=(f.ankle_x-f.root_x,f.ankle_y,f.ankle_z)
    distance=math.dist(head,foot_in_model)
    return {"foot":foot,"frame":frame,"limb_length_m":total,
            "target_distance_m":distance,"margin_m":total-distance}

def screen():
    result={}
    for foot in ("front_L","front_R","hind_L","hind_R"):
        points=[reach_margin(foot,frame) for frame in range(1,CYCLE_FRAMES+1)]
        min_margin=min(p["margin_m"] for p in points)
        result[foot]={"minimum_margin_m":round(min_margin,6),
                      "maximum_reach_distance_m":round(max(p["target_distance_m"] for p in points),6),
                      "limb_chain_length_m":round(points[0]["limb_length_m"],6)}
    return {"schema":"equine.ik.reach-envelope.v1",
            "source":"48 frame authored world target and articulated 3link limb geometry",
            "feet":result,
            "required_margin_m":MIN_MARGIN_M,
            "engineering_verdict":"REACH_MARGIN_PASS" if all(x["minimum_margin_m"]>=MIN_MARGIN_M for x in result.values())
                                  else "REACH_MARGIN_FAIL",
            "physical_contact":"NOT_MEASURED"}

if __name__=="__main__":
    import json
    print(json.dumps(screen(),sort_keys=True))
