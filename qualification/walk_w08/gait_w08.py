"""W08 original synthetic stop easing and staggered ankle projection.
Keeps canonical W06 rights, clock, source joint schema and per-stance foot lock.
No private subjects, natural human gait, calibrated world depth or identity claims.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"walk_w06"))
import gait as w06
SCHEMA="scp.walk_motion.v1"
START=4.7
DURATION=.7
OFFSET=.11
VARIANT="W08_ORIGINAL_SOURCE_EASED_STOP_AND_PLANAR_ANKLE_STAGGER"
def root(start,direction,speed,t):
    s=max(0,min(t,w06.MOVING_UNTIL))
    if s<=START:return start+direction*speed*s
    u=(s-START)/DURATION
    return start+direction*speed*(START+DURATION*(u-u**3+.5*u**4))
def foot(actor,side,t,speed):
    if t>=w06.MOVING_UNTIL:
        x,y,_=foot(actor,side,w06.MOVING_UNTIL-1e-9,speed)
        return x,y,True
    d=actor["facing"]
    offset=0 if side=="left" else .5
    u=t/w06.PERIOD+offset
    cycle=math.floor(u)
    phase=u-cycle
    at=(cycle-offset)*w06.PERIOD
    shift=d*(.18+(OFFSET if side=="left" else -OFFSET))
    planted=root(actor["start_x"],d,speed,at)+shift
    if phase<w06.STANCE:return planted,w06.GROUND_ANKLE_Y,True
    p=(phase-w06.STANCE)/(1-w06.STANCE)
    next_pos=root(actor["start_x"],d,speed,at+w06.PERIOD)+shift
    return (planted+(next_pos-planted)*w06.smoothstep(p),
            w06.GROUND_ANKLE_Y+.18*math.sin(math.pi*p),False)
def generate(profile="relaxed"):
    old_root,old_foot=w06.root_at,w06.foot_at
    try:
        w06.root_at=root
        w06.foot_at=foot
        source=w06.generate(profile)
    finally:
        w06.root_at=old_root
        w06.foot_at=old_foot
    source["w08_variant"]=VARIANT
    source["w08_ease_start_seconds"]=START
    source["w08_ease_duration_seconds"]=DURATION
    source["w08_foot_stagger_scene_units"]=OFFSET
    if source["schema"]!=SCHEMA or source["source_rights"]!="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY":
        raise ValueError("W08_SOURCE_RIGHTS_OR_SCHEMA")
    w06.validate(source)
    return source
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--profile",choices=["relaxed","brisk"],default="relaxed")
    p.add_argument("--out",required=True)
    args=p.parse_args()
    m=generate(args.profile)
    body=(json.dumps(m,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(body)
    print("W08_PUBLIC_GAIT_PASS",hashlib.sha256(body).hexdigest(),len(m["frames"]))
if __name__=="__main__":main()
