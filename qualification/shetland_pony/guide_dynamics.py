"""Bounded fixed-step guide-hair dynamics for original synthetic pony.

No cloth solver/physics-in-GLB claim: this runs as pre-export offline guide
simulation. Geometry/morph baking and source skin remain separate adapters.
"""
from dataclasses import dataclass
import math

SCHEMA="equine.longhair.guide.xpbd-prototype.v1"
FPS=24
PHYSICS_HZ=120

def vec3(v):
    if not isinstance(v,(tuple,list)) or len(v)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in v):
        raise ValueError("invalid 3D vector")
    return tuple(float(x) for x in v)

def add(a,b):return tuple(a[i]+b[i] for i in range(3))
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def mul(a,t):return tuple(x*t for x in a)
def norm(a):return math.sqrt(sum(x*x for x in a))
def normalized(a):
    v=norm(a)
    if v<1e-9:raise ValueError("degenerate direction")
    return mul(a,1.0/v)

@dataclass(frozen=True)
class Guide:
    root: tuple
    direction: tuple
    length: float
    segments: int=4
    damping: float=.075
    bend: float=.055
    def __post_init__(self):
        vec3(self.root);normalized(vec3(self.direction))
        if not (.08<=self.length<=.70 and isinstance(self.segments,int) and 2<=self.segments<=12):
            raise ValueError("unbounded guide")
        if not (0<=self.damping<=.5 and 0<=self.bend<=.5):
            raise ValueError("bad damping/stiffness")

def simulate(guide,frames=48,wind=(-4.,0.,0.),root_velocity=(0.,0.,0.),collision_sphere=None,root_frames=None):
    if not isinstance(guide,Guide) or not isinstance(frames,int) or not 1<=frames<=240:
        raise ValueError("unbounded experiment")
    wind=vec3(wind);root_velocity=vec3(root_velocity)
    if max(abs(x) for x in wind)>25 or max(abs(x) for x in root_velocity)>15:
        raise ValueError("excess input velocity")
    if collision_sphere is not None:
        center,radius=collision_sphere
        center=vec3(center)
        if not isinstance(radius,(float,int)) or not .01<=radius<=3:raise ValueError("bad collider")
    else:center=radius=None
    root=vec3(guide.root)
    if root_frames is not None:
        if len(root_frames)!=frames+1:
            raise ValueError("root trajectory must contain initial anchor plus every frame")
        root_frames=[vec3(p) for p in root_frames]
        if norm(sub(root_frames[0],root))>1e-7:
            raise ValueError("root trajectory initial anchor mismatch")
        for a,b in zip(root_frames,root_frames[1:]):
            if norm(sub(a,b))*FPS>12.:
                raise ValueError("root speed exceeded engineering cap")
    direction=normalized(vec3(guide.direction))
    ds=guide.length/guide.segments
    positions=[add(root,mul(direction,i*ds)) for i in range(guide.segments+1)]
    prev=positions[:]
    dt=1/PHYSICS_HZ
    result=[]
    for frame in range(1,frames+1):
        # One physical state spans exactly five 120 Hz substeps per 24 FPS frame.
        for substep in range(PHYSICS_HZ//FPS):
            old=positions[:]
            if root_frames is None:
                target_root=root
                root_speed=(0.,0.,0.)
            else:
                a,b=root_frames[frame-1],root_frames[frame]
                target_root=add(a,mul(sub(b,a),(substep+1)/(PHYSICS_HZ//FPS)))
                root_speed=mul(sub(b,a),FPS)
            # Root movement is not a new wind vector: apply its velocity
            # once as apparent flow, while inertia arises from the anchored
            # solver in world coordinates. World source positions must be
            # supplied by the actually evaluated rig, not a guessed swish.
            relative=sub(sub(wind,root_velocity),root_speed)
            for i in range(1,len(positions)):
                velocity=sub(positions[i],prev[i])
                # Approximate bounded aerodynamic force, not aerodynamic truth.
                acceleration=add((0.,0.,-3.2),mul(relative,1.7))
                p=add(add(positions[i],mul(velocity,1-guide.damping)),mul(acceleration,dt*dt))
                positions[i]=p
            positions[0]=target_root
            for _ in range(5):
                for i in range(1,len(positions)):
                    d=sub(positions[i],positions[i-1])
                    positions[i]=add(positions[i-1],mul(normalized(d),ds))
                for i in range(2,len(positions)):
                    d1=normalized(sub(positions[i-1],positions[i-2]))
                    d2=normalized(sub(positions[i],positions[i-1]))
                    positions[i]=add(positions[i-1],mul(normalized(add(mul(d2,1-guide.bend),mul(d1,guide.bend))),ds))
                if center is not None:
                    for i in range(1,len(positions)):
                        d=sub(positions[i],center)
                        if norm(d)<radius:
                            positions[i]=add(center,mul(normalized(d if norm(d)>1e-9 else (0.,1.,0.)),radius+.001))
                positions[0]=target_root
            prev=old
            if any(not math.isfinite(q) or abs(q)>100 for p in positions for q in p):
                raise ValueError("physics instability")
        result.append(tuple(positions))
    return result

def report(guide,frames,wind,root_velocity=(0.,0.,0.),root_frames=None):
    traces=simulate(guide,frames,wind,root_velocity,root_frames=root_frames)
    max_length_error=max(abs(norm(sub(p[i],p[i-1]))-guide.length/guide.segments) for p in traces for i in range(1,len(p)))
    max_root_drift=max(norm(sub(p[0],vec3(root_frames[i+1]) if root_frames else vec3(guide.root))) for i,p in enumerate(traces))
    return {"schema":SCHEMA,"frames":len(traces),"max_segment_length_error_m":max_length_error,
      "max_root_drift_m":max_root_drift,"last_tip_m":list(traces[-1][-1]),
      "medium":"original synthetic guide physics; NOT GLB-native autonomous simulation"}
