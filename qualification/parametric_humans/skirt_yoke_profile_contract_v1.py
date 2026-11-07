#!/usr/bin/env python3
"""Pure-stdlib fail-closed profile for the R009 experimental skirt yoke."""
import math
ACTORS=('AsterOriginal','JuniperOriginal')
SOURCE_SHA256='ae2b809ffa5cf5dfee0adf2f6b88b0a864e3588b95638de4c8b86e83a6e524af'
class ProfileError(ValueError):pass

def validate(actor,strength,hip_share):
    if actor not in ACTORS:raise ProfileError('UNKNOWN_ACTOR')
    if type(strength) not in (float,int) or not math.isfinite(strength) or not 0<=strength<=.95:
        raise ProfileError('INVALID_LOWER_STRENGTH')
    if type(hip_share) not in (float,int) or not math.isfinite(hip_share) or not 0<=hip_share<=.8:
        raise ProfileError('INVALID_HIP_SHARE')
    return True
