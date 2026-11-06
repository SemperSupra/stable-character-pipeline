"""Deterministic voluntary tail-swishing clip, separate from passive hair physics.

Angles are provisional animation limits, NOT veterinary ROM data. No Blender dependency.
"""
import math

FRAMES=48
FPS=24
SCHEMA="equine.tail.intent.v1"
TAIL_BONES=("tail_1","tail_2","tail_3")
LIMIT_RAD=0.58
SNAP_LIMIT=0.19

def _swing(frame,delay,amplitude):
    start=8.+delay
    stop=34.+delay
    t=(frame-start)/(stop-start)
    if not 0.<t<1.:return 0.
    envelope=math.sin(math.pi*t)**2
    return amplitude*envelope*math.sin(math.tau*1.28*t)

def sample(frame, enabled=True):
    if isinstance(frame,bool) or not isinstance(frame,int) or not 1<=frame<=FRAMES:
        raise ValueError("frame not in 48-frame domain")
    if not isinstance(enabled,bool):raise ValueError("enabled not bool")
    angles=(
      _swing(frame,0.,.29),
      _swing(frame,2.,.40),
      _swing(frame,4.,.51),
    ) if enabled else (0.,0.,0.)
    result=dict(zip(TAIL_BONES,angles))
    if any(not math.isfinite(v) or abs(v)>LIMIT_RAD for v in result.values()):
        raise ValueError("tail engineering bound exceeded")
    return result

def validate_timeline(values):
    if len(values)!=FRAMES:raise ValueError("incomplete clip")
    for f,row in enumerate(values,1):
        if set(row)!=set(TAIL_BONES):raise ValueError("missing tail chain")
        if any(not isinstance(v,(float,int)) or not math.isfinite(v) or abs(v)>LIMIT_RAD for v in row.values()):
            raise ValueError("unsafe pose")
        if f>1 and any(abs(row[b]-values[f-2][b])>SNAP_LIMIT for b in TAIL_BONES):
            raise ValueError("angular snap")
    return True

def timeline():
    rows=[sample(f) for f in range(1,FRAMES+1)]
    validate_timeline(rows)
    return {"schema":SCHEMA,"frames":rows,"fps":FPS,
            "activity":"voluntary_synthetic_scheduled_swish",
            "not":"gait or physical hair simulation; not veterinary limit"}
