"""Deterministic source-original equine walk foot targets.

This is a testable animation hypothesis, not scientific validation of gait.
Units: meters, 48 frames per cycle, 24 frames per second. X is forward,
Y lateral, Z up. Walk contacts ordered HL, FL, HR, FR.
"""
from dataclasses import dataclass
from math import pi, sin, isfinite

CYCLE_FRAMES = 48
STRIDE_M = 0.16
DUTY_FACTOR = 0.625
SWING_HEIGHT_M = 0.105
ANKLE_BASE_Z_M = 0.252  # measured source hoof-sole hover ~17.8mm; test this correction independently
FOOT_CONTACT_PHASE = {
    "hind_L": 0.0,
    "front_L": 0.25,
    "hind_R": 0.5,
    "front_R": 0.75,
}
REST_LOWER_TAIL_X = {"front": 0.412, "hind": -0.468}
REST_Y = {"L": -0.2, "R": 0.2}

@dataclass(frozen=True)
class FootTarget:
    frame: int
    foot: str
    phase: float
    state: str
    root_x: float
    ankle_x: float
    ankle_y: float
    ankle_z: float

def smoothstep(u):
    if not 0 <= u <= 1:
        raise ValueError("swing fraction outside [0,1]")
    return u*u*(3-2*u)

def target(frame, foot):
    if not 1 <= frame <= CYCLE_FRAMES:
        raise ValueError("invalid animation frame")
    if foot not in FOOT_CONTACT_PHASE:
        raise ValueError("unrecognized hoof")
    prefix, side = foot.split("_")
    t = (frame-1)/CYCLE_FRAMES
    phase = (t-FOOT_CONTACT_PHASE[foot]) % 1.0
    root = STRIDE_M*t
    # Relative body-space X compensates for forward root motion during stance.
    if phase < DUTY_FACTOR:
        relative = 0.08 - STRIDE_M*phase
        height = 0.0
        state = "stance_planned"
    else:
        u = (phase-DUTY_FACTOR)/(1-DUTY_FACTOR)
        relative = 0.08 - STRIDE_M*DUTY_FACTOR*(1.0-smoothstep(u))
        height = SWING_HEIGHT_M*(sin(pi*u)**2)
        state = "swing_planned"
    item=FootTarget(frame=frame, foot=foot,phase=phase,state=state,
        root_x=root,
        ankle_x=REST_LOWER_TAIL_X[prefix]+root+relative,
        ankle_y=REST_Y[side], ankle_z=ANKLE_BASE_Z_M+height)
    if not all(isfinite(v) for v in (item.root_x,item.ankle_x,item.ankle_y,item.ankle_z)):
        raise ValueError("non-finite foot target")
    return item

def trajectory():
    return {foot:[target(frame, foot) for frame in range(1, CYCLE_FRAMES+1)]
            for foot in FOOT_CONTACT_PHASE}
