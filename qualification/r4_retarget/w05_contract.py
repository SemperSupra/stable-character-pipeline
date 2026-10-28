"""W05 source-only bridge: fail-closed schema and exact original-synthetic clocks."""
import json, math, hashlib
from pathlib import Path

def read_motion(path):
    raw=Path(path).read_bytes()
    r=json.loads(raw)
    if (r.get('schema')!='stable-character/r4-w04-synthetic-retarget/1' or
        r.get('status')!='PASS_SYNTHETIC_LOCAL_TRANSLATION_SOURCE_CLOCK_ONLY' or
        r.get('lane')!='motion' or
        r.get('source_rights')!='ORIGINAL_SELF_AUTHORED_SYNTHETIC' or
        r.get('target_rights')!='ORIGINAL_SELF_AUTHORED_SYNTHETIC' or
        r.get('learned_model_inference') is not False or
        r.get('metric_3d_recovered') is not False or
        r.get('real_human_or_animal_contact_measured') is not False or
        r.get('joint_count')!=4 or r.get('frame_count')!=3):
        raise ValueError('INVALID_OR_UNADMITTED_ORIGINAL_SYNTHETIC_RETARGET')
    frames=r.get('samples')
    if not isinstance(frames,list) or len(frames)!=3:
        raise ValueError('INVALID_SOURCE_CLOCK')
    result=[]
    for i,s in enumerate(frames):
        if s.get('source_ms')!=i*1000:raise ValueError('INVALID_SOURCE_CLOCK')
        poses=s.get('target_local')
        if not isinstance(poses,dict) or set(poses)!=set(('base','pivot','hinge','tip')):
            raise ValueError('INVALID_TARGET_RIG_JOINTS')
        for p in poses.values():
            if not isinstance(p,list) or len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p):
                raise ValueError('NONFINITE_OR_INVALID_POSITION')
            if abs(p[2])>1e-9:raise ValueError('UNOBSERVED_SOURCE_DEPTH')
        result.append(poses['hinge'][0])
    if any(abs(x-y)>1e-9 for x,y in zip(result,[0,.05,.1])):
        raise ValueError('EXPECTED_SYNTHETIC_KNEE_DELTA_MISSING')
    return result,hashlib.sha256(raw).hexdigest()
