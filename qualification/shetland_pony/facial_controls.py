"""Deterministic, bounded synthetic equine face action channel sampler.

This is an engineering subset informed by equine anatomy, NOT a certified
EquiFACS annotation or a classifier of equine emotional state.
No Blender dependency; exported channel semantics stay stable across actors.
"""
import math

SCHEMA="equine.face.controls.v1"
FRAMES=48
CHANNEL_LIMITS={
    "ear_L_yaw_deg":(-20.0,20.0),
    "ear_R_yaw_deg":(-20.0,20.0),
    "blink_L":(0.0,1.0),
    "blink_R":(0.0,1.0),
    "nostril_L":(0.0,1.0),
    "nostril_R":(0.0,1.0),
    "jaw_open_deg":(0.0,9.0),
}
def pulse(frame,center,halfwidth):
    if not (isinstance(frame,int) and 1<=frame<=FRAMES):
        raise ValueError("invalid frame")
    if not (1<=center<=FRAMES and halfwidth>0):raise ValueError("invalid pulse")
    d=abs(frame-center)/float(halfwidth)
    t=max(0.,1.-d)
    return t*t*(3.-2.*t)

def sample(frame):
    if not isinstance(frame,int) or frame<1 or frame>FRAMES:
        raise ValueError("frame out of range")
    p=math.tau*(frame-1)/FRAMES
    actions={
       "ear_L_yaw_deg":10*math.sin(p),
       "ear_R_yaw_deg":-8*math.sin(p+.5),
       "blink_L":max(pulse(frame,10,3),pulse(frame,30,3)),
       "blink_R":max(pulse(frame,11,3),pulse(frame,30,3)),
       "nostril_L":.75*pulse(frame,22,9),
       "nostril_R":.68*pulse(frame,23,9),
       "jaw_open_deg":6.5*pulse(frame,40,8),
    }
    validate(actions)
    return actions

def validate(values):
    if set(values)!=set(CHANNEL_LIMITS):raise ValueError("missing/extra action")
    for k,(lo,hi) in CHANNEL_LIMITS.items():
        v=values[k]
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v):
            raise ValueError("nonfinite or invalid "+k)
        if v<lo-1e-8 or v>hi+1e-8:
            raise ValueError("unsafe action "+k)
    return True

def timeline():
    result=[sample(f) for f in range(1,FRAMES+1)]
    assert len(result)==FRAMES
    return {"schema":SCHEMA,"fps":24,"frames":result,
            "note":"original synthetic face test, not measured EquiFACS ground truth"}
