#!/usr/bin/env python3
"""Original synthetic costume: bounded smooth 3D armhole-ease control (stdlib).

This controls only bind-pose x-displacement near the shoulder/armhole. It is
NOT a cloth simulation, fitting algorithm or biological-accuracy assertion.
"""
import math
ACTORS=('AsterOriginal','JuniperOriginal')
CENTER_X=.184
CENTER_Y=1.345
RADIUS_X=.12
RADIUS_Y=.095
MAX_DISPLACEMENT_M=.06
class ArmholeContractError(ValueError):pass

def valid_amount(value):
    if type(value) not in (float,int) or not math.isfinite(value) or not 0<=value<=MAX_DISPLACEMENT_M:
        raise ArmholeContractError('AMPLITUDE_OUT_OF_RANGE')
    return value

def validate_amounts(amounts):
    if type(amounts) is not dict or set(amounts)!=set(ACTORS):
        raise ArmholeContractError('ACTOR_SET_MISMATCH')
    for amount in amounts.values():valid_amount(amount)
    return True

def smoothstep(x):
    if type(x) not in (float,int) or not math.isfinite(x):raise ArmholeContractError('NONFINITE_CONTROL')
    v=max(0.,min(1.,float(x)))
    return v*v*(3.-2.*v)

def delta_x(x,y,z,amount):
    valid_amount(amount)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x,y,z)):
        raise ArmholeContractError('NONFINITE_VERTEX')
    tx=smoothstep(1.-abs(abs(x)-CENTER_X)/RADIUS_X)
    ty=smoothstep(1.-abs(y-CENTER_Y)/RADIUS_Y)
    return (1. if x>=0 else -1.)*amount*tx*ty
