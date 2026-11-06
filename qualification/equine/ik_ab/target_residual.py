"""Independent actual exported 30j GLB ankle-target deviation screen.

Compares per-frame actual *lower bone tail* in world coordinates with the
source-authored target. It does not measure hoof-ground contact or force.
"""
import math

FEET=('front_L','front_R','hind_L','hind_R')

def vec(v):
    if len(v)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in v):
        raise ValueError('invalid finite 3d point')
    return tuple(v)
def screen(observed, *, tolerance_m=.02):
    if tolerance_m!=.02:raise ValueError('source-experiment tolerance not calibrated')
    if set(observed)!=set(FEET):raise ValueError('four source limbs required')
    out={}
    for foot in FEET:
        samples=observed[foot]
        if len(samples)!=48 or [r.get('frame') for r in samples]!=list(range(1,49)):
            raise ValueError('requires 48 strict frame samples')
        residuals=[];over=[]
        for row in samples:
            target=vec(row['planned_world_ankle_xyz'])
            actual=vec(row['actual_world_lower_tail_xyz'])
            err=math.dist(target,actual)
            if err>3:raise ValueError('coordinate-frame mismatch or invalid rig, fail closed')
            residuals.append(err)
            if err>tolerance_m:
                over.append({'frame':row['frame'],'residual_m':round(err,6)})
        out[foot]={'max_world_ankle_target_error_m':round(max(residuals),7),
                   'mean_world_ankle_target_error_m':round(sum(residuals)/len(residuals),7),
                   'frames_over_20mm':len(over),
                   'first_excessive_samples':over[:10],
                   'frame_1_error_m':round(residuals[0],7)}
    return {'schema':'equine.ik.actual-world-target-residual.v1','source':'IMPORTED_NATIVE_30J_GLTF_48F',
            'contact_physics':'UNKNOWN','veterinary_anatomy':'UNKNOWN',
            'orientation_source_verified_by':'WORLD_COORDINATES_AND_PINNED_SOURCE_PLAN',
            'threshold_source':'ENGINEERING_20MM_ONLY_NOT_VETERNARY',
            'limbs':out,'all_frames':48,
            'total_front_frames_over_20mm':sum(out[f]['frames_over_20mm'] for f in FEET[:2]),
            'model_release_accepted':False}
