"""Deterministic bounded secondary-motion *research* controller.
One-dimensional per-region compliance. NOT an anatomically calibrated soft-body
solver, collision system, FEM or proof of realistic human skin motion.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class RegionParameters:
    mass: float
    stiffness: float
    damping: float
    max_displacement: float
    def __post_init__(self):
        if (not all(isfinite(v) for v in
                    (self.mass,self.stiffness,self.damping,self.max_displacement))
            or self.mass<=0 or self.stiffness<=0 or self.damping<0 or
            self.max_displacement<=0):
            raise ValueError("invalid or nonfinite region parameters")

@dataclass
class RegionState:
    displacement: float=0.
    velocity: float=0.

class RegionController:
    def __init__(self,params:RegionParameters,sample_hz:int=240):
        if sample_hz<24 or sample_hz>2000: raise ValueError("unsupported rate")
        self.params=params
        self.sample_hz=sample_hz
        self.state=RegionState()
    def sample(self,local_acceleration:float):
        if not isfinite(local_acceleration):
            raise ValueError("nonfinite kinematic driver")
        h=1.0/self.sample_hz
        q=self.state
        p=self.params
        # Base acceleration is in the local tissue axis and acts through inertia.
        force=-p.stiffness*q.displacement-p.damping*q.velocity-p.mass*local_acceleration
        q.velocity+=h*force/p.mass
        q.displacement+=h*q.velocity
        if q.displacement>p.max_displacement:
            q.displacement=p.max_displacement
            q.velocity=min(0.,q.velocity)
        if q.displacement < -p.max_displacement:
            q.displacement=-p.max_displacement
            q.velocity=max(0.,q.velocity)
        if not all(isfinite(v) for v in (q.velocity,q.displacement)):
            raise ArithmeticError("unstable region state")
        return q.displacement
    def energy(self):
        q=self.state;p=self.params
        return .5*p.mass*q.velocity*q.velocity+.5*p.stiffness*q.displacement*q.displacement
    def snapshot(self):
        return (self.state.displacement,self.state.velocity)

def simulate(params,frames,fps,driver,sample_hz=240):
    if fps<=0 or sample_hz%fps:
        raise ValueError("frame rate must divide deterministic solver sample rate")
    c=RegionController(params,sample_hz)
    samples_per_frame=sample_hz//fps
    sampled=[]
    for frame in range(frames):
        for sample_in_frame in range(samples_per_frame):
            global_sample=frame*samples_per_frame+sample_in_frame
            c.sample(float(driver(global_sample/sample_hz)))
        sampled.append(c.snapshot())
    return sampled

def to_morph_amplitude(displacement,range_m):
    """Symmetric bounded amplitude; compatible with two opposite morph targets."""
    if range_m<=0 or not isfinite(range_m) or not isfinite(displacement):
        raise ValueError("bad deformation range")
    q=max(-1.,min(1.,displacement/range_m))
    return {"positive":max(q,0.),"negative":max(-q,0.)}
